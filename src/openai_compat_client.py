"""
Shared client for Groq and Featherless - both expose a fully
OpenAI-compatible API (confirmed from their own docs: Groq at
https://api.groq.com/openai/v1, Featherless at
https://api.featherless.ai/v1), so one implementation using the
standard `openai` package covers both instead of writing two nearly
identical clients.

Setup:
    pip install openai
    Groq:        free key (no card) at https://console.groq.com
                 export GROQ_API_KEY="your-key-here"
    Featherless: key from your account dashboard at https://featherless.ai
                 export FEATHERLESS_API_KEY="your-key-here"

Neither key is ever read from anywhere but the environment - nothing to
paste into code or chat.
"""
import json
import os
import time

from openai import OpenAI

PROVIDER_SETTINGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    "featherless": {
        "base_url": "https://api.featherless.ai/v1",
        "api_key_env": "FEATHERLESS_API_KEY",
    },
}

_clients = {}  # one cached client per provider


def _get_client(provider: str) -> OpenAI:
    if provider not in _clients:
        settings = PROVIDER_SETTINGS[provider]
        api_key = os.environ.get(settings["api_key_env"])
        if not api_key:
            raise RuntimeError(f"{settings['api_key_env']} is not set.")
        _clients[provider] = OpenAI(
            base_url=settings["base_url"],
            api_key=api_key,
            timeout=20.0,       # seconds - same hard-cap philosophy as gemini_client
            max_retries=0,      # disable the openai package's own internal retry -
                                # we handle retry/failover ourselves, one retry
                                # authority only, same reasoning as gemini_client.py
        )
    return _clients[provider]


def _status_code(exc) -> int | None:
    """Best-effort extraction of an HTTP status code from whatever the
    openai package raised, without depending on exact exception class
    names (which have moved between SDK versions before)."""
    code = getattr(exc, "status_code", None)
    if code is not None:
        return code
    msg = str(exc)
    for candidate in (429, 503, 500, 502, 504, 401, 404, 400):
        if str(candidate) in msg:
            return candidate
    return None


def call_model(prompt: str, model: str, base_url: str = None, api_key_env: str = None,
                provider: str = None, max_retries: int = 2) -> str:
    """
    provider is the simple way to call this (looks up base_url/api_key_env
    from PROVIDER_SETTINGS); base_url/api_key_env let you override directly
    if ever needed. Same asymmetric error handling as gemini_client.py:
    429 fails fast, 503 gets a short bounded retry, everything else fails
    immediately.
    """
    if provider:
        client = _get_client(provider)
    else:
        client = OpenAI(base_url=base_url, api_key=os.environ[api_key_env],
                         timeout=20.0, max_retries=0)

    last_err = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            last_err = e
            code = _status_code(e)
            if code == 429:
                print(f"    [openai_compat_client] 429 quota/rate-limit on {model} - failing fast, not retrying")
                raise
            elif code in (503, 500, 502, 504):
                wait = 2 ** attempt
                print(f"    [openai_compat_client] {code} on {model} (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            else:
                raise
    raise RuntimeError(f"Call failed after {max_retries} attempts: {last_err}")


def call_model_json(prompt: str, model: str, base_url: str = None, api_key_env: str = None,
                     provider: str = None, max_retries: int = 2):
    raw = call_model(prompt, model=model, base_url=base_url, api_key_env=api_key_env,
                      provider=provider, max_retries=max_retries)
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
