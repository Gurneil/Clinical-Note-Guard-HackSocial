"""
Node 3b: verification inherits the uncertainty of its source.

THE IDEA
--------
Node 3 answers "is this claim supported by the transcript?". That question
has an unstated second half: "...and how much is the transcript worth
here?". While the transcript is hand-written text, the answer is "all of
it". While it comes out of a speech recogniser, the answer varies segment
by segment, and the recogniser will tell you if you ask.

So a claim's verdict is only as good as the audio it was checked against.
This module takes node 3's verdicts, finds which stretch of audio each
verdict actually rested on, and downgrades the ones that rested on audio
the recogniser was guessing at:

    supported + confident audio     -> supported          (unchanged)
    supported + UNRELIABLE audio    -> UNVERIFIABLE       (new)
    contradicted + confident audio  -> contradicted       (unchanged)
    contradicted + UNRELIABLE audio -> UNVERIFIABLE       (new)

WHY "SUPPORTED" IS THE DANGEROUS ONE
------------------------------------
A contradicted claim already goes to a human - it is a flag, someone reads
it. A *supported* claim is the one that passes silently into a signed note.
If it was validated against a mis-heard number, this system has done worse
than nothing: it has laundered an ASR error into a confirmed fact and put
a tick next to it. Downgrading confident-looking passes is the whole point,
not a side effect.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not guess what the audio really said, correct the transcript, or
decide whether the note is right. There is no way to resolve the
uncertainty from the text alone - the only thing that resolves it is a
person listening to those seconds of audio. So the output is an
"unverifiable" flag carrying a timestamp, and the human at node 7 gets
told where to listen. Uncertainty is surfaced, never silently resolved.

Every function here is pure: text and dicts in, dicts out. No API calls,
no I/O. That is what makes it testable without audio.
"""
import re

from pipeline import _DOSE_RE, _BP_RE  # reuse the real detectors, never a copy

# Below this geometric-mean token probability, a segment is treated as
# unreliable.
#
# NOT a guess - measured. eval/asr_confidence_check.py degrades one
# synthetic encounter in steps and records, at each step, both the
# recogniser's confidence and whether the clinically load-bearing facts
# survived (see eval/asr_confidence_results.json):
#
#   clean / mild    0.801 - 0.901   dose and blood pressure both recovered
#   heavy / severe  0.313 - 0.369   both lost; the "heavy" run returned
#                                   fluent, grammatical English that was
#                                   entirely invented
#
# Every run that preserved the facts scored at least 0.801; every run that
# destroyed them scored at most 0.369. 0.55 sits in the empty band between,
# with margin on both sides.
#
# Still exposed as a parameter, because that gap was measured on one
# recogniser and one recording chain. Anyone deploying this should re-run
# that script on their own audio rather than inherit this number on trust.
DEFAULT_CONFIDENCE_FLOOR = 0.55

# A segment Whisper thinks may not contain speech at all is unreliable
# regardless of how confident it is about the words it invented for it.
DEFAULT_NO_SPEECH_CEILING = 0.5

