"""
Node 0 as an actual step instead of an assumption.

Everywhere else in this project, the transcript is the ground truth: the
note is checked against it, and whatever it says wins. That is fine while
the transcript is a hand-written string in data/test_cases.json. It stops
being fine the moment the transcript comes from a real encounter, because
then the transcript is itself a model's output - an ASR model's - and this
project's entire premise is that an unverified model output should not be
trusted.

That is the gap this module exists to close. It does not just turn audio
into text; it carries the recognizer's own uncertainty forward, so that
`analysis.py` can tell the difference between "this claim was checked
against the transcript and holds" and "this claim was checked against a
stretch of audio the recognizer was guessing at."

The categories that matter most here are not arbitrary. taxonomy.json
ranks numeric/medication and negation errors as the highest-severity
failures, and those are exactly the two things speech recognition damages
most: "fifteen" and "fifty" differ by one phoneme, and a dropped "no"
inverts a denial. ASR failure modes and this project's error taxonomy fail
on the same categories, for the same clinical stakes.

Providers, in failover order (mirroring llm_router's philosophy - a single
provider being down should degrade the run, not end it):

  1. groq / whisper-large-v3-turbo  - fast, free tier, OpenAI-compatible
  2. groq / whisper-large-v3        - slower, more accurate
  3. local faster-whisper           - only if the package is installed;
                                      no key, no network, fully offline

Every provider is normalised to the same result shape, so nothing
downstream knows or cares which one ran.

Usage:
    from transcribe import transcribe
    result = transcribe("encounter.wav")
    result["text"]      -> the transcript
    result["segments"]  -> timed spans, each with a confidence in [0, 1]
"""
import math
import os

import _env  # noqa: F401 - loads .env before anything reads os.environ
import usage
from openai_compat_client import PROVIDER_SETTINGS, resolve_api_key

# Provider chain. Same shape as the model chains in config.py so this reads
# like the rest of the project rather than a bolted-on subsystem.
TRANSCRIBE_CHAIN = [
    {"provider": "groq", "model": "whisper-large-v3-turbo"},
    {"provider": "groq", "model": "whisper-large-v3"},
    {"provider": "local", "model": "faster-whisper-base"},
]

# Audio formats the hosted providers accept. Checked before upload so a
# wrong file type fails immediately with a useful message rather than
# burning a request to find out.
SUPPORTED_SUFFIXES = {".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm", ".flac", ".ogg"}


def _confidence_from_logprob(avg_logprob) -> float:
    """Whisper reports avg_logprob: the mean log-probability per token in a
    segment. exp() of that is the geometric mean probability, which is the
    closest thing to a calibrated 0-1 confidence Whisper offers.

    It is NOT a probability that the text is correct, and this module never
    claims it is. It is a usable relative signal: segments the model was
    guessing at score lower than segments it was sure of. That is enough to
    decide what a human should re-listen to, which is all it is used for.
    """
    if avg_logprob is None:
        return None
    try:
        return round(min(1.0, math.exp(float(avg_logprob))), 4)
    except (TypeError, ValueError, OverflowError):
        return None


def _normalise_segments(raw_segments) -> list[dict]:
    """Every provider gets flattened into this one shape."""
    segments = []
    for seg in raw_segments or []:
        get = seg.get if isinstance(seg, dict) else lambda k, d=None: getattr(seg, k, d)
        avg_logprob = get("avg_logprob")
        segments.append({
            "start": float(get("start", 0.0) or 0.0),
            "end": float(get("end", 0.0) or 0.0),
            "text": (get("text") or "").strip(),
            "avg_logprob": avg_logprob,
            "no_speech_prob": get("no_speech_prob"),
            "confidence": _confidence_from_logprob(avg_logprob),
        })
    return segments


def _transcribe_hosted(audio_path: str, provider: str, model: str) -> dict:
    from openai import OpenAI

    api_key = resolve_api_key(provider)
    if not api_key:
        raise RuntimeError(f"no API key for provider '{provider}'")

    client = OpenAI(api_key=api_key, base_url=PROVIDER_SETTINGS[provider]["base_url"])
    with usage.timed() as t:
        try:
            with open(audio_path, "rb") as audio:
                response = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio.read()),
                    model=model,
                    # verbose_json is what carries avg_logprob per segment.
                    # Without it this module would return text and nothing
                    # else, and the whole point here is the "and nothing
                    # else" part not being true.
                    response_format="verbose_json",
                    temperature=0.0,
                )
        except Exception:
            usage.record(provider, model, latency_s=t.elapsed, ok=False)
            raise
    usage.record(provider, model, latency_s=t.elapsed, ok=True)

    data = response if isinstance(response, dict) else response.model_dump()
    return {
        "text": (data.get("text") or "").strip(),
        "segments": _normalise_segments(data.get("segments")),
        "duration_s": data.get("duration"),
        "provider": provider,
        "model": model,
    }


def _transcribe_local(audio_path: str, model: str) -> dict:
    """Offline failover. Optional dependency on purpose: the hosted path
    needs no install at all, so faster-whisper is not in requirements.txt
    and its absence is a skipped provider, never a crash."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed (pip install faster-whisper). "
            "This provider is optional - it only exists so the pipeline can "
            "run with no API key and no network."
        ) from exc

    size = model.replace("faster-whisper-", "") or "base"
    with usage.timed() as t:
        whisper = WhisperModel(size, device="cpu", compute_type="int8")
        segments, info = whisper.transcribe(audio_path, temperature=0.0)
        segments = list(segments)
    usage.record("local", model, latency_s=t.elapsed, ok=True)

    return {
        "text": " ".join(s.text.strip() for s in segments).strip(),
        "segments": _normalise_segments(segments),
        "duration_s": getattr(info, "duration", None),
        "provider": "local",
        "model": model,
    }


def transcribe(audio_path: str, chain: list = None, verbose: bool = False) -> dict:
    """Audio file -> {text, segments, provider, model}.

    Tries each provider in order and returns the first success. If every
    provider fails, raises with the full list of what went wrong - the same
    contract llm_router uses, because a silent fallback to "no transcript"
    would be indistinguishable from "the encounter was silent".
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(audio_path)

    suffix = os.path.splitext(audio_path)[1].lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"{suffix or 'file'} is not a supported audio format. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )

    failures = []
    for tier in (chain or TRANSCRIBE_CHAIN):
        provider, model = tier["provider"], tier["model"]
        if provider != "local" and not resolve_api_key(provider):
            failures.append(f"{provider}/{model}: no API key set - SKIPPED")
            continue
        try:
            if verbose:
                print(f"  [transcribe] trying {provider}/{model}...")
            result = (_transcribe_local(audio_path, model) if provider == "local"
                      else _transcribe_hosted(audio_path, provider, model))
            if not result["text"]:
                raise RuntimeError("provider returned an empty transcript")
            if verbose:
                scored = [s for s in result["segments"] if s["confidence"] is not None]
                print(f"  [transcribe] {provider}/{model} returned "
                      f"{len(result['segments'])} segment(s), "
                      f"{len(scored)} with a confidence score")
            return result
        except Exception as exc:  # noqa: BLE001 - the whole point is to try the next tier
            failures.append(f"{provider}/{model}: {type(exc).__name__}: {exc}")
            if verbose:
                print(f"  [transcribe] {provider}/{model} unavailable - trying next tier...")

    raise RuntimeError(
        "Every transcription provider failed:\n  " + "\n  ".join(failures)
    )
