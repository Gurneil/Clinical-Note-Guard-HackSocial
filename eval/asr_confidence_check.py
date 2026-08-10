"""
Does Whisper's confidence actually fall when Whisper starts making things
up? Calibration experiment for node 3b's threshold.

WHY THIS HAD TO BE MEASURED
---------------------------
src/transcript_confidence.py downgrades a claim to "unverifiable" when the
audio behind it scores below DEFAULT_CONFIDENCE_FLOOR. That threshold is
the entire feature: too low and it never fires, too high and every claim
becomes unverifiable and the system is useless. Picking it by intuition
would have made node 3b decorative - a mechanism that looks principled and
never does anything.

So: take one clean recording, degrade it in controlled steps, and at each
step measure BOTH the recogniser's confidence AND whether the clinically
load-bearing facts (the dose, the blood pressure) actually survived. If
confidence tracks damage, the threshold can be placed in the gap between
them and defended with data. If it doesn't, node 3b has no usable input and
this repo needs to say so.

WHAT THE FIRST RUN FOUND (see asr_confidence_results.json)
----------------------------------------------------------
Confidence separates cleanly, with a wide margin:

    clean   0.835 - 0.901   dose 10mg recovered, BP 128/82 recovered
    mild    0.801 - 0.869   dose 10mg recovered, BP 128/82 recovered
    heavy   0.362 - 0.369   NOTHING recovered - fluent, entirely invented speech
    severe  0.313 - 0.671   NOTHING recovered - garbage

The "heavy" row is the one that matters. Whisper did not fail loudly there;
it produced calm, grammatical English ("I miss your operation. Please
proceed.") that has nothing to do with the audio. That is an ASR
hallucination wearing the same clothes as a real transcript - and it is
exactly what a downstream note-checker would otherwise validate against
without noticing. Confidence caught it: 0.36 against 0.85 for real speech.

The default floor of 0.55 sits in the empty band between those two
clusters, roughly equidistant from the worst correct run (0.80) and the
best hallucinated one (0.37).

Usage:
    python asr_confidence_check.py path/to/encounter.wav
    python asr_confidence_check.py path/to/encounter.wav --model whisper-large-v3

Requires a Groq key (or any provider in TRANSCRIBE_CHAIN). Degradation is
done with the stdlib only - no ffmpeg, no numpy.
"""
import argparse
import array
import json
import os
import re
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from transcribe import transcribe  # noqa: E402
from transcript_confidence import DEFAULT_CONFIDENCE_FLOOR  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "asr_confidence_results.json")

# (label, speech gain, peak noise amplitude). Roughly: untouched, a poor
# room mic, a bad speakerphone, and a recording that should never have been
# used for documentation at all.
LEVELS = [
    ("clean", 1.0, 0),
    ("mild", 0.6, 1500),
    ("heavy", 0.25, 7000),
    ("severe", 0.12, 14000),
]

_DOSE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:mg|milligram)", re.IGNORECASE)
_BP = re.compile(r"(\d{2,3})\s*(?:over|/)\s*(\d{2,3})", re.IGNORECASE)


