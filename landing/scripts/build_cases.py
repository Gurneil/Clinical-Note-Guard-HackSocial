"""
Bakes the benchmark into landing/src/data/cases.json so the guard console can
run any of the 60 synthetic conversations in the browser.

The flags shown are NOT simulated. They are the pipeline's real output for
that case, lifted from eval/raw_outputs.json - the same committed run every
number in docs/ARCHITECTURE.md comes from. Selecting a case in the browser
shows what the pipeline actually found when it ran, so the page cannot
drift from the evidence.

Two cases errored out during that run and have no output. They are included
anyway, marked so the page can say "this case errored during the eval"
rather than silently pretending it was clean - that failure is in the
reported numbers and hiding it here would be inconsistent.

(Was frontend/build_cases.py, which also emitted a window.GUARD_CASES bundle
for the old static site. That site has been replaced by landing/.)

Regenerate after any new eval run:
    python landing/scripts/build_cases.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(BASE)
ROOT = os.path.dirname(LANDING)
OUT = os.path.join(LANDING, "src", "data", "cases.json")


def main():
    with open(os.path.join(ROOT, "data", "test_cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    with open(os.path.join(ROOT, "eval", "raw_outputs.json"), encoding="utf-8") as f:
        runs = {r["case_id"]: r for r in json.load(f)}

    out = []
    for case in cases:
        run = runs.get(case["id"], {})
        pipeline = run.get("pipeline_result") or {}
        gt = case["ground_truth"]
        planted = (gt.get("injected_errors") or [{}])[0] if gt.get("has_error") else None

        flags = []
        for flag in pipeline.get("all_flags", []):
            flags.append({
                "claim": flag.get("claim") or flag.get("flagged_value") or "",
                "category": flag.get("category", ""),
                "why": flag.get("explanation") or flag.get("reason") or "",
                "evidence": flag.get("evidence", ""),
                "source": flag.get("source", ""),
            })

        out.append({
            "id": case["id"],
            "specialty": case.get("specialty", ""),
            "transcript": case["transcript"],
            "note": case["note_under_test"],
            "claims": pipeline.get("claims_checked", []),
            "flags": flags,
            "baseline": [i.get("issue", "") for i in (run.get("baseline_result") or [])],
            "model": run.get("core_reasoning_model", ""),
            "hasError": bool(gt.get("has_error")),
            "planted": ({"category": planted.get("category", ""),
                         "text": planted.get("claim_text", ""),
                         "correct": planted.get("correct_value", "")} if planted else None),
            "errored": "error" in run,
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    errored = sum(1 for c in out if c["errored"])
    print(f"wrote {OUT}")
    print(f"  {len(out)} cases, {sum(1 for c in out if c['flags'])} with committed flags, "
          f"{errored} errored during the eval")
    print(f"  {os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
