"""
Node ablation over the committed eval run - answers "does each detector
actually earn its place?" without spending a single API call.

WHY THIS EXISTS
---------------
docs/ARCHITECTURE.md argues that node 4 (deterministic numeric check) and
node 5 (omission check) exist because node 3 (LLM entailment) structurally
cannot do their jobs. That is an argument, not a measurement. This script
turns it into a measurement.

Every flag in raw_outputs.json records which node produced it, in its
`source` field:

    llm_pipeline           -> node 3, entailment
    deterministic_check    -> node 4, regex numeric/medication check
    llm_pipeline_omission  -> node 5, omission check

So the pipeline can be re-scored with any node's flags withheld, using the
outputs already committed to this repo. No re-run, no new API spend, and
every configuration below is scored against the exact same run - which is
a cleaner comparison than re-running the pipeline three times would be,
since it removes run-to-run model variance entirely.

WHAT IT REPORTS
---------------
For the full pipeline and for each single-node ablation:
  - recall (planted errors caught)
  - severity-weighted recall (numeric/medication and negation weigh most)
  - false positives raised across the clean control cases

The number that matters is the DELTA: full recall minus ablated recall is
that node's marginal contribution - the errors that would have been missed
had the node not existed. A node whose delta is 0 caught nothing the other
nodes didn't already catch, and this script will say so plainly.

INHERITED CAVEAT
----------------
This reuses auto_score.py's matching heuristic, so it inherits the same
proxy limitation: it is keyword/category overlap, not a human's judgment.
The deltas are more trustworthy than the absolute numbers, because both
sides of every delta are scored by the identical heuristic on the identical
run - a systematic bias in the matcher largely cancels out.

Usage:
    python ablation.py
    python ablation.py --include-mismatches
    python ablation.py --threshold 0.25
"""
import argparse
import json
import os

from auto_score import (
    AUTO_SCORE_THRESHOLD,
    SEVERITY_WEIGHT,
    RAW_OUT_PATH,
    TAXONOMY_PATH,
    _is_caught,
)

BASE = os.path.dirname(__file__)
ABLATION_PATH = os.path.join(BASE, "ablation_results.json")

# node id -> (flag source value, human label)
NODES = {
    3: ("llm_pipeline", "entailment check"),
    3.5: ("asr_confidence", "transcript confidence"),
    4: ("deterministic_check", "deterministic numeric check"),
    5: ("llm_pipeline_omission", "omission check"),
}

# Node 3b only produces flags on runs whose transcript came from audio. The
# committed benchmark is hand-written text, so it contributes nothing there,
# and a row of zeros for a node that could not have fired would be
# misleading rather than informative - so it is skipped unless present.
def _sources_present(raw_outputs) -> set:
    present = set()
    for row in raw_outputs:
        if "error" in row:
            continue
        for flag in row["pipeline_result"]["all_flags"]:
            present.add(flag.get("source"))
    return present