def degrade(src_path: str, dst_path: str, gain: float, noise: float):
    """Attenuate the speech and add uniform hiss. Deterministic: seeded, so
    a rerun degrades the audio identically and the numbers are comparable."""
    import random
    random.seed(11)

    with wave.open(src_path, "rb") as src:
        params = src.getparams()
        if params.sampwidth != 2:
            raise SystemExit("this script expects 16-bit PCM wav input")
        frames = src.readframes(src.getnframes())

    samples = array.array("h")
    samples.frombytes(frames)
    if noise or gain != 1.0:
        noise = int(noise)
        for i in range(len(samples)):
            value = int(samples[i] * gain) + (random.randint(-noise, noise) if noise else 0)
            samples[i] = max(-32768, min(32767, value))

    with wave.open(dst_path, "wb") as dst:
        dst.setparams(params)
        dst.writeframes(samples.tobytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", help="16-bit PCM wav of a synthetic encounter")
    parser.add_argument("--model", default="whisper-large-v3")
    parser.add_argument("--provider", default="groq")
    parser.add_argument("--keep", action="store_true", help="keep the degraded wav files")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        raise SystemExit(f"{args.audio} not found")

    chain = [{"provider": args.provider, "model": args.model}]
    stem = os.path.splitext(args.audio)[0]
    rows = []

    print(f"\nASR confidence vs. transcription damage - {args.provider}/{args.model}\n")
    header = f"{'level':<9}{'confidence':>20}{'dose':>10}{'blood pressure':>17}{'chars':>8}"
    print(header)
    print("-" * len(header))

    for label, gain, noise in LEVELS:
        path = args.audio if label == "clean" else f"{stem}_{label}.wav"
        if label != "clean":
            degrade(args.audio, path, gain, noise)

        try:
            result = transcribe(path, chain=chain)
        except Exception as exc:  # noqa: BLE001
            print(f"{label:<9}{'FAILED: ' + type(exc).__name__:>20}")
            rows.append({"level": label, "error": f"{type(exc).__name__}: {exc}"})
            continue

        confidences = [s["confidence"] for s in result["segments"] if s["confidence"] is not None]
        text = result["text"]
        doses = _DOSE.findall(text)
        bps = ["/".join(b) for b in _BP.findall(text)]

        low, high = (min(confidences), max(confidences)) if confidences else (None, None)
        rows.append({
            "level": label,
            "gain": gain,
            "noise_amplitude": noise,
            "confidence_min": low,
            "confidence_max": high,
            "segments": len(result["segments"]),
            "doses_recovered": doses,
            "blood_pressures_recovered": bps,
            "transcript_chars": len(text),
            "transcript_excerpt": text[:160],
            "below_floor": bool(low is not None and low < DEFAULT_CONFIDENCE_FLOOR),
        })

        span = f"{low:.3f} - {high:.3f}" if low is not None else "n/a"
        print(f"{label:<9}{span:>20}{(doses[0] + 'mg' if doses else '-- LOST'):>10}"
              f"{(bps[0] if bps else '-- LOST'):>17}{len(text):>8}")

        if not args.keep and label != "clean" and os.path.exists(path):
            os.remove(path)

    scored = [r for r in rows if r.get("confidence_min") is not None]
    intact = [r for r in scored if r["doses_recovered"] and r["blood_pressures_recovered"]]
    damaged = [r for r in scored if not r["doses_recovered"] or not r["blood_pressures_recovered"]]

    report = {
        "provider": args.provider,
        "model": args.model,
        "confidence_floor": DEFAULT_CONFIDENCE_FLOOR,
        "levels": rows,
    }

    print()
    if intact and damaged:
        worst_intact = min(r["confidence_min"] for r in intact)
        best_damaged = max(r["confidence_min"] for r in damaged)
        report["worst_confidence_with_facts_intact"] = worst_intact
        report["best_confidence_with_facts_lost"] = best_damaged
        report["separated"] = worst_intact > best_damaged
        if worst_intact > best_damaged:
            print(f"Separated: every run that kept the clinical facts scored at least "
                  f"{worst_intact:.3f};\nevery run that lost them scored at most {best_damaged:.3f}. "
                  f"The floor of {DEFAULT_CONFIDENCE_FLOOR} sits inside that gap.")
        else:
            print(f"NOT SEPARATED: a run that lost the facts scored {best_damaged:.3f}, "
                  f"at or above\nthe worst run that kept them ({worst_intact:.3f}). "
                  "No threshold can divide these,\nand node 3b should not be trusted on "
                  "this provider until that changes.")
    else:
        print("Not enough contrast in this run to place a threshold - "
              "every level either kept or lost the facts.")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWritten to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
