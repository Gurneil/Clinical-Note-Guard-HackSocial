"""
Tests for three silent-failure bugs found in openai_compat_client.py:

1. Featherless's key used to be read from FEATHERLESS_API_KEY only, so a
   key set as FEATHERLESS_AI_API_KEY made the provider silently vanish
   from every failover chain (a missing key is a skip, not an error - so
   this failed with no visible error at all).
2. _status_code() used to substring-match "404" etc. anywhere in
   str(exception), which could misclassify an unrelated error (e.g. one
   that happens to mention a byte count or model name containing those
   digits) as that HTTP status.
3. No max_tokens was ever set, so a long batched JSON-array response
   (e.g. omission_check_batch on a case with a dozen transcript facts)
   could get silently truncated mid-string by the provider's own default
   token cap - discovered for real running run_eval.py against Groq,
   surfacing as a confusing JSONDecodeError with finish_reason="length"
   nowhere visible in the error message.

Run:
    D:\\Python312\\python.exe -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import openai  # noqa: E402
import openai_compat_client  # noqa: E402

_ENV_KEYS = ("FEATHERLESS_API_KEY", "FEATHERLESS_AI_API_KEY", "GROQ_API_KEY")


class ApiKeyEnvBase(unittest.TestCase):
    def setUp(self):
        self._snapshot = {k: os.environ.get(k) for k in _ENV_KEYS}
        for k in _ENV_KEYS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestResolveApiKey(ApiKeyEnvBase):
    def test_accepts_the_ai_suffixed_name(self):
        os.environ["FEATHERLESS_AI_API_KEY"] = "key-from-ai-suffixed-var"
        self.assertEqual(openai_compat_client.resolve_api_key("featherless"),
                          "key-from-ai-suffixed-var")

    def test_accepts_the_alias_name_too(self):
        # This is the exact scenario that used to fail silently: a key set
        # under the "wrong" (but documented-elsewhere) name.
        os.environ["FEATHERLESS_API_KEY"] = "key-from-alias-var"
        self.assertEqual(openai_compat_client.resolve_api_key("featherless"),
                          "key-from-alias-var")

    def test_missing_key_returns_none_not_an_exception(self):
        self.assertIsNone(openai_compat_client.resolve_api_key("featherless"))

    def test_unknown_provider_returns_none(self):
        self.assertIsNone(openai_compat_client.resolve_api_key("not-a-real-provider"))


class TestStatusCodeExtraction(unittest.TestCase):
    def test_real_api_status_error_is_read_correctly(self):
        # Construct a genuine RateLimitError the way the openai package does,
        # rather than a hand-rolled fake, so this test breaks if the SDK
        # changes how status_code is exposed.
        response = mock.Mock()
        response.status_code = 429
        response.headers = {}
        err = openai.RateLimitError("rate limited", response=response, body=None)
        self.assertEqual(openai_compat_client._status_code(err), 429)

    def test_unrelated_exception_does_not_get_misclassified(self):
        # Regression test: the old substring-matching fallback would have
        # matched "404" inside this message and wrongly reported a 404, even
        # though this isn't an HTTP error response at all.
        err = Exception("model qwen-404-turbo produced 0 tokens after 12000ms")
        self.assertIsNone(openai_compat_client._status_code(err))

    def test_connection_error_with_no_response_returns_none(self):
        err = Exception("Connection reset by peer")
        self.assertIsNone(openai_compat_client._status_code(err))


def _fake_completion(content: str, finish_reason: str = "stop"):
    choice = mock.Mock()
    choice.finish_reason = finish_reason
    choice.message.content = content
    response = mock.Mock()
    response.choices = [choice]
    return response


class TestTruncationRetry(ApiKeyEnvBase):
    def setUp(self):
        super().setUp()
        os.environ["GROQ_API_KEY"] = "fake-key-for-this-test"
        openai_compat_client._clients.pop("groq", None)  # don't reuse a cached client from another test

    def tearDown(self):
        openai_compat_client._clients.pop("groq", None)
        super().tearDown()

    def test_truncated_response_is_retried_with_doubled_max_tokens(self):
        calls = []

        def fake_create(**kwargs):
            calls.append(kwargs["max_tokens"])
            if len(calls) == 1:
                return _fake_completion('["truncated, no closing brack', finish_reason="length")
            return _fake_completion('["a", "b"]', finish_reason="stop")

        fake_client = mock.Mock()
        fake_client.chat.completions.create.side_effect = fake_create

        with mock.patch.object(openai_compat_client, "_get_client", return_value=fake_client):
            result = openai_compat_client.call_model("prompt", model="m", provider="groq", max_tokens=100)

        self.assertEqual(result, '["a", "b"]')
        self.assertEqual(calls, [100, 200])  # second attempt doubled the budget

    def test_truncation_on_the_final_attempt_returns_the_truncated_text_rather_than_looping_forever(self):
        # max_retries=1 means there is no "next attempt" to retry into - the
        # truncated content is still returned (and will fail JSON parsing
        # further up the stack, which is the correct, visible failure mode,
        # rather than this function looping or hanging).
        fake_client = mock.Mock()
        fake_client.chat.completions.create.return_value = _fake_completion(
            '["still truncated', finish_reason="length")

        with mock.patch.object(openai_compat_client, "_get_client", return_value=fake_client):
            result = openai_compat_client.call_model("prompt", model="m", provider="groq", max_retries=1)

        self.assertEqual(result, '["still truncated')
        self.assertEqual(fake_client.chat.completions.create.call_count, 1)


if __name__ == "__main__":
    unittest.main()
