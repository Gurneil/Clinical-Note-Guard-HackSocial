"""
Severity ranking (src/triage.py).

Note that node 6b is NOT wired into the pipeline: eval/review_burden.py
measured it against the committed run and found it changes nothing (see
docs/ARCHITECTURE.md, "a mitigation that didn't work"). The module is kept
because the measurement is part of the submission's argument, and these
tests exist so the thing that was measured is the thing that is described -
an untested module would make that claim unverifiable.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import triage  # noqa: E402


def flag(category, source="llm_pipeline", claim="c"):
    return {"category": category, "source": source, "claim": claim}


class TestSeverity(unittest.TestCase):
    def test_severity_comes_from_the_taxonomy(self):
        self.assertEqual(triage.severity_of(flag("numeric_medication_error")), "critical")
        self.assertEqual(triage.severity_of(flag("negation_error")), "critical")
        self.assertEqual(triage.severity_of(flag("fabrication")), "high")
        self.assertEqual(triage.severity_of(flag("omission")), "medium")

    def test_transcript_uncertainty_is_not_a_taxonomy_category(self):
        """It is deliberately outside taxonomy.json - ranked, not classified."""
        self.assertEqual(triage.severity_of(flag("transcript_uncertainty")), "high")

    def test_unknown_category_defaults_to_medium_not_last(self):
        self.assertEqual(triage.severity_of(flag("something_new")), "medium")


class TestRanking(unittest.TestCase):
    def test_critical_outranks_medium(self):
        ranked = triage.rank_flags([flag("omission"), flag("numeric_medication_error")])
        self.assertEqual(ranked[0]["category"], "numeric_medication_error")

    def test_deterministic_outranks_llm_at_equal_severity(self):
        """Node 4 raised zero false positives on every control note, so its
        flag is the better use of the reviewer's first look."""
        ranked = triage.rank_flags([
            flag("numeric_medication_error", "llm_pipeline", "llm"),
            flag("numeric_medication_error", "deterministic_check", "regex"),
        ])
        self.assertEqual(ranked[0]["claim"], "regex")

    def test_ties_keep_pipeline_order(self):
        a, b = flag("omission", claim="a"), flag("omission", claim="b")
        self.assertEqual([f["claim"] for f in triage.rank_flags([a, b])], ["a", "b"])

    def test_ranking_does_not_mutate_the_input(self):
        """all_flags must stay in pipeline order - every committed number
        iterates it, and a silent reorder would be invisible."""
        original = [flag("omission", claim="first"), flag("negation_error", claim="second")]
        triage.rank_flags(original)
        self.assertEqual(original[0]["claim"], "first")

    def test_nothing_is_dropped(self):
        """Ranking a list is not filtering it. Every flag still needs a human."""
        flags = [flag("omission"), flag("fabrication"), flag("negation_error")]
        self.assertEqual(len(triage.rank_flags(flags)), 3)

    def test_empty_list(self):
        self.assertEqual(triage.rank_flags([]), [])
        self.assertEqual(triage.rank_flags(None), [])


class TestSummary(unittest.TestCase):
    def test_counts_by_severity(self):
        summary = triage.triage_summary([
            flag("numeric_medication_error"), flag("omission"), flag("omission")])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_severity"]["critical"], 1)
        self.assertEqual(summary["by_severity"]["medium"], 2)
        self.assertEqual(summary["highest_severity"], "critical")

    def test_empty_summary_has_no_highest(self):
        self.assertIsNone(triage.triage_summary([])["highest_severity"])


if __name__ == "__main__":
    unittest.main()
