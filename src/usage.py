"""
Per-call usage + latency recorder.

Exists because "Sustainability & Scalability" is a real question about
this project that the repo previously had no data on at all: how many
LLM calls, how many tokens, and how many seconds does guarding one note
actually cost, and how does that compare to the single-prompt baseline
it's being measured against?

Those are the honest scalability numbers - the pipeline makes ~4 model
calls per case where the baseline makes 1, so a recall win that costs 4x
the tokens is a different proposition from one that's free, and a grader
should be able to see which it is.

Design notes:

- Every client (gemini_client, openai_compat_client) calls record() once
  per completed API call. Failed calls are recorded too, with whatever
  latency they burned before failing, because a failover that costs three
  seconds of timeouts is a real cost of the multi-provider design.
- Token counts come from the provider's own usage metadata, never
  estimated by counting characters locally. If a provider doesn't return
  usage for a call, that call's token fields are None and the aggregate
  reports how many calls were missing usage data rather than quietly
  treating them as zero.
- DOLLAR COST IS NOT COMPUTED HERE BY DEFAULT. Published per-token prices
  change often and differ per provider/model, and this project's runs
  were all on free tiers (actual spend: $0). Rather than bake in
  plausible-looking numbers nobody verified, prices live in
  eval/prices.json, default to null, and cost is reported only for models
  whose price has actually been filled in from the provider's own pricing
  page. Tokens and latency are measured; cost is arithmetic on top of a
  number the user supplies.
"""
import time

_records = []


def reset():
    """Clear all recorded calls. Called between the pipeline and baseline
    halves of a case so each side's usage is attributed separately."""
    _records.clear()


def record(provider: str, model: str, latency_s: float,
           prompt_tokens=None, completion_tokens=None, ok: bool = True):
    _records.append({
        "provider": provider,
        "model": model,
        "latency_s": round(latency_s, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "ok": ok,
    })


def records():
    return list(_records)


def summary():
    """Aggregate of everything recorded since the last reset()."""
    total_prompt = sum(r["prompt_tokens"] or 0 for r in _records)
    total_completion = sum(r["completion_tokens"] or 0 for r in _records)
    missing_usage = sum(1 for r in _records
                        if r["prompt_tokens"] is None and r["completion_tokens"] is None)
    by_model = {}
    for r in _records:
        key = f"{r['provider']}/{r['model']}"
        agg = by_model.setdefault(key, {"calls": 0, "prompt_tokens": 0,
                                        "completion_tokens": 0, "latency_s": 0.0})
        agg["calls"] += 1
        agg["prompt_tokens"] += r["prompt_tokens"] or 0
        agg["completion_tokens"] += r["completion_tokens"] or 0
        agg["latency_s"] = round(agg["latency_s"] + r["latency_s"], 3)
    return {
        "calls": len(_records),
        "failed_calls": sum(1 for r in _records if not r["ok"]),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "latency_s": round(sum(r["latency_s"] for r in _records), 3),
        "calls_missing_usage_data": missing_usage,
        "by_model": by_model,
    }


class timed:
    """Context manager: times a block and hands the elapsed seconds back.

        with usage.timed() as t:
            response = ...
        usage.record(..., latency_s=t.elapsed, ...)

    Used instead of bare time.time() bookkeeping in the clients so the
    elapsed time is still captured on the exception path (a call that
    fails after a 20s timeout burned 20 real seconds and should say so).
    """

    def __enter__(self):
        self._start = time.perf_counter()
        self.elapsed = 0.0
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self._start
        return False  # never suppress
