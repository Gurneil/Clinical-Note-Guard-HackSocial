"""
Node 3b (transcript confidence) - the rule that a verdict is only as good
as the audio it was checked against.

No API calls and no audio files: the ASR result shape is constructed
directly, which is the whole reason locate/flag logic lives in a pure
module. Everything here is the real function from transcript_confidence.py,
never a reimplementation.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import transcript_confidence as tc  # noqa: E402


def seg(text, start, end, confidence=0.97, no_speech=0.01):
    """A normalised segment as src/transcribe.py would emit it."""
    return {"text": text, "start": start, "end": end,
            "confidence": confidence, "no_speech_prob": no_speech,
            "avg_logprob": None}


CLEAR = seg("Are you still taking the lisinopril 10 milligrams once a day", 38.0, 44.0)
SHAKY = seg("Are you still taking the lisinopril 10 milligrams once a day",
            38.0, 44.0, confidence=0.31)


class TestUnreliability(unittest.TestCase):
    def test_confident_segment_is_reliable(self):
        self.assertFalse(tc.is_unreliable(CLEAR))

    def test_low_confidence_segment_is_unreliable(self):
        self.assertTrue(tc.is_unreliable(SHAKY))

    def test_probable_non_speech_is_unreliable_even_when_confident(self):
        self.assertTrue(tc.is_unreliable(seg("...", 1.0, 2.0, confidence=0.99, no_speech=0.9)))

    def test_unscored_segment_is_treated_as_reliable(self):
        """Hand-written benchmark transcripts carry no confidence at all.
        Scoring their absence as unreliable would flag all 60 cases."""
        self.assertFalse(tc.is_unreliable({"text": "x", "start": 0, "end": 1,
                                           "confidence": None, "no_speech_prob": None}))


class TestLocateEvidence(unittest.TestCase):
    def test_finds_the_segment_containing_the_quote(self):
        found = tc.locate_evidence("lisinopril 10 milligrams", [CLEAR])
        self.assertEqual(len(found), 1)

    def test_matching_ignores_case_and_whitespace(self):
        found = tc.locate_evidence("  LISINOPRIL   10 Milligrams ", [CLEAR])
        self.assertEqual(len(found), 1)

    def test_finds_a_quote_spanning_two_segments(self):
        a = seg("it's reading 128", 60.0, 62.0)
        b = seg("over 82, that's an improvement", 62.0, 65.0)
        found = tc.locate_evidence("128 over 82", [a, b])
        self.assertEqual(len(found), 2)

    def test_unlocatable_evidence_returns_nothing(self):
        self.assertEqual(tc.locate_evidence("discussed the patient's travel plans", [CLEAR]), [])

    def test_a_couple_of_shared_words_is_not_a_match(self):
        """The fallback must not attribute a claim to unrelated audio just
        because they share common words."""
        found = tc.locate_evidence("patient has been taking their medication regularly",
                                   [seg("the weather has been fine", 0.0, 2.0)])
        self.assertEqual(found, [])


class TestHighRiskTokens(unittest.TestCase):
    def test_detects_doses(self):
        self.assertIn("10 milligrams", tc.high_risk_tokens("lisinopril 10 milligrams daily"))

    def test_detects_blood_pressure(self):
        self.assertTrue(tc.high_risk_tokens("blood pressure 128 over 82"))

    def test_detects_negations(self):
        self.assertTrue(tc.high_risk_tokens("patient denies chest pain"))

    def test_plain_claim_has_no_high_risk_tokens(self):
        self.assertEqual(tc.high_risk_tokens("patient appeared comfortable"), [])


class TestUnverifiableFlags(unittest.TestCase):
    claims = ["Lisinopril dose is 10 mg once daily"]
    supported = [{"status": "supported", "evidence": "lisinopril 10 milligrams once a day"}]

    def test_supported_claim_on_clear_audio_is_left_alone(self):
        self.assertEqual(tc.unverifiable_flags(self.claims, self.supported, [CLEAR]), [])

    def test_supported_claim_on_shaky_audio_becomes_unverifiable(self):
        """The core rule: a pass validated against audio the recogniser was
        guessing at is not a pass."""
        flags = tc.unverifiable_flags(self.claims, self.supported, [SHAKY])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["status"], "unverifiable")
        self.assertEqual(flags[0]["original_status"], "supported")
        self.assertEqual(flags[0]["category"], "transcript_uncertainty")
        self.assertEqual(flags[0]["source"], "asr_confidence")

    def test_flag_tells_the_human_where_to_listen(self):
        flags = tc.unverifiable_flags(self.claims, self.supported, [SHAKY])
        self.assertEqual(flags[0]["audio_span"], "00:38-00:44")
        self.assertIn("00:38-00:44", flags[0]["action"])

    def test_flag_names_the_high_risk_token(self):
        flags = tc.unverifiable_flags(self.claims, self.supported, [SHAKY])
        self.assertTrue(flags[0]["high_risk_tokens"])

    def test_contradicted_claim_on_shaky_audio_is_also_downgraded(self):
        """The transcript could be the wrong one, not the note."""
        results = [{"status": "contradicted", "evidence": "lisinopril 10 milligrams once a day"}]
        flags = tc.unverifiable_flags(self.claims, results, [SHAKY])
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["original_status"], "contradicted")

    def test_not_mentioned_is_not_downgraded(self):
        """It rests on the absence of evidence, so there is no segment whose
        confidence could be attributed to it."""
        results = [{"status": "not_mentioned", "evidence": ""}]
        self.assertEqual(tc.unverifiable_flags(self.claims, results, [SHAKY]), [])

    def test_unlocatable_evidence_raises_no_flag(self):
        """Unattributable is not the same as unreliable - staying quiet is
        the honest behaviour when the module knows least."""
        results = [{"status": "supported", "evidence": "something never said aloud"}]
        self.assertEqual(tc.unverifiable_flags(self.claims, results, [SHAKY]), [])

    def test_no_segments_means_no_flags(self):
        """Text-only runs (the whole committed benchmark) are unaffected."""
        self.assertEqual(tc.unverifiable_flags(self.claims, self.supported, []), [])

    def test_only_the_claim_on_bad_audio_is_flagged(self):
        claims = ["Lisinopril dose is 10 mg once daily", "Blood pressure was 128 over 82"]
        results = [
            {"status": "supported", "evidence": "lisinopril 10 milligrams once a day"},
            {"status": "supported", "evidence": "it's reading 128 over 82"},
        ]
        clean_bp = seg("okay, it's reading 128 over 82", 60.0, 64.0)
        flags = tc.unverifiable_flags(claims, results, [SHAKY, clean_bp])
        self.assertEqual(len(flags), 1)
        self.assertIn("Lisinopril", flags[0]["claim"])


class TestReliabilitySummary(unittest.TestCase):
    def test_summarises_how_much_audio_is_untrustworthy(self):
        summary = tc.transcript_reliability_summary([CLEAR, SHAKY])
        self.assertEqual(summary["segments"], 2)
        self.assertEqual(summary["segments_unreliable"], 1)
        self.assertEqual(summary["spans_to_review"], ["00:38-00:44"])

    def test_all_clear_audio_reports_nothing_to_review(self):
        summary = tc.transcript_reliability_summary([CLEAR])
        self.assertEqual(summary["segments_unreliable"], 0)
        self.assertEqual(summary["unreliable_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
