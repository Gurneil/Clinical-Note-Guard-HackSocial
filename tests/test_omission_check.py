"""
Tests for the omission-detection node (extract_transcript_facts +
omission_check_batch), added because taxonomy.json defines an "omission"
category that the original pipeline had no way to actually detect -
entailment_check_batch only ever checks note-claims against the
transcript, never the reverse direction. No real API calls: llm_router's
call_mechanical is monkeypatched directly, the same pattern used in
test_llm_router.py.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import llm_router  # noqa: E402
import pipeline  # noqa: E402


class TestExtractTranscriptFacts(unittest.TestCase):
    def test_returns_the_list_the_model_produced(self):
        fake_facts = ["Patient denies chest pain", "Blood pressure 128/82"]
        with mock.patch.object(llm_router, "call_mechanical", return_value=fake_facts):
            result = pipeline.extract_transcript_facts("some transcript")
        self.assertEqual(result, fake_facts)

    def test_non_list_response_raises(self):
        with mock.patch.object(llm_router, "call_mechanical", return_value={"not": "a list"}):
            with self.assertRaises(ValueError):
                pipeline.extract_transcript_facts("some transcript")


class TestOmissionCheckBatch(unittest.TestCase):
    def test_empty_fact_list_short_circuits_with_no_call(self):
        with mock.patch.object(llm_router, "call_mechanical") as mocked:
            result = pipeline.omission_check_batch([], "some note")
        self.assertEqual(result, [])
        mocked.assert_not_called()

    def test_correct_count_returns_the_model_verdicts_in_order(self):
        facts = ["fact A", "fact B", "fact C"]
        fake_response = [
            {"fact_number": 1, "status": "mentioned"},
            {"fact_number": 2, "status": "omitted"},
            {"fact_number": 3, "status": "mentioned"},
        ]
        with mock.patch.object(llm_router, "call_mechanical", return_value=fake_response):
            result = pipeline.omission_check_batch(facts, "some note")
        self.assertEqual(result, fake_response)

    def test_count_mismatch_raises_rather_than_silently_accepting(self):
        # Mirrors the exact coverage guarantee entailment_check_batch has -
        # a model that skips or merges facts when batching must be caught,
        # not silently trusted.
        facts = ["fact A", "fact B", "fact C"]
        fake_response = [{"fact_number": 1, "status": "mentioned"}]  # only 1, not 3
        with mock.patch.object(llm_router, "call_mechanical", return_value=fake_response):
            with self.assertRaises(ValueError) as ctx:
                pipeline.omission_check_batch(facts, "some note")
        self.assertIn("Expected exactly 3", str(ctx.exception))


class TestRunGuardIncludesOmissionFlags(unittest.TestCase):
    """End-to-end wiring check for run_guard(), with every LLM call faked."""

    def test_an_omitted_fact_produces_an_omission_flag_in_all_flags(self):
        def fake_call_mechanical(chain, prompt, json_mode=False):
            # Matched on short, single-line fragments only - the real prompts
            # wrap across lines, so a multi-word substring spanning a
            # newline would never match (caught by this test failing the
            # first time it was written).
            if "independently-checkable" in prompt:
                return ["Patient takes lisinopril 10mg"]
            if "clinically relevant facts" in prompt:
                return ["Patient has a penicillin allergy"]
            if "checking whether each" in prompt:
                return [{"fact_number": 1, "status": "omitted"}]
            if "Classify each" in prompt:
                return []
            raise AssertionError(f"unexpected mechanical prompt: {prompt[:80]!r}")

        def fake_call_core_reasoning(prompt, json_mode=False, chain=None):
            # One claim, "supported" - so no entailment flags, only the
            # omission flag should end up in all_flags.
            return [{"claim_number": 1, "status": "supported", "evidence": "..."}], "fake-provider", "fake-model"

        with mock.patch.object(llm_router, "call_mechanical", side_effect=fake_call_mechanical), \
             mock.patch.object(llm_router, "call_core_reasoning", side_effect=fake_call_core_reasoning):
            result = pipeline.run_guard("some transcript", "some note")

        self.assertEqual(len(result["omission_flags"]), 1)
        self.assertEqual(result["omission_flags"][0]["category"], "omission")
        self.assertIn(result["omission_flags"][0], result["all_flags"])
        # The entailment-side flags must be empty - the only flag here is omission.
        self.assertEqual(result["llm_flags"], [])


if __name__ == "__main__":
    unittest.main()
