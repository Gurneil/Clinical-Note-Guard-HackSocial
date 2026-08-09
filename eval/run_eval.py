"""
Runs both the pipeline and the single-prompt baseline across every case in
data/test_cases.json, and writes:

  eval/raw_outputs.json   - full raw output from both systems, every case,
                             INCLUDING which provider/model backed the
                             core-reasoning comparison for that case (this
                             is what makes a run that downgrades mid-way
                             still fully auditable, not silently mixed)
  eval/scorecard_blind.csv - a BLINDED grading sheet: for each case, "System A"
                             and "System B" outputs are shown with labels
                             randomized per case, so whoever grades it (you)
                             doesn't know which is the pipeline and which is
                             the baseline while scoring. This avoids
                             unconsciously grading generously in favor of the
                             system you built.
  eval/blind_key.json     - the mapping from A/B back to pipeline/baseline,
                             per case. Do NOT look at this until AFTER you've
                             filled in scorecard_blind.csv.

Usage:
    export GEMINI_API_KEY="your-key-here"
    export GROQ_API_KEY="your-key-here"          (optional - failover)
    export FEATHERLESS_API_KEY="your-key-here"   (optional - failover)
    cd eval
    python run_eval.py
"""
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import run_guard          # noqa: E402
from baseline import single_prompt_check  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_cases.json")
RAW_OUT_PATH = os.path.join(os.path.dirname(__file__), "raw_outputs.json")
SCORECARD_PATH = os.path.join(os.path.dirname(__file__), "scorecard_blind.csv")
KEY_PATH = os.path.join(os.path.dirname(__file__), "blind_key.json")


def summarize_pipeline_flags(guard_result: dict) -> str:
    lines = []
    for f in guard_result["all_flags"]:
        label = f.get("claim") or f.get("flagged_value")
        cat = f.get("category", "")
        lines.append(f"[{cat}] {label}")
    return " | ".join(lines) if lines else "(no flags raised)"


def summarize_baseline_flags(baseline_result: list) -> str:
    lines = [f"{item.get('issue')}" for item in baseline_result]
    return " | ".join(lines) if lines else "(no issues found)"


def main():
    # encoding="utf-8" is not optional here: these files contain em dashes,
    # and Windows defaults to cp1252, which silently mojibakes them into the
    # prompts rather than failing.
    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)["cases"]

    raw_outputs = []
    blind_rows = []
    blind_key = {}
    tier_mismatches = []

    for case in dataset:
        case_id = case["id"]
        transcript = case["transcript"]
        note = case["note_under_test"]
        print(f"Running case: {case_id} ...")

        pipeline_result = run_guard(transcript, note, verbose=True)
        baseline_flags, baseline_provider, baseline_model = single_prompt_check(transcript, note)

        pipe_provider = pipeline_result["core_reasoning_provider"]
        pipe_model = pipeline_result["core_reasoning_model"]
        if (pipe_provider, pipe_model) != (baseline_provider, baseline_model):
            # Should not happen given the sticky shared tier index in
            # llm_router.py, but checked explicitly rather than assumed -
            # if this ever fires, the comparison for this case is NOT
            # fair and should be flagged, not silently scored.
            tier_mismatches.append(case_id)
            print(f"  !! WARNING: fairness mismatch on {case_id}: "
                  f"pipeline used {pipe_provider}/{pipe_model}, "
                  f"baseline used {baseline_provider}/{baseline_model}")

        raw_outputs.append({
            "case_id": case_id,
            "ground_truth": case["ground_truth"],
            "pipeline_result": pipeline_result,
            "baseline_result": baseline_flags,
            "core_reasoning_provider": pipe_provider,
            "core_reasoning_model": pipe_model,
        })

        # Randomize A/B assignment per case so position isn't a tell
        systems = ["pipeline", "baseline"]
        random.shuffle(systems)
        label_map = {systems[0]: "A", systems[1]: "B"}
        blind_key[case_id] = {v: k for k, v in label_map.items()}

        summaries = {
            "pipeline": summarize_pipeline_flags(pipeline_result),
            "baseline": summarize_baseline_flags(baseline_flags),
        }

        blind_rows.append({
            "case_id": case_id,
            "system_A_output": summaries["pipeline"] if label_map["pipeline"] == "A" else summaries["baseline"],
            "system_B_output": summaries["pipeline"] if label_map["pipeline"] == "B" else summaries["baseline"],
            "A_caught_target_error(1/0)": "",
            "B_caught_target_error(1/0)": "",
            "A_false_positive_count": "",
            "B_false_positive_count": "",
            "core_reasoning_provider_model": f"{pipe_provider}/{pipe_model}",
            "notes": "",
        })

    with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_outputs, f, indent=2)
    print(f"\nWrote raw outputs -> {RAW_OUT_PATH}")

    with open(SCORECARD_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(blind_rows[0].keys()))
        writer.writeheader()
        writer.writerows(blind_rows)
    print(f"Wrote blind scorecard -> {SCORECARD_PATH}")
    print("  -> Fill in the 4 blank columns by hand, WITHOUT looking at blind_key.json first.")

    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(blind_key, f, indent=2)
    print(f"Wrote blind key -> {KEY_PATH}  (don't peek until scorecard is filled in!)")

    if tier_mismatches:
        print(f"\n!! {len(tier_mismatches)} case(s) had a fairness mismatch: {tier_mismatches}")
        print("   These comparisons are not apples-to-apples - treat their scores with caution")
        print("   or exclude them, and note this explicitly in your documentation.")
    else:
        print("\nNo fairness mismatches - every case compared pipeline vs. baseline on the same provider/model.")


if __name__ == "__main__":
    main()
