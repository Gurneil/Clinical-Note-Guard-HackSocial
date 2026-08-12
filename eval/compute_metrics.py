"""
Run this AFTER you've filled in the 4 blank columns of scorecard_blind.csv
by hand. Reveals which system was A/B per case using blind_key.json, joins
against the ground truth in data/test_cases.json, and computes:

  - recall: of the cases that actually had a planted error, what fraction
    did each system catch?
  - severity-weighted recall: same, but weighted by taxonomy severity
    (numeric_medication_error / negation_error = critical, so missing one
    of those costs more than missing a lower-severity category)
  - false positive rate: on the clean control case(s), did the system
    raise any flags at all?

Cases where the pipeline and baseline ended up on different providers/
models (a "fairness mismatch" - see run_eval.py and llm_router.py) are
EXCLUDED from all of the above by default, because that comparison isn't
apples-to-apples for that case. They're reported separately instead of
being silently folded into the headline numbers. Pass --include-mismatches
to score them anyway (not recommended - only for debugging).

Usage:
    python compute_metrics.py
    python compute_metrics.py --include-mismatches
"""
import csv
import json
import os
import sys

SEVERITY_WEIGHT = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "..", "data", "test_cases.json")
TAXONOMY_PATH = os.path.join(BASE, "..", "taxonomy.json")
SCORECARD_PATH = os.path.join(BASE, "scorecard_blind.csv")
KEY_PATH = os.path.join(BASE, "blind_key.json")
RAW_OUT_PATH = os.path.join(BASE, "raw_outputs.json")


def main():
    include_mismatches = "--include-mismatches" in sys.argv

    # encoding="utf-8" everywhere - see the note in run_eval.py.
    with open(DATA_PATH, encoding="utf-8") as f:
        cases = {c["id"]: c for c in json.load(f)["cases"]}
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        taxonomy = {c["id"]: c for c in json.load(f)["categories"]}
    with open(KEY_PATH, encoding="utf-8") as f:
        blind_key = json.load(f)
    with open(SCORECARD_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    mismatched_cases = set()
    if os.path.exists(RAW_OUT_PATH):
        with open(RAW_OUT_PATH, encoding="utf-8") as f:
            raw_outputs = json.load(f)
        mismatched_cases = {
            r["case_id"] for r in raw_outputs if r.get("fairness_mismatch")
        }
    else:
        print(f"NOTE: {RAW_OUT_PATH} not found - can't check for fairness "
              f"mismatches, scoring all rows as-is.\n")

    results = {"pipeline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                             "weighted_possible": 0.0, "false_positives": 0,
                             "control_cases": 0},
               "baseline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                            "weighted_possible": 0.0, "false_positives": 0,
                            "control_cases": 0}}

    missing_cells = []
    excluded_cases = []

    for row in rows:
        case_id = row["case_id"]
        if case_id in mismatched_cases and not include_mismatches:
            excluded_cases.append(case_id)
            continue
        gt = cases[case_id]["ground_truth"]
        key = blind_key[case_id]  # {"A": "pipeline"/"baseline", "B": ...}

        for label in ("A", "B"):
            system = key[label]
            caught_cell = row[f"{label}_caught_target_error(1/0)"].strip()
            fp_cell = row[f"{label}_false_positive_count"].strip()

            if gt["has_error"]:
                if caught_cell == "":
                    missing_cells.append((case_id, label, "caught_target_error"))
                    continue
                severity = taxonomy[gt["injected_errors"][0]["category"]]["severity"]
                weight = SEVERITY_WEIGHT.get(severity, 1)
                results[system]["possible"] += 1
                results[system]["weighted_possible"] += weight
                if caught_cell == "1":
                    results[system]["hits"] += 1
                    results[system]["weighted_hits"] += weight
            else:
                # An UNGRADED control must not count toward control_cases.
                # It used to: the denominator grew while the numerator
                # couldn't, so a partially-graded sheet silently reported a
                # better false-positive rate than the grading supported.
                # Harmless on a fully-filled sheet, wrong on a subsample.
                if fp_cell == "":
                    missing_cells.append((case_id, label, "false_positive_count"))
                    continue
                results[system]["control_cases"] += 1
                try:
                    results[system]["false_positives"] += int(fp_cell)
                except ValueError:
                    missing_cells.append((case_id, label, "false_positive_count (unparseable)"))

    if missing_cells:
        print("WARNING: some scorecard cells are still blank, skipped in scoring:")
        for c in missing_cells:
            print(f"  {c}")
        print()

    if excluded_cases:
        print(f"EXCLUDED {len(excluded_cases)} case(s) from scoring - pipeline and "
              f"baseline ran on different providers/models for these, so the "
              f"comparison isn't fair: {sorted(excluded_cases)}")
        print("(pass --include-mismatches to score them anyway)\n")

    print("=" * 60)
    print("RESULTS")
    if excluded_cases:
        print(f"({len(excluded_cases)} fairness-mismatched case(s) excluded - see above)")
    print("=" * 60)
    for system in ("pipeline", "baseline"):
        r = results[system]
        recall = r["hits"] / r["possible"] if r["possible"] else float("nan")
        w_recall = r["weighted_hits"] / r["weighted_possible"] if r["weighted_possible"] else float("nan")
        print(f"\n{system.upper()}")
        print(f"  Recall (planted errors caught):        {r['hits']}/{r['possible']}  ({recall:.0%})")
        print(f"  Severity-weighted recall:               {w_recall:.0%}")
        print(f"  False positives on clean control cases: {r['false_positives']} (across {r['control_cases']} control case(s))")

    print("\n" + "=" * 60)
    print("Copy this table into your documentation / samples doc.")


if __name__ == "__main__":
    main()
