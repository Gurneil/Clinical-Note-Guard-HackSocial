r"""
Verifies that each configured provider actually answers, and that the
failover router works end to end. Run this before trusting any eval run.

Deliberately minimal: ONE tiny call per provider, so confirming that
Gemini works costs one request out of its 5 RPM free-tier budget rather
than a meaningful chunk of it.

Usage (PowerShell):
    $env:GEMINI_API_KEY="..."           # optional
    $env:GROQ_API_KEY="..."             # optional
    $env:FEATHERLESS_AI_API_KEY="..."   # optional
    D:\Python312\python.exe smoke_test.py

Providers with no key set are reported as SKIPPED, not as failures - but
they are reported, never silently omitted.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config              # noqa: E402
import llm_router          # noqa: E402
import openai_compat_client  # noqa: E402

PROMPT = "Reply with exactly the word: OK"


def _has_key(provider: str) -> bool:
    if provider == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY"))
    return bool(openai_compat_client.resolve_api_key(provider))


def check_provider(provider: str, model: str) -> str:
    if not _has_key(provider):
        return "SKIPPED (no API key set)"
    try:
        text = llm_router._dispatch(provider, model, PROMPT, json_mode=False)
        snippet = (text or "").strip().replace("\n", " ")[:60]
        if not snippet:
            return "FAIL (empty response - possibly safety-blocked)"
        return f"OK -> {snippet!r}"
    except Exception as e:
        return f"FAIL ({type(e).__name__}: {str(e)[:160]})"


def main() -> int:
    # Every distinct (provider, model) pair used anywhere in the config.
    pairs, seen = [], set()
    for chain in (config.CORE_REASONING_CHAIN, config.EXTRACT_CHAIN,
                  config.CLASSIFY_CHAIN, config.DRAFT_CHAIN):
        for step in chain:
            key = (step["provider"], step["model"])
            if key not in seen:
                seen.add(key)
                pairs.append(key)

    print("=" * 72)
    print("PROVIDER SMOKE TEST - one minimal call per provider/model")
    print("=" * 72)
    results = {}
    for provider, model in pairs:
        print(f"\n{provider}/{model}")
        result = check_provider(provider, model)
        results[(provider, model)] = result
        print(f"  {result}")

    print("\n" + "=" * 72)
    print("ROUTER TEST - core-reasoning chain (the fairness-critical path)")
    print("=" * 72)
    try:
        result, provider, model = llm_router.call_core_reasoning(PROMPT)
        print(f"  OK - router resolved to {provider}/{model}")
        print(f"  response: {(result or '').strip()[:60]!r}")
        router_ok = True
    except Exception as e:
        print(f"  FAIL ({type(e).__name__}: {str(e)[:200]})")
        router_ok = False

    working = [k for k, v in results.items() if v.startswith("OK")]
    skipped = [k for k, v in results.items() if v.startswith("SKIPPED")]
    failed = [k for k, v in results.items() if v.startswith("FAIL")]

    print("\n" + "=" * 72)
    print(f"SUMMARY: {len(working)} working, {len(skipped)} skipped (no key), {len(failed)} failing")
    for k in failed:
        print(f"  FAILING: {k[0]}/{k[1]}")
    if not any(p == "gemini" for p, _ in working):
        print("\n  NOTE: Gemini is not confirmed working. The core-reasoning chain will")
        print("  run on its next tier - still fair (pipeline and baseline stay linked),")
        print("  but record in your write-up which tier the reported numbers came from.")
    return 0 if (router_ok and not failed) else 1


if __name__ == "__main__":
    sys.exit(main())
