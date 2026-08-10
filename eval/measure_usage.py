"""
Measures real per-note cost (tokens) and latency for the pipeline vs. the
baseline, using src/usage.py.

Deliberately NOT folded into run_eval.py's full 60-case run: token/latency
cost per call doesn't depend on which case is being checked or whether the
answer was right, so a small, diverse sample gives the same per-node numbers
as a full run would, at a fraction of the API budget (this project runs on
free tiers with a 20/day Gemini cap - see docs/ARCHITECTURE.md).

Reports, per system, per case: number of LLM calls, total tokens, wall-clock
latency. Aggregates across the sample into "cost of guarding one note" vs.
"cost of the single-prompt baseline on one note" - the real number behind
this project's Sustainability & Scalability claims, previously undocumented.

Usage:
    cd eval
    python measure_usage.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import run_guard          # noqa: E402
from baseline import single_prompt_check  # noqa: E402
import llm_router  # noqa: E402
import usage  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_cases.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "usage_summary.json")

# A small, deliberately diverse sample - one of each error category plus a
# clean control - rather than all 60, to keep this a cheap, repeatable
# measurement rather than a second full eval run.
SAMPLE_IDS = [
    "case_01_numeric_medication_error",
    "case_02_fabrication",
    "case_03_negation_error",
    "case_04_distortion",
    "case_05_misattribution",
    "case_15_omission_otc_medication",
    "case_06_clean_control",
]


def main():
    llm_router.reset_core_tier()
    with open(DATA_PATH, encoding="utf-8") as f:
        cases = {c["id"]: c for c in json.load(f)["cases"]}

    per_case = []
    for case_id in SAMPLE_IDS:
        case = cases[case_id]
        print(f"Measuring {case_id} ...")

        usage.reset()
        run_guard(case["transcript"], case["note_under_test"], verbose=False)
        pipeline_usage = usage.summary()

        usage.reset()
        single_prompt_check(case["transcript"], case["note_under_test"])
        baseline_usage = usage.summary()

        per_case.append({
            "case_id": case_id,
            "pipeline": pipeline_usage,
            "baseline": baseline_usage,
        })

    def _agg(key):
        calls = sum(c[key]["calls"] for c in per_case)
        tokens = sum(c[key]["total_tokens"] for c in per_case)
        latency = sum(c[key]["latency_s"] for c in per_case)
        n = len(per_case)
        return {
            "sample_size": n,
            "total_calls": calls,
            "avg_calls_per_note": round(calls / n, 2),
            "total_tokens": tokens,
            "avg_tokens_per_note": round(tokens / n, 1),
            "total_latency_s": round(latency, 2),
            "avg_latency_s_per_note": round(latency / n, 2),
        }

    result = {
        "sample_ids": SAMPLE_IDS,
        "pipeline": _agg("pipeline"),
        "baseline": _agg("baseline"),
        "per_case": per_case,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {OUT_PATH}")

    print("\n" + "=" * 60)
    print(f"{'':20}{'Pipeline':>18}{'Baseline':>18}")
    print(f"{'Avg calls/note':20}{result['pipeline']['avg_calls_per_note']:>18}{result['baseline']['avg_calls_per_note']:>18}")
    print(f"{'Avg tokens/note':20}{result['pipeline']['avg_tokens_per_note']:>18}{result['baseline']['avg_tokens_per_note']:>18}")
    print(f"{'Avg latency/note(s)':20}{result['pipeline']['avg_latency_s_per_note']:>18}{result['baseline']['avg_latency_s_per_note']:>18}")
    print("=" * 60)


if __name__ == "__main__":
    main()
