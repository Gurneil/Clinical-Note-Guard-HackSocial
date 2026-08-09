"""
Single-prompt baseline. This is the thing we're testing our pipeline
AGAINST - one call, no decomposition, no verification pass, no taxonomy.

Routed through llm_router.call_core_reasoning() - the SAME function the
pipeline's entailment node uses - which is what guarantees this always
runs on the same provider/model as the pipeline's strongest node for any
given case, even after an automatic failover. See config.py and
llm_router.py for why that fairness link matters.
"""
import llm_router


def single_prompt_check(transcript: str, note: str):
    """Returns (result, provider, model) - always log the provider/model,
    same as run_guard() does, so a downgraded run stays fully auditable."""
    prompt = f"""You are given a doctor-patient conversation transcript and
a clinical note that was generated from it. Carefully review the note and
identify any inaccuracies, fabrications, or discrepancies compared to the
transcript.

TRANSCRIPT:
{transcript}

NOTE:
{note}

Return ONLY a JSON array of objects, one per issue found, like:
[{{"issue": "the problematic text from the note", "explanation": "why it's wrong"}}]
If there are no issues, return an empty array []. No markdown, just the JSON array."""
    result, provider, model = llm_router.call_core_reasoning(prompt, json_mode=True)
    if not isinstance(result, list):
        raise ValueError(f"Expected a JSON list, got: {result}")
    for item in result:
        item["source"] = "single_prompt_baseline"
    return result, provider, model