# Negations invert clinical meaning, and ASR drops or mangles them
# routinely ("no known allergies" -> "known allergies"). taxonomy.json
# ranks negation errors as critical for exactly this reason.
_NEGATION_RE = re.compile(
    r"\b(no|not|never|denies|denied|negative|without|nor|none|isn't|wasn't|doesn't|didn't|can't)\b",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def is_unreliable(segment: dict,
                  confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
                  no_speech_ceiling: float = DEFAULT_NO_SPEECH_CEILING) -> bool:
    """A segment with no confidence score at all is treated as RELIABLE.

    That is the conservative direction here, and it is a deliberate choice:
    the hand-written transcripts in data/test_cases.json carry no scores, so
    scoring absence as unreliable would flag all 60 benchmark cases as
    unverifiable and make the feature unusable everywhere it is not needed.
    Absence of evidence about the audio is not evidence of bad audio.
    """
    confidence = segment.get("confidence")
    if confidence is not None and confidence < confidence_floor:
        return True
    no_speech = segment.get("no_speech_prob")
    if no_speech is not None and no_speech > no_speech_ceiling:
        return True
    return False


def locate_evidence(evidence: str, segments: list[dict]) -> list[dict]:
    """Which segments does this quoted evidence span come from?

    Node 3 returns evidence as a quote from the transcript, so the join is a
    substring search across the segment texts. Matching is whitespace- and
    case-insensitive; if the quote is not found verbatim, falls back to the
    segments sharing the most distinctive words with it, because models
    paraphrase quotes more often than they should.

    Returns [] when nothing can be attributed - callers must treat that as
    "unknown", never as "fine".
    """
    needle = _normalise(evidence)
    if not needle or not segments:
        return []

    # exact-ish: does any single segment contain the quote?
    hits = [s for s in segments if needle in _normalise(s.get("text"))]
    if hits:
        return hits

    # the quote may straddle a segment boundary: walk a sliding window
    for width in (2, 3):
        for i in range(len(segments) - width + 1):
            window = segments[i:i + width]
            joined = _normalise(" ".join(s.get("text", "") for s in window))
            if needle in joined:
                return window

    # fallback: distinctive-word overlap, requiring a real majority so a
    # couple of shared stopwords can't attribute a claim to the wrong audio
    words = {w for w in re.findall(r"[a-z0-9]+", needle) if len(w) >= 4}
    if not words:
        return []
    scored = []
    for s in segments:
        seg_words = set(re.findall(r"[a-z0-9]+", _normalise(s.get("text"))))
        overlap = len(words & seg_words)
        if overlap and overlap >= max(2, len(words) * 0.6):
            scored.append((overlap, s))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [s for _, s in scored[:2]]


def high_risk_tokens(text: str) -> list[str]:
    """The parts of a claim where a mis-hearing is most likely to hurt:
    doses, blood pressures, and negations. Used to escalate severity, not to
    decide whether to flag."""
    found = [m.group(0).strip() for m in _DOSE_RE.finditer(text or "")]
    found += [m.group(0).strip() for m in _BP_RE.finditer(text or "")]
    found += [m.group(0).strip() for m in _NEGATION_RE.finditer(text or "")]
    seen, unique = set(), []
    for token in found:
        key = token.lower()
        if key not in seen:
            seen.add(key)
            unique.append(token)
    return unique


def format_timespan(segments: list[dict]) -> str:
    """'00:41-00:47', for a human who now has to go and listen to it."""
    if not segments:
        return ""
    start = min(s.get("start", 0.0) for s in segments)
    end = max(s.get("end", 0.0) for s in segments)

    def stamp(seconds):
        seconds = int(seconds or 0)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    return f"{stamp(start)}-{stamp(end)}"


def unverifiable_flags(claims: list[str],
                       entailment_results: list[dict],
                       segments: list[dict],
                       confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
                       no_speech_ceiling: float = DEFAULT_NO_SPEECH_CEILING) -> list[dict]:
    """Node 3's verdicts + the audio they rested on -> unverifiable flags.

    Only fires for claims whose supporting audio is measurably shaky. A
    claim whose evidence cannot be located in any segment is left alone: it
    is unattributable, not unreliable, and inventing a flag for it would
    make this noisy in exactly the cases where it knows least.
    """
    if not segments:
        return []

    flags = []
    for claim, result in zip(claims, entailment_results or []):
        status = (result or {}).get("status")
        evidence = (result or {}).get("evidence", "")

        # "not_mentioned" rests on the absence of audio evidence, not on any
        # particular segment, so there is nothing to attribute confidence to.
        if status not in ("supported", "contradicted"):
            continue

        located = locate_evidence(evidence, segments)
        shaky = [s for s in located
                 if is_unreliable(s, confidence_floor, no_speech_ceiling)]
        if not shaky:
            continue

        risky = high_risk_tokens(claim) or high_risk_tokens(evidence)
        confidences = [s["confidence"] for s in shaky if s.get("confidence") is not None]
        worst = min(confidences) if confidences else None
        timespan = format_timespan(shaky)

        if status == "supported":
            explanation = (
                f"This claim was marked supported, but the transcript span it "
                f"relies on came from audio the recogniser was unsure of "
                f"({timespan}). The note may be right - the source is not "
                f"reliable enough to confirm it."
            )
        else:
            explanation = (
                f"This claim was marked contradicted, but the transcript span "
                f"it conflicts with came from unreliable audio ({timespan}). "
                f"The note may be correct and the transcript wrong."
            )
        if risky:
            explanation += (
                f" It contains {', '.join(repr(t) for t in risky[:3])}, which is "
                f"where mis-recognition does the most clinical damage."
            )

        flags.append({
            "claim": claim,
            "status": "unverifiable",
            "category": "transcript_uncertainty",
            "explanation": explanation,
            "original_status": status,
            "evidence": evidence,
            "audio_span": timespan,
            "asr_confidence": worst,
            "high_risk_tokens": risky,
            "action": f"Re-listen to {timespan} before signing.",
            "source": "asr_confidence",
        })

    return flags


def transcript_reliability_summary(segments: list[dict],
                                   confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
                                   no_speech_ceiling: float = DEFAULT_NO_SPEECH_CEILING) -> dict:
    """Whole-transcript view, for the header of a review screen: how much of
    this encounter is the system actually able to vouch for?"""
    scored = [s for s in segments if s.get("confidence") is not None]
    unreliable = [s for s in segments
                  if is_unreliable(s, confidence_floor, no_speech_ceiling)]
    total_audio = sum(max(0.0, (s.get("end") or 0) - (s.get("start") or 0)) for s in segments)
    shaky_audio = sum(max(0.0, (s.get("end") or 0) - (s.get("start") or 0)) for s in unreliable)
    return {
        "segments": len(segments),
        "segments_scored": len(scored),
        "segments_unreliable": len(unreliable),
        "audio_seconds": round(total_audio, 1),
        "unreliable_seconds": round(shaky_audio, 1),
        "unreliable_pct": round(100.0 * shaky_audio / total_audio, 1) if total_audio else 0.0,
        "mean_confidence": (round(sum(s["confidence"] for s in scored) / len(scored), 3)
                            if scored else None),
        "spans_to_review": [format_timespan([s]) for s in unreliable],
    }
