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


def call_model(prompt: str, model: str, max_retries: int = 2) -> str:
    """
    Call a Gemini model with a plain text prompt. Returns raw text.

    Error handling is deliberately asymmetric:
      - 429 (quota exhausted): fails IMMEDIATELY, no retry. Retrying a
        per-minute quota error a second later almost never helps, and
        every second spent retrying here is a second not spent trying
        the next provider in the failover chain (see llm_router.py).
      - 503 (transiently overloaded): short bounded retry (2 attempts,
        1s/2s backoff) - this one genuinely is often transient.
      - anything else (400, 401, 404...): fails immediately. Retrying a
        malformed request or a bad model name will never succeed.
    """
    client = get_client()
    last_err = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
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


def call_model_json(prompt: str, model: str, max_retries: int = 2):
    """Call a Gemini model and parse the response as JSON."""
    raw = call_model(prompt, model=model, max_retries=max_retries)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON.\nError: {e}\nRaw output:\n{raw}")
