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

Usage:
    python compute_metrics.py
"""
import csv
import json
import os

SEVERITY_WEIGHT = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, "..", "data", "test_cases.json")
TAXONOMY_PATH = os.path.join(BASE, "..", "taxonomy.json")
SCORECARD_PATH = os.path.join(BASE, "scorecard_blind.csv")
KEY_PATH = os.path.join(BASE, "blind_key.json")


def main():
    with open(DATA_PATH) as f:
        cases = {c["id"]: c for c in json.load(f)["cases"]}
    with open(TAXONOMY_PATH) as f:
        taxonomy = {c["id"]: c for c in json.load(f)["categories"]}
    with open(KEY_PATH) as f:
        blind_key = json.load(f)
    with open(SCORECARD_PATH) as f:
        rows = list(csv.DictReader(f))

    results = {"pipeline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                             "weighted_possible": 0.0, "false_positives": 0,
                             "control_cases": 0},
               "baseline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                            "weighted_possible": 0.0, "false_positives": 0,
                            "control_cases": 0}}

    missing_cells = []

    for row in rows:
        case_id = row["case_id"]
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
                results[system]["control_cases"] += 1
                if fp_cell not in ("", "0"):
                    try:
                        results[system]["false_positives"] += int(fp_cell)
                    except ValueError:
                        pass

    if missing_cells:
        print("WARNING: some scorecard cells are still blank, skipped in scoring:")
        for c in missing_cells:
            print(f"  {c}")
        print()

    print("=" * 60)
    print("RESULTS")
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
