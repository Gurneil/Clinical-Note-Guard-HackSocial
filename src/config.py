"""
Central place for 'which model/provider does which job, and why'.

Extended to support automatic failover across providers, because Gemini's
free tier turned out to be tight enough that a single case's worth of
calls can exhaust it. (Earlier notes here said "5 requests/minute" -
that was never directly confirmed; a real 429 later showed a DAILY cap
of 20 requests/day for gemini-3.6-flash instead. See docs/ARCHITECTURE.md
for the full correction - the failover logic below doesn't depend on
which one it actually is, since it reacts to whatever error comes back
rather than pre-counting requests.) Two different kinds of node, handled
differently:

1. CORE_REASONING_CHAIN - used by BOTH the entailment-check node AND the
   single-prompt baseline. These two are FAIRNESS-LINKED (see
   llm_router.py): for any given case, they always end up using the same
   provider/model as each other. If Gemini's quota is hit, both drop to
   the next tier together and stay there for the rest of the run - it
   only ever downgrades, never flaps back and forth mid-run - and
   whichever tier was actually used for a given case gets logged, not
   hidden. This is what keeps "pipeline vs. baseline" a fair comparison
   even after a provider switch: both sides are always tested against
   the same underlying model capability.

2. EXTRACT_CHAIN / CLASSIFY_CHAIN / OMISSION_CHAIN - mechanical,
   structural tasks with no fairness constraint (the baseline has no
   extraction, classification, or omission-check step to match against).
   Deliberately NOT using Gemini at all - Gemini's free tier is the
   tightest constraint in this whole project, so it's reserved entirely
   for the fairness-critical comparison above. These run on Groq first
   (much more free-tier headroom), with Featherless as backup.

Order within each chain = failover priority, left to right.

Set GROQ_API_KEY and/or FEATHERLESS_AI_API_KEY as environment variables
if you want those providers available - NEVER hardcode a key here. If a
key isn't set, that provider is skipped (with a loud warning) - see
llm_router.py.
"""
import json
import os

_TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), "..", "taxonomy.json")
with open(_TAXONOMY_PATH, encoding="utf-8") as f:
    TAXONOMY = json.load(f)

# Fairness-critical. Both the entailment node and the baseline draw from this
# one chain via llm_router.call_core_reasoning(), so they can never diverge.
# NOTE ON THE GROQ ENTRIES BELOW: this project originally used
# llama-3.3-70b-versatile here and llama-3.1-8b-instant on the mechanical
# tiers. Groq withdrew both mid-project - they began returning 404
# model_not_found within hours of a 60-case eval run that had been using them
# successfully - and replaced them with the openai/gpt-oss family. The model
# IDs below are the live ones as of that switch.
#
# The eval results committed under eval/ were produced by the OLD models.
# They are not re-runnable on demand, which is a real limitation of building
# on free tiers rather than a bookkeeping detail; every run records the
# provider/model it actually used per case for exactly this reason. See
# eval/runs/README.md.
CORE_REASONING_CHAIN = [
    {"provider": "gemini", "model": "gemini-3.6-flash"},
    {"provider": "groq", "model": "openai/gpt-oss-120b"},
    {"provider": "featherless", "model": "Qwen/Qwen2.5-7B-Instruct"},
]

# Robustness runs: pin the fairness-critical tier without editing this file,
# so "does the workflow claim hold on a different core-reasoning model?" is a
# reproducible switch rather than a diff someone has to remember to revert.
#
#     CORE_CHAIN="groq:openai/gpt-oss-120b" python run_eval.py
#
# Comma-separate for a failover chain. Deliberately affects ONLY this chain -
# the mechanical tiers stay put, so the only variable between two runs is the
# model doing the reasoning that both the pipeline and the baseline depend on.
# A single-entry chain is the honest choice for a robustness run: if that
# model is unavailable the case errors out and is reported as an error,
# rather than silently downgrading and quietly mixing two models into one
# result - which is exactly the caveat these runs exist to remove.
_CORE_OVERRIDE = os.environ.get("CORE_CHAIN", "").strip()
if _CORE_OVERRIDE:
    CORE_REASONING_CHAIN = [
        {"provider": entry.split(":", 1)[0].strip(),
         "model": entry.split(":", 1)[1].strip()}
        for entry in _CORE_OVERRIDE.split(",") if ":" in entry
    ]
    print(f"[config] CORE_REASONING_CHAIN overridden -> "
          f"{[c['provider'] + '/' + c['model'] for c in CORE_REASONING_CHAIN]}")

# Mechanical nodes - no fairness constraint, and deliberately Gemini-free so
# the whole (tight) Gemini free-tier budget stays available to the
# comparison above.
EXTRACT_CHAIN = [
    {"provider": "groq", "model": "openai/gpt-oss-20b"},
    {"provider": "featherless", "model": "Qwen/Qwen2.5-7B-Instruct"},
]
CLASSIFY_CHAIN = [
    {"provider": "groq", "model": "openai/gpt-oss-20b"},
    {"provider": "featherless", "model": "Qwen/Qwen2.5-7B-Instruct"},
]

# Omission checking (transcript facts -> is each mentioned in the note?) is
# the mirror image of extraction/entailment, but taxonomy.json is explicit
# that it's "tracked as a secondary metric" with "a different detection
# approach" - not the guard's primary job. No fairness constraint (the
# baseline has no equivalent decomposition either way), so mechanical tier.
OMISSION_CHAIN = [
    {"provider": "groq", "model": "openai/gpt-oss-20b"},
    {"provider": "featherless", "model": "Qwen/Qwen2.5-7B-Instruct"},
]

# Node 1 (drafting the note) only runs in the live demo, never in eval, and
# has no fairness constraint - it is routed through DRAFT_CHAIN so the demo
# survives a Gemini outage. MODEL_DRAFT is kept as the preferred draft model.
MODEL_DRAFT = "gemini-3.6-flash"
DRAFT_CHAIN = [
    {"provider": "gemini", "model": MODEL_DRAFT},
    {"provider": "groq", "model": "openai/gpt-oss-120b"},
    {"provider": "featherless", "model": "Qwen/Qwen2.5-7B-Instruct"},
]
