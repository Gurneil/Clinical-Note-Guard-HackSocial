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
                 export FEATHERLESS_AI_API_KEY="your-key-here"
                 (FEATHERLESS_API_KEY is also accepted, as an alias)

Neither key is ever read from anywhere but the environment - nothing to
paste into code or chat.
"""
import json
import os
import time

import _env  # noqa: F401 - loads .env before anything reads os.environ
import openai
from openai import OpenAI

PROVIDER_SETTINGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        # Tuple, not a single string: Featherless in particular is documented
        # under two different env-var names in the wild, and a key set under
        # the "wrong" one used to make the provider vanish from every failover
        # chain silently (a missing key is treated as "skip", not "error").
        # Accepting every plausible name removes that whole failure mode.
        "api_key_envs": ("GROQ_API_KEY",),
    },
    "featherless": {
        "base_url": "https://api.featherless.ai/v1",
        "api_key_envs": ("FEATHERLESS_AI_API_KEY", "FEATHERLESS_API_KEY"),
    },
}

_clients = {}  # one cached client per provider


def resolve_api_key(provider: str) -> str | None:
    """The single place that decides whether a provider has a usable key.
    Returns the first env var that is set, or None. llm_router uses this too,
    so 'is this provider available?' and 'what key do we call it with?' can
    never disagree."""
    settings = PROVIDER_SETTINGS.get(provider)
    if not settings:
        return None
    for env_name in settings["api_key_envs"]:
        value = os.environ.get(env_name)
        if value:
            return value
    return None


def _get_client(provider: str) -> OpenAI:
    if provider not in _clients:
        settings = PROVIDER_SETTINGS[provider]
        api_key = resolve_api_key(provider)
        if not api_key:
            names = " or ".join(settings["api_key_envs"])
            raise RuntimeError(f"No API key for {provider}: set {names}.")
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
    openai package raised.

    openai.APIStatusError and every subclass (RateLimitError,
    InternalServerError, NotFoundError, ...) carry a real `.status_code`
    attribute - that covers every actual HTTP error response. There is
    deliberately NO string-matching fallback: a substring scan over
    str(exc) for "429", "404" etc. used to misfire on any error message
    that happened to *contain* those digits for an unrelated reason (a
    model name, a byte count, part of a request id) and silently
    misclassify it as that HTTP status. APIConnectionError/APITimeoutError
    (no HTTP response at all - the request never completed) correctly
    return None here, and are treated as a real, immediate failure rather
    than guessed at.
    """
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code
    return None


def call_model(prompt: str, model: str, base_url: str = None, api_key_env: str = None,
                provider: str = None, max_retries: int = 2, max_tokens: int = 4096) -> str:
    """
    provider is the simple way to call this (looks up base_url/api_key_env
    from PROVIDER_SETTINGS); base_url/api_key_env let you override directly
    if ever needed. Same asymmetric error handling as gemini_client.py:
    429 fails fast, 503 gets a short bounded retry, everything else fails
    immediately.

    max_tokens is set explicitly (not left to the provider's default) -
    without it, a batched JSON-array response (e.g. the omission-check
    prompt for a case with a dozen transcript facts) can get silently
    truncated mid-string by a small provider default, which then surfaces
    as a confusing JSONDecodeError with no indication that the real cause
    was a token cap, not a malformed response. If a response IS still cut
    off at 4096, that's detected via finish_reason == "length" and gets
    one retry at double the token budget before giving up - a different,
    explicit failure mode from a quota/availability error.
    """
    if provider:
        client = _get_client(provider)
    else:
        client = OpenAI(base_url=base_url, api_key=os.environ[api_key_env],
                         timeout=20.0, max_retries=0)

    last_err = None
    tokens_for_attempt = max_tokens
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=tokens_for_attempt,
            )
            choice = response.choices[0]
            if choice.finish_reason == "length" and attempt < max_retries - 1:
                tokens_for_attempt *= 2
                print(f"    [openai_compat_client] response truncated at {model} "
                      f"(finish_reason=length) - retrying with max_tokens={tokens_for_attempt}")
                continue
            return choice.message.content
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
                     provider: str = None, max_retries: int = 2, max_tokens: int = 4096):
    raw = call_model(prompt, model=model, base_url=base_url, api_key_env=api_key_env,
                      provider=provider, max_retries=max_retries, max_tokens=max_tokens)
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
