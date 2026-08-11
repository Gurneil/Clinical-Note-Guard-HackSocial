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
import llm_router  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_cases.json")
RAW_OUT_PATH = os.path.join(os.path.dirname(__file__), "raw_outputs.json")
SCORECARD_PATH = os.path.join(os.path.dirname(__file__), "scorecard_blind.csv")
KEY_PATH = os.path.join(os.path.dirname(__file__), "blind_key.json")


# The blinding is only real if the two systems' cells are INDISTINGUISHABLE.
# The first version of this leaked in two ways at once, and a 100% reliable
# tell means the grading sheet was blind in name only:
#   1. pipeline rows carried "[category] " prefixes; baseline rows never did
#   2. the empty cells differed - "(no flags raised)" vs "(no issues found)"
# Both are normalised away below. Items are also sorted, so neither system's
# internal ordering (pipeline emits node 3's flags, then node 4's, then
# node 5's) survives as a structural hint.
#
# One tell CANNOT be removed and is documented rather than hidden: the
# pipeline usually raises more items per case, because decomposition is what
# it does. A grader may still guess from volume. That is inherent to the
# systems being compared, not an artifact of presentation.
EMPTY_CELL = "(nothing flagged)"


def _blinded_cell(items: list) -> str:
    cleaned = sorted({(i or "").strip() for i in items if (i or "").strip()})
    return " | ".join(cleaned) if cleaned else EMPTY_CELL


def summarize_pipeline_flags(guard_result: dict) -> str:
    return _blinded_cell([
        f.get("claim") or f.get("flagged_value")
        for f in guard_result["all_flags"]
    ])


def summarize_baseline_flags(baseline_result: list) -> str:
    return _blinded_cell([item.get("issue") for item in baseline_result])


def main():
    # Without this, a fresh `python run_eval.py` process still starts clean
    # (the sticky tier index is a module-level variable, gone when the
    # process exits) - this only matters if something else in the same
    # process already called into llm_router before main() ran. Explicit
    # here anyway so a full eval run always starts by trying Gemini first,
    # rather than depending on that being true by accident of process
    # lifetime.
    llm_router.reset_core_tier()

    # encoding="utf-8" is not optional here: these files contain em dashes,
    # and Windows defaults to cp1252, which silently mojibakes them into the
    # prompts rather than failing.
    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = json.load(f)["cases"]

    raw_outputs = []
    blind_rows = []
    blind_key = {}
    tier_mismatches = []
    failed_cases = []

    # The whole loop body is wrapped so that ANY exception (a case that
    # exhausts its JSON retry budget, a keyboard interrupt, whatever) still
    # results in every case processed BEFORE the failure being written to
    # disk, rather than losing an entire run's worth of API calls. This was
    # a real bug, not a hypothetical: a full 60-case run crashed on case 54
    # of 60 (a small model returning malformed JSON twice in a row) with no
    # top-level handling, silently discarding 53 already-completed cases'
    # worth of paid API calls because raw_outputs was only ever written
    # after the loop finished normally.
    try:
        for case in dataset:
            case_id = case["id"]
            transcript = case["transcript"]
            note = case["note_under_test"]
            print(f"Running case: {case_id} ...")

            try:
                pipeline_result = run_guard(transcript, note, verbose=True)
                baseline_flags, baseline_provider, baseline_model = single_prompt_check(transcript, note)
            except Exception as e:
                # A single case failing (e.g. a mechanical-tier model
                # returning malformed JSON on every retry) is a real,
                # expected possibility at this scale - not a reason to
                # discard every other case's results. Recorded explicitly
                # as failed (not silently skipped) so it's visible in
                # raw_outputs.json and excluded from scoring rather than
                # miscounted as "no flags raised".
                print(f"  !! ERROR on {case_id}, skipping this case: {e}")
                failed_cases.append(case_id)
                raw_outputs.append({
                    "case_id": case_id,
                    "ground_truth": case["ground_truth"],
                    "error": str(e),
                })
                continue

            pipe_provider = pipeline_result["core_reasoning_provider"]
            pipe_model = pipeline_result["core_reasoning_model"]
            fairness_mismatch = (pipe_provider, pipe_model) != (baseline_provider, baseline_model)
            if fairness_mismatch:
                # Should not happen given the sticky shared tier index in
                # llm_router.py, but checked explicitly rather than assumed -
                # if this ever fires, the comparison for this case is NOT
                # fair. Recorded on the case itself (not just printed) so
                # compute_metrics.py can exclude it from scoring rather than
                # silently folding an invalid comparison into the headline
                # numbers.
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
                "baseline_provider": baseline_provider,
                "baseline_model": baseline_model,
                "fairness_mismatch": fairness_mismatch,
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
    finally:
        # Runs even on a mid-loop crash or Ctrl-C - whatever was completed
        # is never silently lost.
        with open(RAW_OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(raw_outputs, f, indent=2)
        print(f"\nWrote raw outputs -> {RAW_OUT_PATH}")

        if blind_rows:
            with open(SCORECARD_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(blind_rows[0].keys()))
                writer.writeheader()
                writer.writerows(blind_rows)
            print(f"Wrote blind scorecard -> {SCORECARD_PATH}")
            print("  -> Fill in the 4 blank columns by hand, WITHOUT looking at blind_key.json first.")

            with open(KEY_PATH, "w", encoding="utf-8") as f:
                json.dump(blind_key, f, indent=2)
            print(f"Wrote blind key -> {KEY_PATH}  (don't peek until scorecard is filled in!)")

    if failed_cases:
        print(f"\n!! {len(failed_cases)} case(s) failed and were excluded entirely: {failed_cases}")
        print("   See each case's \"error\" field in raw_outputs.json. Consider re-running just")
        print("   those cases (transient model-formatting failures are usually not reproducible).")

    if tier_mismatches:
        print(f"\n!! {len(tier_mismatches)} case(s) had a fairness mismatch: {tier_mismatches}")
        print("   These comparisons are not apples-to-apples - treat their scores with caution")
        print("   or exclude them, and note this explicitly in your documentation.")
    else:
        print("\nNo fairness mismatches - every case compared pipeline vs. baseline on the same provider/model.")


if __name__ == "__main__":
    main()
