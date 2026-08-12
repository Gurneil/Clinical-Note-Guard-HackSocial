"""
How many wrong flags does a reviewer read before reaching the real one?

WHY THIS METRIC EXISTS
----------------------
The pipeline's honest weakness is precision: ~2.5 false positives per clean
note against the baseline's ~1.8. That number is reported in
docs/ARCHITECTURE.md and is not in dispute.

But it is the wrong unit for the cost that actually lands on a person. A
clinician does not experience a false-positive rate. They open a list and
read down it, and what costs them is the number of items they read before
they hit the one that matters. A system that raises 5 flags with the real
error first is cheaper to review than one that raises 3 with the real error
last - even though the second has the better FP rate.

So this measures rank, not count:

  - hit@1 / hit@3 : was the planted error inside the first 1 / first 3
                    flags the reviewer would see?
  - mean rank     : average position of the planted error in the list
  - flags read    : how many items a reviewer reads before reaching it

and it computes each of those twice - once in the pipeline's natural
emission order, once in src/triage.py's severity ranking - so the ranking
is held to a measurement rather than asserted to help.

If ranking does not improve these numbers, this script will say so, and
node 6b should be deleted rather than defended.

No API calls: this re-reads the committed raw_outputs.json, the same run
every other number in this repo comes from.

Usage:
    python review_burden.py
    python review_burden.py --threshold 0.25
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from auto_score import AUTO_SCORE_THRESHOLD, RAW_OUT_PATH, _is_caught  # noqa: E402
from triage import rank_flags, severity_of  # noqa: E402

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "review_burden_results.json")


def rank_of_target(flags, gt_error, threshold):
    """1-based position of the first flag that matches the planted error, or
    None if the system never caught it. Uses auto_score's own matcher, so
    'caught' means exactly what it means everywhere else in this repo."""
    for position, flag in enumerate(flags, start=1):
        if _is_caught([flag], gt_error, threshold, is_pipeline=True):
            return position
    return None


def summarise(ranks, total_cases):
    found = [r for r in ranks if r is not None]
    if not found:
        return {"caught": 0, "hit_at_1": 0, "hit_at_3": 0,
                "mean_rank": None, "mean_flags_read_first": None}
    return {
        "caught": len(found),
        "of_cases": total_cases,
        "hit_at_1": sum(1 for r in found if r <= 1),
        "hit_at_3": sum(1 for r in found if r <= 3),
        "mean_rank": round(sum(found) / len(found), 2),
        # what the reviewer actually pays: items read before the real one
        "mean_flags_read_first": round(sum(r - 1 for r in found) / len(found), 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=AUTO_SCORE_THRESHOLD)
    args = parser.parse_args()

    with open(RAW_OUT_PATH, encoding="utf-8") as f:
        raw_outputs = json.load(f)

    natural, ranked, per_case = [], [], []

    for row in raw_outputs:
        if "error" in row or row.get("fairness_mismatch"):
            continue
        gt = row["ground_truth"]
        if not gt["has_error"]:
            continue

        gt_error = gt["injected_errors"][0]
        flags = row["pipeline_result"]["all_flags"]
        if not flags:
            continue

        r_nat = rank_of_target(flags, gt_error, args.threshold)
        r_rank = rank_of_target(rank_flags(flags), gt_error, args.threshold)
        natural.append(r_nat)
        ranked.append(r_rank)

        if r_nat is not None:
            per_case.append({
                "case_id": row["case_id"],
                "flags": len(flags),
                "rank_natural": r_nat,
                "rank_triaged": r_rank,
                "moved": (r_nat - r_rank) if r_rank is not None else None,
                "severity": severity_of(gt_error) if gt_error.get("category") else None,
            })

    nat = summarise(natural, len(natural))
    tri = summarise(ranked, len(ranked))

    print(f"\nReviewer burden over {len(natural)} cases with a planted error")
    print("(rank = position of the real error in the list the reviewer reads)\n")
    header = f"{'order':<26}{'hit@1':>8}{'hit@3':>8}{'mean rank':>12}{'read first':>13}"
    print(header)
    print("-" * len(header))
    for label, s in (("pipeline emission order", nat), ("severity-triaged", tri)):
        print(f"{label:<26}{s['hit_at_1']:>8}{s['hit_at_3']:>8}"
              f"{str(s['mean_rank']):>12}{str(s['mean_flags_read_first']):>13}")

    improved = [c for c in per_case if c["moved"] and c["moved"] > 0]
    worsened = [c for c in per_case if c["moved"] and c["moved"] < 0]

    print(f"\nmoved earlier: {len(improved)} case(s)   moved later: {len(worsened)} case(s)")
    if nat["mean_flags_read_first"] is not None and tri["mean_flags_read_first"] is not None:
        delta = nat["mean_flags_read_first"] - tri["mean_flags_read_first"]
        if delta > 0:
            print(f"\nTriage saves the reviewer {delta:.2f} wrong flag(s) per note on average, "
                  f"and puts the\nreal error in the top 3 on "
                  f"{tri['hit_at_3']}/{tri['caught']} cases vs {nat['hit_at_3']}/{nat['caught']}.")
        elif delta == 0:
            print("\nTriage changed nothing measurable. It is not earning its place.")
        else:
            print(f"\nTriage makes it WORSE by {-delta:.2f} flag(s) per note. "
                  "Do not ship this ordering.")

    report = {
        "threshold": args.threshold,
        "cases": len(natural),
        "pipeline_emission_order": nat,
        "severity_triaged": tri,
        "moved_earlier": len(improved),
        "moved_later": len(worsened),
        "per_case": sorted(per_case, key=lambda c: -(c["moved"] or 0))[:15],
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWritten to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
