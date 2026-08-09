"""
Tests for the failover/fairness logic in llm_router.py, using a FAKE
dispatch function - no real API calls, no quota spent. This is what makes
it possible to test the sticky-downgrade behavior (which needs a real
quota error to trigger) without ever hitting a live rate limit.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import llm_router  # noqa: E402

_ENV_KEYS = ("GEMINI_API_KEY", "GROQ_API_KEY", "FEATHERLESS_API_KEY", "FEATHERLESS_AI_API_KEY")


class QuotaError(Exception):
    """Stands in for a real 429/503 from any provider - llm_router only
    looks at .status_code (or, for Gemini, isinstance(genai_errors.APIError)),
    so this is enough to trigger failover without a real SDK exception."""
    def __init__(self, status_code):
        super().__init__(f"fake quota error {status_code}")
        self.status_code = status_code


class RouterTestBase(unittest.TestCase):
    """Snapshots and restores the real environment and llm_router's module-
    level sticky state around every test, so tests can freely set/unset keys
    and downgrade the tier without leaking into other tests or the real
    environment."""

    def setUp(self):
        self._env_snapshot = {k: os.environ.get(k) for k in _ENV_KEYS}
        for k in _ENV_KEYS:
            os.environ.pop(k, None)
        llm_router.reset_core_tier()
        llm_router._warned_missing_key.clear()

    def tearDown(self):
        for k, v in self._env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        llm_router.reset_core_tier()
        llm_router._warned_missing_key.clear()


class TestCoreReasoningFailover(RouterTestBase):
    def setUp(self):
        super().setUp()
        os.environ["GEMINI_API_KEY"] = "fake-gemini-key"
        os.environ["GROQ_API_KEY"] = "fake-groq-key"
        self.chain = [
            {"provider": "gemini", "model": "m1"},
            {"provider": "groq", "model": "m2"},
        ]

    def test_downgrade_is_sticky_across_separate_calls(self):
        calls = []

        def fake_dispatch(provider, model, prompt, json_mode):
            calls.append(provider)
            if provider == "gemini":
                raise QuotaError(429)
            return f"response from {provider}"

        with mock.patch.object(llm_router, "_dispatch", side_effect=fake_dispatch):
            result, provider, model = llm_router.call_core_reasoning("case 1", chain=self.chain)
            self.assertEqual(provider, "groq")
            self.assertEqual(calls, ["gemini", "groq"])

            calls.clear()
            result2, provider2, model2 = llm_router.call_core_reasoning("case 2", chain=self.chain)
            self.assertEqual(provider2, "groq")
            # gemini must NOT be retried for case 2 - the tier only moves
            # forward, it doesn't reset between calls within a run.
            self.assertEqual(calls, ["groq"])

    def test_no_provider_has_a_key_raises_a_distinct_error(self):
        for k in _ENV_KEYS:
            os.environ.pop(k, None)  # undo setUp's fake keys for this test

        with self.assertRaises(RuntimeError) as ctx:
            llm_router.call_core_reasoning("prompt", chain=self.chain)
        self.assertIn("No core-reasoning provider could be tried", str(ctx.exception))

    def test_all_providers_failing_raises_a_different_error_than_no_keys(self):
        def always_quota_error(provider, model, prompt, json_mode):
            raise QuotaError(503)

        with mock.patch.object(llm_router, "_dispatch", side_effect=always_quota_error):
            with self.assertRaises(RuntimeError) as ctx:
                llm_router.call_core_reasoning("prompt", chain=self.chain)
        msg = str(ctx.exception)
        self.assertIn("exhausted or unavailable", msg)
        self.assertNotIn("No core-reasoning provider could be tried", msg)

    def test_non_quota_error_is_not_failed_over(self):
        # A malformed prompt or bad response shape is a real bug, not a
        # capacity problem - it must surface immediately, not get masked by
        # silently trying the next provider.
        calls = []

        def fake_dispatch(provider, model, prompt, json_mode):
            calls.append(provider)
            raise ValueError("model returned malformed JSON")

        with mock.patch.object(llm_router, "_dispatch", side_effect=fake_dispatch):
            with self.assertRaises(ValueError):
                llm_router.call_core_reasoning("prompt", chain=self.chain)
        self.assertEqual(calls, ["gemini"])  # never reached groq


class TestMechanicalChainIndependence(RouterTestBase):
    def test_mechanical_chain_ignores_core_reasoning_tier_state(self):
        os.environ["GEMINI_API_KEY"] = "fake-gemini-key"
        os.environ["GROQ_API_KEY"] = "fake-groq-key"
        core_chain = [{"provider": "gemini", "model": "m1"}, {"provider": "groq", "model": "m2"}]
        mechanical_chain = [{"provider": "gemini", "model": "extract-model"}]

        def fake_dispatch(provider, model, prompt, json_mode):
            if provider == "gemini" and model == "m1":
                raise QuotaError(429)
            return "ok"

        with mock.patch.object(llm_router, "_dispatch", side_effect=fake_dispatch):
            # Downgrade the core-reasoning tier away from gemini.
            _, provider, _ = llm_router.call_core_reasoning("case", chain=core_chain)
            self.assertEqual(provider, "groq")

        # The mechanical chain has its own gemini entry and must still try
        # it - it has no shared state with the core-reasoning tier.
        calls = []

        def fake_dispatch_2(provider, model, prompt, json_mode):
            calls.append(provider)
            return "ok"

        with mock.patch.object(llm_router, "_dispatch", side_effect=fake_dispatch_2):
            llm_router.call_mechanical(mechanical_chain, "prompt")
        self.assertEqual(calls, ["gemini"])


if __name__ == "__main__":
    unittest.main()