def _score(raw_outputs, taxonomy, keep_sources, threshold, include_mismatches):
    """Score the pipeline counting only flags whose source is in keep_sources."""
    hits = possible = 0
    weighted_hits = weighted_possible = 0.0
    false_positives = control_cases = 0
    caught_ids = set()

    for row in raw_outputs:
        if "error" in row:
            continue
        if row.get("fairness_mismatch") and not include_mismatches:
            continue

        flags = [f for f in row["pipeline_result"]["all_flags"]
                 if f.get("source") in keep_sources]
        gt = row["ground_truth"]

        if gt["has_error"]:
            gt_error = gt["injected_errors"][0]
            weight = SEVERITY_WEIGHT.get(taxonomy[gt_error["category"]]["severity"], 1)
            possible += 1
            weighted_possible += weight
            if _is_caught(flags, gt_error, threshold, is_pipeline=True):
                hits += 1
                weighted_hits += weight
                caught_ids.add(row["case_id"])
        else:
            control_cases += 1
            false_positives += len(flags)

    return {
        "recall_hits": hits,
        "recall_possible": possible,
        "recall_pct": round(100.0 * hits / possible, 1) if possible else 0.0,
        "weighted_pct": round(100.0 * weighted_hits / weighted_possible, 1) if weighted_possible else 0.0,
        "false_positives": false_positives,
        "control_cases": control_cases,
        "_caught_ids": caught_ids,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-mismatches", action="store_true",
                        help="Score fairness-mismatched cases too (not recommended - see ARCHITECTURE.md).")
    parser.add_argument("--threshold", type=float, default=AUTO_SCORE_THRESHOLD,
                        help=f"Jaccard overlap threshold for a text match (default {AUTO_SCORE_THRESHOLD}).")
    args = parser.parse_args()

    if not os.path.exists(RAW_OUT_PATH):
        raise SystemExit(f"{RAW_OUT_PATH} not found - run run_eval.py first.")

    with open(RAW_OUT_PATH, encoding="utf-8") as f:
        raw_outputs = json.load(f)
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        taxonomy = {c["id"]: c for c in json.load(f)["categories"]}

    # The partition has to be exact, or every delta below is meaningless.
    # Fail loudly rather than quietly scoring a subset of the real flags.
    known = {src for src, _ in NODES.values()}
    for row in raw_outputs:
        if "error" in row:
            continue
        p = row["pipeline_result"]
        parts = len(p["llm_flags"]) + len(p["deterministic_flags"]) + len(p["omission_flags"])
        if parts != len(p["all_flags"]):
            raise SystemExit(
                f"{row['case_id']}: all_flags ({len(p['all_flags'])}) is not the sum of the "
                f"per-node lists ({parts}) - the node partition is not exact, so ablation "
                "deltas cannot be trusted. Investigate before reporting anything from this."
            )
        for flag in p["all_flags"]:
            if flag.get("source") not in known:
                raise SystemExit(
                    f"{row['case_id']}: flag with unrecognised source {flag.get('source')!r}. "
                    "Add it to NODES before scoring, or it will be silently dropped."
                )

    all_sources = set(known)
    full = _score(raw_outputs, taxonomy, all_sources, args.threshold, args.include_mismatches)

    report = {
        "threshold": args.threshold,
        "cases_scored": full["recall_possible"] + full["control_cases"],
        "full_pipeline": {k: v for k, v in full.items() if not k.startswith("_")},
        "ablations": {},
    }

    rows = [("full pipeline (nodes 3+4+5)", full, None)]

    present = _sources_present(raw_outputs)
    for node_id, (source, label) in sorted(NODES.items()):
        if source not in present:
            continue
        ablated = _score(raw_outputs, taxonomy, all_sources - {source},
                         args.threshold, args.include_mismatches)
        lost = sorted(full["_caught_ids"] - ablated["_caught_ids"])
        entry = {k: v for k, v in ablated.items() if not k.startswith("_")}
        entry["label"] = label
        entry["recall_delta"] = round(full["recall_pct"] - ablated["recall_pct"], 1)
        entry["errors_only_this_node_caught"] = lost
        entry["false_positives_removed"] = full["false_positives"] - ablated["false_positives"]
        report["ablations"][f"without_node_{node_id}"] = entry
        rows.append((f"without node {node_id} ({label})", ablated, entry))

    with open(ABLATION_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    width = max(len(r[0]) for r in rows) + 2
    print(f"\nNode ablation over {report['cases_scored']} scored cases "
          f"(threshold {args.threshold}, same committed run for every row)\n")
    print(f"{'configuration'.ljust(width)}{'recall':>16}{'sev-weighted':>15}{'false pos':>12}{'delta':>9}")
    print("-" * (width + 52))
    for name, res, entry in rows:
        recall = f"{res['recall_hits']}/{res['recall_possible']} ({res['recall_pct']}%)"
        delta = "-" if entry is None else f"{entry['recall_delta']:+.1f}"
        print(f"{name.ljust(width)}{recall:>16}{str(res['weighted_pct']) + '%':>15}"
              f"{res['false_positives']:>12}{delta:>9}")

    print("\nMarginal contribution per node:")
    for node_id, (source, label) in sorted(NODES.items()):
        if f"without_node_{node_id}" not in report["ablations"]:
            continue
        entry = report["ablations"][f"without_node_{node_id}"]
        lost = entry["errors_only_this_node_caught"]
        if lost:
            print(f"  node {node_id} ({label}): {len(lost)} error(s) no other node caught, "
                  f"at the cost of {entry['false_positives_removed']} false positive(s)")
            for case_id in lost:
                print(f"      - {case_id}")
        else:
            print(f"  node {node_id} ({label}): caught nothing the other nodes missed "
                  f"(it raised {entry['false_positives_removed']} of the false positives)")

    print(f"\nWritten to {ABLATION_PATH}")


if __name__ == "__main__":
    main()
