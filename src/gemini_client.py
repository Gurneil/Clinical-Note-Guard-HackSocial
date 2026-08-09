"""
Thin wrapper around the Gemini API (google-genai SDK). Used only for
provider="gemini" calls, dispatched through llm_router.py.

Setup (one-time):
    pip install google-genai
    Get a free API key (no credit card) at https://aistudio.google.com/apikey
    export GEMINI_API_KEY="your-key-here"      (Mac/Linux)
    $env:GEMINI_API_KEY="your-key-here"        (Windows PowerShell)
    set GEMINI_API_KEY=your-key-here           (Windows Command Prompt)
"""
import json
import os
import time

import _env  # noqa: F401 - loads .env before anything reads os.environ
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and run:\n"
                '  export GEMINI_API_KEY="your-key-here"'
            )
        # attempts=1 disables the SDK's own internal retry (it otherwise
        # retries transient errors internally, with backoff up to 60s,
        # BEFORE a call ever returns to us - stacking badly with any
        # retry loop we write ourselves). timeout gives every call a
        # hard cap so a stalled request fails fast instead of hanging.
        _client = genai.Client(
            http_options=types.HttpOptions(
                timeout=20_000,  # milliseconds
                retry_options=types.HttpRetryOptions(attempts=1),
            )
        )
    return _client


def call_model(prompt: str, model: str, max_retries: int = 2, max_output_tokens: int = 4096) -> str:
    """
    Call a Gemini model with a plain text prompt. Returns raw text.

    max_output_tokens is set explicitly rather than left at the SDK
    default - see the equivalent note in openai_compat_client.py, which
    is where this was actually observed to matter (a batched JSON-array
    response silently truncated by a small provider default surfaces as
    a confusing JSONDecodeError with no hint the real cause was a token
    cap). Set here too for consistency even though the failure was seen
    on Groq, not Gemini.

    Error handling is deliberately asymmetric:
      - 429 (quota exhausted): fails IMMEDIATELY, no retry. Retrying a
        quota error a second later almost never helps - regardless of
        whether the underlying window is per-minute or per-day (this
        project's free tier turned out to be a 20/day cap, not the
        per-minute limit originally assumed - see docs/ARCHITECTURE.md)
        - and every second spent retrying here is a second not spent
        trying the next provider in the failover chain (see llm_router.py).
      - 503 (transiently overloaded): short bounded retry (2 attempts,
        1s/2s backoff) - this one genuinely is often transient.
      - anything else (400, 401, 404...): fails immediately. Retrying a
        malformed request or a bad model name will never succeed.
    """
    client = get_client()
    last_err = None
    tokens_for_attempt = max_output_tokens
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=tokens_for_attempt),
            )
            if response.candidates and response.candidates[0].finish_reason == "MAX_TOKENS" \
                    and attempt < max_retries - 1:
                tokens_for_attempt *= 2
                print(f"    [gemini_client] response truncated at {model} "
                      f"(MAX_TOKENS) - retrying with max_output_tokens={tokens_for_attempt}")
                continue
            return response.text
        except genai_errors.APIError as e:
            last_err = e
            if e.code == 429:
                print(f"    [gemini_client] 429 quota exhausted on {model} - failing fast, not retrying")
                raise
            elif e.code == 503:
                wait = 2 ** attempt
                print(f"    [gemini_client] 503 overloaded on {model} (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            else:
                raise
        except Exception as e:
            # Non-APIError (e.g. a real connection issue) - one short retry
            last_err = e
            wait = 2 ** attempt
            print(f"    [gemini_client] call failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Gemini call failed after {max_retries} attempts: {last_err}")


def _strip_markdown_fence(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return cleaned


def call_model_json(prompt: str, model: str, max_retries: int = 2, max_output_tokens: int = 4096,
                     json_retries: int = 2):
    """
    Call a Gemini model and parse the response as JSON.

    json_retries is separate from max_retries - see the equivalent note
    in openai_compat_client.py. A complete, non-truncated response can
    still be malformed JSON (a missing comma or bracket); each retry here
    is a fresh generation, not a reparse of the same broken text.
    """
    last_err = None
    last_raw = None
    for attempt in range(json_retries):
        raw = call_model(prompt, model=model, max_retries=max_retries, max_output_tokens=max_output_tokens)
        last_raw = raw
        try:
            return json.loads(_strip_markdown_fence(raw))
        except json.JSONDecodeError as e:
            last_err = e
            if attempt < json_retries - 1:
                print(f"    [gemini_client] {model} returned malformed JSON "
                      f"(attempt {attempt + 1}/{json_retries}) - retrying with a fresh generation")
    raise ValueError(f"Model did not return valid JSON after {json_retries} attempts.\n"
                      f"Error: {last_err}\nRaw output:\n{last_raw}")
