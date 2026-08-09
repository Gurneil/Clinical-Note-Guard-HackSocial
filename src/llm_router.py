"""
Central dispatch + automatic failover across providers.

Two categories of node, handled differently - see config.py for the full
reasoning:

1. Core reasoning (entailment check + the single-prompt baseline). These
   MUST always use the same provider/model as each other for any given
   case, or the comparison stops being fair. Failover here uses a single
   shared, STICKY tier index: if the current tier's provider hits a
   quota/availability error, BOTH entailment and baseline drop to the
   next tier together and stay there - it only ever moves down the
   chain, never flaps back up mid-run. Call call_core_reasoning() for
   both of these; it returns (result, provider, model) so the caller can
   log exactly what was used for that case.

2. Mechanical nodes (extraction, classification). No fairness constraint
   applies, so each call independently tries its chain in order and
   moves on. Call call_mechanical() for these.

In both cases: if a provider's API key isn't set in the environment, it
is skipped automatically (not an error) - see PROVIDER_SETTINGS in
openai_compat_client.py and the GEMINI_API_KEY check in gemini_client.py.
"""
import os

import gemini_client
import openai_compat_client
from google.genai import errors as genai_errors

_core_tier_index = 0  # sticky - only ever moves forward (downgrades)


def _is_quota_or_unavailable(exc: Exception) -> bool:
    """
    True only for errors worth failing over on (quota exhausted /
    provider overloaded). False for anything else - a bad API key, a
    malformed prompt, an auth error should surface immediately and loudly,
    not get silently swallowed by a switch to a different provider that
    would just mask a real bug.
    """
    if isinstance(exc, genai_errors.APIError):
        return exc.code in (429, 503)
    code = getattr(exc, "status_code", None)
    if code in (429, 503, 500, 502, 504):
        return True
    msg = str(exc).lower()
    return any(s in msg for s in ("429", "503", "rate limit", "quota", "resource_exhausted", "unavailable"))


def _key_available(provider: str) -> bool:
    if provider == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY"))
    settings = openai_compat_client.PROVIDER_SETTINGS.get(provider)
    return bool(settings and os.environ.get(settings["api_key_env"]))


def _dispatch(provider: str, model: str, prompt: str, json_mode: bool):
    if provider == "gemini":
        fn = gemini_client.call_model_json if json_mode else gemini_client.call_model
        return fn(prompt, model=model)
    elif provider in openai_compat_client.PROVIDER_SETTINGS:
        fn = openai_compat_client.call_model_json if json_mode else openai_compat_client.call_model
        return fn(prompt, model=model, provider=provider)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_core_reasoning(prompt: str, json_mode: bool = False, chain=None):
    """
    Used by BOTH entailment_check_batch() and single_prompt_check().
    Returns (result, provider, model) - always log the provider/model
    that come back, per-case, so a run that downgrades mid-way is fully
    auditable rather than silently mixed.
    """
    global _core_tier_index
    from config import CORE_REASONING_CHAIN
    chain = chain or CORE_REASONING_CHAIN

    last_err = None
    for i in range(_core_tier_index, len(chain)):
        provider, model = chain[i]["provider"], chain[i]["model"]
        if not _key_available(provider):
            print(f"    [llm_router] skipping {provider} (no API key set)")
            continue
        try:
            result = _dispatch(provider, model, prompt, json_mode)
            if i > _core_tier_index:
                print(f"    [llm_router] DOWNGRADING core-reasoning tier to {provider}/{model} for the rest of this run")
                _core_tier_index = i
            return result, provider, model
        except Exception as e:
            if _is_quota_or_unavailable(e):
                print(f"    [llm_router] {provider}/{model} unavailable ({e}); trying next tier...")
                last_err = e
                continue
            raise  # not a quota/availability issue - surface immediately, don't mask a real bug
    raise RuntimeError(f"All core-reasoning providers exhausted or unavailable. Last error: {last_err}")


def call_mechanical(chain, prompt: str, json_mode: bool = False):
    """Used by extraction and classification. No fairness constraint, so
    each call independently tries the chain in order."""
    last_err = None
    for step in chain:
        provider, model = step["provider"], step["model"]
        if not _key_available(provider):
            continue
        try:
            return _dispatch(provider, model, prompt, json_mode)
        except Exception as e:
            if _is_quota_or_unavailable(e):
                print(f"    [llm_router] {provider}/{model} unavailable; trying next in chain...")
                last_err = e
                continue
            raise
    raise RuntimeError(f"All providers in chain exhausted or unavailable. Last error: {last_err}")


def reset_core_tier():
    """Call at the start of a fresh eval run if you want to re-try Gemini
    from the top rather than staying downgraded from a previous run
    (the sticky index otherwise persists for the life of the process)."""
    global _core_tier_index
    _core_tier_index = 0
