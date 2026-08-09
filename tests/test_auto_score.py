"""
Tests for eval/auto_score.py's matching heuristic - the part of an
automated scorer most likely to silently over- or under-credit a system,
so it's worth pinning down with real examples rather than trusting it by
inspection.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "eval"))

import auto_score  # noqa: E402


class TestTokensAndJaccard(unittest.TestCase):
    def test_stopwords_and_short_tokens_are_dropped(self):
        tokens = auto_score._tokens("The patient reports a dry cough")
        self.assertEqual(tokens, {"dry", "cough"})

    def test_jaccard_of_disjoint_sets_is_zero(self):
        self.assertEqual(auto_score._jaccard({"fever"}, {"cough"}), 0.0)

    def test_jaccard_of_identical_sets_is_one(self):
        self.assertEqual(auto_score._jaccard({"fever", "nausea"}, {"fever", "nausea"}), 1.0)

    def test_jaccard_with_an_empty_set_is_zero_not_an_error(self):
        self.assertEqual(auto_score._jaccard(set(), {"fever"}), 0.0)
        self.assertEqual(auto_score._jaccard(set(), set()), 0.0)


class TestIsCaught(unittest.TestCase):
    def setUp(self):
        self.gt_error = {
            "category": "fabrication",
            "claim_text": "accompanied by fever and mild nausea",
            "correct_value": "not mentioned; patient explicitly denied fever and denied nausea/vomiting",
            "transcript_evidence": "Patient said 'No fever that I've noticed'",
        }

    def test_category_match_is_sufficient_even_with_different_wording(self):
        flags = [{"claim": "completely unrelated wording here", "category": "fabrication"}]
        self.assertTrue(auto_score._is_caught(flags, self.gt_error, threshold=0.2, is_pipeline=True))

    def test_text_overlap_catches_a_miscategorized_but_correct_flag(self):
        # Same underlying claim, but the classifier picked a different
        # category - should still count as "caught" via text overlap.
        flags = [{"claim": "note reports fever and nausea not in transcript", "category": "distortion"}]
        self.assertTrue(auto_score._is_caught(flags, self.gt_error, threshold=0.2, is_pipeline=True))

    def test_unrelated_flag_is_not_caught(self):
        flags = [{"claim": "blood pressure reading differs from transcript", "category": "distortion"}]
        self.assertFalse(auto_score._is_caught(flags, self.gt_error, threshold=0.2, is_pipeline=True))

    def test_empty_flag_list_is_never_caught(self):
        self.assertFalse(auto_score._is_caught([], self.gt_error, threshold=0.2, is_pipeline=True))

    def test_baseline_issues_use_issue_and_explanation_fields(self):
        issues = [{"issue": "fever and nausea", "explanation": "not supported by the transcript"}]
        self.assertTrue(auto_score._is_caught(issues, self.gt_error, threshold=0.2, is_pipeline=False))

    def test_higher_threshold_can_flip_a_borderline_match_to_uncaught(self):
        # One shared token ("fever") out of otherwise distinct wording -
        # low threshold catches it, a strict threshold doesn't. Documents
        # that the threshold is a real, visible knob, not an implementation
        # detail nobody can see the effect of.
        flags = [{"claim": "vital signs show elevated fever reading", "category": "numeric_medication_error"}]
        caught_loose = auto_score._is_caught(flags, self.gt_error, threshold=0.05, is_pipeline=True)
        caught_strict = auto_score._is_caught(flags, self.gt_error, threshold=0.9, is_pipeline=True)
        self.assertTrue(caught_loose)
        self.assertFalse(caught_strict)


if __name__ == "__main__":
    unittest.main()
