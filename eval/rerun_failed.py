"""
Re-runs only the cases that FAILED in a previous run, and merges the results
back into that run's raw_outputs.json.

Why this exists: at 60 cases a handful will fail for reasons that have
nothing to do with the systems being compared - a free-tier rate limit, a
small model returning malformed JSON twice. Those cases are recorded with
their error and excluded from scoring, which is correct, but it leaves the
run smaller than it should be. Re-running the whole benchmark to recover
them would cost a full run's worth of quota and, worse, would re-roll every
other case's result, so the numbers would move for reasons unrelated to the
fix.

This re-runs the failures only, leaves every already-successful case exactly
as it was, and rebuilds the blind scorecard from the merged set so the run
stays gradeable.

Usage:
    CORE_CHAIN="groq:llama-3.3-70b-versatile" \
        python eval/rerun_failed.py eval/runs/core-llama-3.3-70b

Pass the same CORE_CHAIN the original run used, or the recovered cases will
be answered by a different model than the rest of the run - which is exactly
the mixed-model problem the run existed to avoid. The script checks this
against the models already recorded and refuses to merge on a mismatch.
"""
import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from pipeline import run_guard                      # noqa: E402
from baseline import single_prompt_check            # noqa: E402
import llm_router                                   # noqa: E402
from run_eval import (summarize_pipeline_flags,     # noqa: E402
                      summarize_baseline_flags)

DATA_PATH = os.path.join(HERE, "..", "data", "test_cases.json")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    run_dir = os.path.abspath(sys.argv[1])
    raw_path = os.path.join(run_dir, "raw_outputs.json")
    if not os.path.exists(raw_path):
        raise SystemExit(f"no raw_outputs.json in {run_dir}")

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    with open(DATA_PATH, encoding="utf-8") as f:
        dataset = {c["id"]: c for c in json.load(f)["cases"]}

    failed = [r["case_id"] for r in raw if "error" in r]
    if not failed:
        print("nothing to do - no failed cases in this run")
        return

    existing_models = {r.get("core_reasoning_model") for r in raw if "error" not in r}
    print(f"run:              {run_dir}")
    print(f"already succeeded: {len(raw) - len(failed)} cases on {sorted(existing_models)}")
    print(f"failed:            {len(failed)} cases")
    for c in failed:
        print(f"                     {c}")
    print()

    llm_router.reset_core_tier()
    recovered, still_failing = {}, []

    for case_id in failed:
        case = dataset[case_id]
        print(f"Re-running {case_id} ...")
        try:
            pipeline_result = run_guard(case["transcript"], case["note_under_test"], verbose=True)
            baseline_flags, b_provider, b_model = single_prompt_check(
                case["transcript"], case["note_under_test"])
        except Exception as e:
            print(f"  !! still failing: {e}")
            still_failing.append(case_id)
            continue

        p_provider = pipeline_result["core_reasoning_provider"]
        p_model = pipeline_result["core_reasoning_model"]

        # Guard against quietly stitching a different model into the run.
        if existing_models and p_model not in existing_models:
            print(f"  !! REFUSING to merge {case_id}: answered by {p_model}, "
                  f"but the rest of this run is {sorted(existing_models)}. "
                  f"Set CORE_CHAIN to match and try again.")
            still_failing.append(case_id)
            continue

        recovered[case_id] = {
            "case_id": case_id,
            "ground_truth": case["ground_truth"],
            "pipeline_result": pipeline_result,
            "baseline_result": baseline_flags,
            "core_reasoning_provider": p_provider,
            "core_reasoning_model": p_model,
            "baseline_provider": b_provider,
            "baseline_model": b_model,
            "fairness_mismatch": (p_provider, p_model) != (b_provider, b_model),
        }

    if not recovered:
        print("\nnothing recovered - original files left untouched")
        return

    merged = [recovered.get(r["case_id"], r) for r in raw]
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    # Rebuild the blind scorecard from the merged set. Safe because this
    # run's scorecard is ungraded; never do this to a scorecard someone has
    # already filled in by hand.
    rows, key = [], {}
    for r in merged:
        if "error" in r:
            continue
        systems = ["pipeline", "baseline"]
        random.shuffle(systems)
        label = {systems[0]: "A", systems[1]: "B"}
        key[r["case_id"]] = {v: k for k, v in label.items()}
        s = {"pipeline": summarize_pipeline_flags(r["pipeline_result"]),
             "baseline": summarize_baseline_flags(r["baseline_result"])}
        rows.append({
            "case_id": r["case_id"],
            "system_A_output": s["pipeline"] if label["pipeline"] == "A" else s["baseline"],
            "system_B_output": s["pipeline"] if label["pipeline"] == "B" else s["baseline"],
            "A_caught_target_error(1/0)": "",
            "B_caught_target_error(1/0)": "",
            "A_false_positive_count": "",
            "B_false_positive_count": "",
            "core_reasoning_provider_model": f"{r['core_reasoning_provider']}/{r['core_reasoning_model']}",
            "notes": "",
        })
    with open(os.path.join(run_dir, "scorecard_blind.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(run_dir, "blind_key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, indent=2)

    print(f"\nrecovered {len(recovered)} case(s); {len(still_failing)} still failing")
    if still_failing:
        for c in still_failing:
            print(f"  {c}")
    print(f"merged -> {raw_path}")
    print(f"scorecard rebuilt ({len(rows)} scoreable cases)")


if __name__ == "__main__":
    main()
