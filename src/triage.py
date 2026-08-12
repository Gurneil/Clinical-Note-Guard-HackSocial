"""
Node 6b: the order a human reads the flags in.

THE PROBLEM THIS ADDRESSES
--------------------------
The pipeline's measured cost is precision: 15 false positives across 6
clean control notes (~2.5/note) against the baseline's 11 (~1.8/note).
docs/ARCHITECTURE.md discloses that honestly and leaves it there.

But "false positives per note" is the wrong unit for the thing that
actually matters. A reviewer does not experience a false-positive rate;
they experience *how many wrong flags they read before they reach a real
one*. Two systems with identical FP counts are not equally expensive to
review if one puts the dangerous flag first and the other buries it
eighth.

So rather than only reporting the precision cost, this orders the flags so
the reviewer meets the highest-consequence ones first. Ranking cannot
remove a false positive - it changes what a reviewer pays to find the real
error, which is the cost that lands on a clinician.

THE ORDER, AND WHY
------------------
1. Severity, from taxonomy.json - never invented here. numeric/medication
   and negation are critical because a small text change carries outsized
   clinical risk; that ranking already exists in the taxonomy and this
   module reads it rather than duplicating it.
2. Deterministic before probabilistic, within a severity band. Node 4's
   regex raised ZERO false positives across every control note (see
   eval/ablation.py) - it is the only detector here with no precision
   cost, so when it and the LLM both flag at the same severity, its flag
   is the better use of the reviewer's first look.
3. Unverifiable (node 3b) sits directly below same-severity contradictions
   but above lower-severity ones: "the source audio is unreliable here"
   needs a person more urgently than a medium-severity note quibble, but
   less than a confirmed critical mismatch.
4. Original pipeline order for anything still tied, so ranking is stable
   and reproducible rather than dependent on dict iteration.

WHAT THIS DOES NOT DO
---------------------
It does not drop, hide, suppress, or auto-dismiss anything. Every flag the
pipeline raised is still in the list and still requires a human decision -
node 7 is unchanged. Ranking a list is not filtering it, and a
documentation-QA tool that quietly hid its low-confidence flags would be
making exactly the kind of silent judgement this project exists to prevent.
"""
import json
import os

_TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "taxonomy.json")

# Same scale auto_score.py uses for severity-weighted recall, so "severity"
# means one thing across the whole repo.
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_UNKNOWN_SEVERITY = 2  # treat an unrecognised category as medium, not last

# Lower sorts earlier. Deterministic first: it is the only detector with a
# measured zero false-positive rate.
SOURCE_RANK = {
    "deterministic_check": 0,
    "llm_pipeline": 1,
    "asr_confidence": 2,
    "llm_pipeline_omission": 3,
}

_severity_by_category = None


def _severities() -> dict:
    global _severity_by_category
    if _severity_by_category is None:
        with open(_TAXONOMY_PATH, encoding="utf-8") as f:
            taxonomy = json.load(f)
        _severity_by_category = {c["id"]: c["severity"] for c in taxonomy["categories"]}
    return _severity_by_category


def severity_of(flag: dict) -> str:
    """A flag's severity, from the taxonomy. transcript_uncertainty is not a
    taxonomy category by design (see taxonomy.json's comment) - it is ranked
    high because unreliable source audio under a clinical claim warrants a
    person's attention, without claiming to be a note-error category."""
    category = flag.get("category")
    if category == "transcript_uncertainty":
        return "high"
    return _severities().get(category, "medium")


def rank_flags(flags: list) -> list:
    """Review order. Returns a new list; the input is not mutated, so
    `all_flags` stays in pipeline order and every committed number that
    iterates it is provably unaffected."""
    decorated = []
    for position, flag in enumerate(flags or []):
        severity = severity_of(flag)
        decorated.append((
            SEVERITY_RANK.get(severity, _UNKNOWN_SEVERITY),
            SOURCE_RANK.get(flag.get("source"), 9),
            position,                      # stable: ties keep pipeline order
            flag,
        ))
    decorated.sort(key=lambda item: item[:3])
    return [item[3] for item in decorated]


def triage_summary(flags: list) -> dict:
    """What a reviewer is walking into, before they read anything."""
    ranked = rank_flags(flags)
    counts = {}
    for flag in ranked:
        severity = severity_of(flag)
        counts[severity] = counts.get(severity, 0) + 1
    return {
        "total": len(ranked),
        "by_severity": counts,
        "critical_first": [f.get("claim") or f.get("flagged_value") for f in ranked[:3]],
        "highest_severity": severity_of(ranked[0]) if ranked else None,
    }
