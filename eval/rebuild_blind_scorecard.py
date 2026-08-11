"""
Rebuilds scorecard_blind.csv + blind_key.json from the committed
raw_outputs.json. No API calls, no re-run.

WHY THIS EXISTS
---------------
The original grading sheet was blind in name only. Pipeline cells carried
"[category] " prefixes and baseline cells did not, and the two systems even
had different text for "nothing flagged". Checked against blind_key.json
after the fact: in all 57 cases where exactly one side was bracketed, the
bracketed side was the pipeline. 100%. A grader learns that tell in two
rows and is unblinded for the rest of the sheet.

Re-running the whole eval to fix a formatting bug would have cost a day of
free-tier quota and produced different model outputs, making the fix
impossible to separate from run-to-run variance. The outputs are already
committed, so the sheet is rebuilt from them instead: same outputs, blinded
properly, and a freshly randomised A/B assignment so the old key is void.

Usage:
    python rebuild_blind_scorecard.py
    python rebuild_blind_scorecard.py --seed 7   # reproducible assignment
"""
import argparse
import csv
import json
import os
import random

from run_eval import summarize_pipeline_flags, summarize_baseline_flags

BASE = os.path.dirname(__file__)
RAW_PATH = os.path.join(BASE, "raw_outputs.json")
SCORECARD_PATH = os.path.join(BASE, "scorecard_blind.csv")
KEY_PATH = os.path.join(BASE, "blind_key.json")

FIELDS = [
    "case_id", "system_A_output", "system_B_output",
    "A_caught_target_error(1/0)", "B_caught_target_error(1/0)",
    "A_false_positive_count", "B_false_positive_count",
    "core_reasoning_provider_model", "notes",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed the A/B randomisation (default: unseeded).")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    with open(RAW_PATH, encoding="utf-8") as f:
        raw_outputs = json.load(f)

    # Refuse to silently destroy grading work already done.
    if os.path.exists(SCORECARD_PATH):
        with open(SCORECARD_PATH, encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
        graded = [r for r in existing if any(
            (r.get(c) or "").strip() for c in
            ("A_caught_target_error(1/0)", "B_caught_target_error(1/0)",
             "A_false_positive_count", "B_false_positive_count"))]
        if graded:
            raise SystemExit(
                f"{SCORECARD_PATH} already has {len(graded)} graded row(s). "
                "Rebuilding would discard them AND invalidate them (the A/B "
                "assignment is re-randomised). Move that file aside first if "
                "you really mean to start over."
            )

    rows, blind_key, skipped = [], {}, []

    for row in raw_outputs:
        case_id = row["case_id"]
        if "error" in row:
            skipped.append(case_id)
            continue

        summaries = {
            "pipeline": summarize_pipeline_flags(row["pipeline_result"]),
            "baseline": summarize_baseline_flags(row["baseline_result"]),
        }

        systems = ["pipeline", "baseline"]
        random.shuffle(systems)
        label_map = {systems[0]: "A", systems[1]: "B"}
        blind_key[case_id] = {v: k for k, v in label_map.items()}

        rows.append({
            "case_id": case_id,
            "system_A_output": summaries["pipeline"] if label_map["pipeline"] == "A" else summaries["baseline"],
            "system_B_output": summaries["pipeline"] if label_map["pipeline"] == "B" else summaries["baseline"],
            "A_caught_target_error(1/0)": "",
            "B_caught_target_error(1/0)": "",
            "A_false_positive_count": "",
            "B_false_positive_count": "",
            "core_reasoning_provider_model": (
                f"{row.get('core_reasoning_provider')}/{row.get('core_reasoning_model')}"),
            "notes": "",
        })

    with open(SCORECARD_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with open(KEY_PATH, "w", encoding="utf-8") as f:
        json.dump(blind_key, f, indent=2)

    # Prove the tell is gone rather than assuming it.
    bracketed = sum(1 for r in rows
                    if ("[" in r["system_A_output"]) != ("[" in r["system_B_output"]))
    lengths_equal_format = sum(1 for r in rows
                               if r["system_A_output"] == r["system_B_output"])

    print(f"Rebuilt {SCORECARD_PATH} - {len(rows)} rows to grade")
    if skipped:
        print(f"  skipped {len(skipped)} errored case(s): {', '.join(skipped)}")
    print(f"Rebuilt {KEY_PATH} - the OLD key is now void, do not use it")
    print(f"\nFormat-tell check: {bracketed} row(s) where only one side is bracketed "
          f"(should be 0)")
    print(f"Identical-cell rows (both systems flagged the same things): {lengths_equal_format}")
    print("\nNow grade it:  python grade_blind.py")


if __name__ == "__main__":
    main()
