"""
Tests for the two silent-failure bugs found in openai_compat_client.py:

1. Featherless's key used to be read from FEATHERLESS_API_KEY only, so a
   key set as FEATHERLESS_AI_API_KEY made the provider silently vanish
   from every failover chain (a missing key is a skip, not an error - so
   this failed with no visible error at all).
2. _status_code() used to substring-match "404" etc. anywhere in
   str(exception), which could misclassify an unrelated error (e.g. one
   that happens to mention a byte count or model name containing those
   digits) as that HTTP status.

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


if __name__ == "__main__":
    unittest.main()
