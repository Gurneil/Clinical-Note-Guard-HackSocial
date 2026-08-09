"""
Automated (non-blind) scoring proxy for raw_outputs.json.

compute_metrics.py requires a human to grade scorecard_blind.csv by hand,
which is the methodologically preferred path (see "Evaluation
methodology" in docs/ARCHITECTURE.md) but isn't always available - e.g.
running this end-to-end without a person free to sit down and grade 18
cases twice (pipeline + baseline). This script scores raw_outputs.json
directly against ground_truth using keyword/phrase overlap instead of a
person's judgment.

THIS IS A PROXY, NOT A REPLACEMENT. Automated string overlap can both
over-credit a system (flagged something that shares words with the
target error but isn't really the same claim) and under-credit one
(caught the right thing but phrased it in genuinely different words).
Numbers from this script should be labeled as automated/proxy wherever
they're reported, and a real blind grading pass is the recommended path
before treating any number as a final submission result.

Matching heuristic (documented so it can be judged, not just trusted):
  - CAUGHT if any flag/issue the system raised either:
      (a) has category == the ground-truth error's category, exactly, or
      (b) has token-overlap (Jaccard over lowercased, stopword-filtered
          words) >= AUTO_SCORE_THRESHOLD against the ground-truth error's
          claim_text + correct_value + transcript_evidence combined.
  - False positives on clean control cases: every flag/issue raised on a
    case with has_error=False counts as one false positive - there's
    nothing to overlap-match against on a clean case, so no heuristic is
    needed there, just a raw count.

Usage:
    python auto_score.py
    python auto_score.py --include-mismatches
    python auto_score.py --threshold 0.25
"""
import argparse
import json
import os
import re

SEVERITY_WEIGHT = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
AUTO_SCORE_THRESHOLD = 0.2

BASE = os.path.dirname(__file__)
TAXONOMY_PATH = os.path.join(BASE, "..", "taxonomy.json")
RAW_OUT_PATH = os.path.join(BASE, "raw_outputs.json")
AUTO_SCORECARD_PATH = os.path.join(BASE, "auto_scorecard.json")

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "was", "were", "be", "been",
    "of", "to", "in", "on", "at", "for", "with", "as", "this", "that", "it",
    "not", "no", "any", "note", "notes", "transcript", "patient", "reports",
    "report", "reported", "denies", "denied", "endorses", "stated", "said",
    "history", "during", "encounter", "not_mentioned", "supported",
    "contradicted", "mentioned", "omitted", "specified",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set:
    if not text:
        return set()
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) >= 3 and t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _ground_truth_tokens(gt_error: dict) -> set:
    combined = " ".join([
        gt_error.get("claim_text", ""),
        gt_error.get("correct_value", ""),
        gt_error.get("transcript_evidence", ""),
    ])
    return _tokens(combined)


def _pipeline_flag_text_and_category(flag: dict):
    text = " ".join([
        str(flag.get("claim") or flag.get("flagged_value") or ""),
        str(flag.get("explanation") or flag.get("reason") or ""),
    ])
    return text, flag.get("category")


def _baseline_issue_text(item: dict) -> str:
    return " ".join([str(item.get("issue") or ""), str(item.get("explanation") or "")])


def _is_caught(flags_or_issues, gt_error: dict, threshold: float, is_pipeline: bool) -> bool:
    gt_tokens = _ground_truth_tokens(gt_error)
    gt_category = gt_error.get("category")
    for item in flags_or_issues:
        if is_pipeline:
            text, category = _pipeline_flag_text_and_category(item)
            if category == gt_category:
                return True
        else:
            text = _baseline_issue_text(item)
        if _jaccard(_tokens(text), gt_tokens) >= threshold:
            return True
    return False


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

    results = {"pipeline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                             "weighted_possible": 0.0, "false_positives": 0,
                             "control_cases": 0},
               "baseline": {"hits": 0, "possible": 0, "weighted_hits": 0.0,
                            "weighted_possible": 0.0, "false_positives": 0,
                            "control_cases": 0}}

    excluded_cases = []
    per_case_detail = []

    for row in raw_outputs:
        case_id = row["case_id"]
        if row.get("fairness_mismatch") and not args.include_mismatches:
            excluded_cases.append(case_id)
            continue

        gt = row["ground_truth"]
        pipeline_flags = row["pipeline_result"]["all_flags"]
        baseline_issues = row["baseline_result"]

        detail = {"case_id": case_id}

        if gt["has_error"]:
            gt_error = gt["injected_errors"][0]
            severity = taxonomy[gt_error["category"]]["severity"]
            weight = SEVERITY_WEIGHT.get(severity, 1)

            pipeline_caught = _is_caught(pipeline_flags, gt_error, args.threshold, is_pipeline=True)
            baseline_caught = _is_caught(baseline_issues, gt_error, args.threshold, is_pipeline=False)

            for system, caught in (("pipeline", pipeline_caught), ("baseline", baseline_caught)):
                results[system]["possible"] += 1
                results[system]["weighted_possible"] += weight
                if caught:
                    results[system]["hits"] += 1
                    results[system]["weighted_hits"] += weight

            detail["target_category"] = gt_error["category"]
            detail["pipeline_caught"] = pipeline_caught
            detail["baseline_caught"] = baseline_caught
        else:
            results["pipeline"]["control_cases"] += 1
            results["baseline"]["control_cases"] += 1
            results["pipeline"]["false_positives"] += len(pipeline_flags)
            results["baseline"]["false_positives"] += len(baseline_issues)
            detail["pipeline_false_positives"] = len(pipeline_flags)
            detail["baseline_false_positives"] = len(baseline_issues)

        per_case_detail.append(detail)

    with open(AUTO_SCORECARD_PATH, "w", encoding="utf-8") as f:
        json.dump({"threshold": args.threshold, "cases": per_case_detail}, f, indent=2)
    print(f"Wrote per-case detail -> {AUTO_SCORECARD_PATH}\n")

    if excluded_cases:
        print(f"EXCLUDED {len(excluded_cases)} fairness-mismatched case(s): {sorted(excluded_cases)}")
        print("(pass --include-mismatches to score them anyway)\n")

    print("=" * 60)
    print(f"RESULTS (AUTOMATED PROXY SCORING - threshold={args.threshold})")
    print("This is NOT blind human grading. See docs/ARCHITECTURE.md")
    print("'Evaluation methodology' before citing these numbers as final.")
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


if __name__ == "__main__":
    main()
