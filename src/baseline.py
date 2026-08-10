"""
Single-prompt baseline. This is the thing we're testing our pipeline
AGAINST - one call, no decomposition, no verification pass, no taxonomy.

Routed through llm_router.call_core_reasoning() - the SAME function the
pipeline's entailment node uses - which is what guarantees this always
runs on the same provider/model as the pipeline's strongest node for any
given case, even after an automatic failover. See config.py and
llm_router.py for why that fairness link matters.

--- Scope fairness: why this prompt mentions omissions ---

The variable under test in this project is WORKFLOW STRUCTURE
(decompose-then-verify vs. one open-ended read), not task definition. So
the baseline has to be asked to look for the same *kinds* of error the
pipeline looks for, or any measured "win" is just the pipeline having
been pointed at a category the baseline was never told about.

An earlier version of this prompt asked only for "inaccuracies,
fabrications, or discrepancies" - i.e. errors of COMMISSION only - while
the pipeline ran a dedicated omission node (node 5) AND the benchmark
scored both systems on omission cases. That made the headline recall gap
partly an artifact of prompt scope rather than of workflow design. Fixed
below by naming both directions explicitly.

What the baseline still deliberately does NOT get, because these are the
actual independent variable: the atomic-claim decomposition step, the
forced one-verdict-per-claim coverage requirement, the deterministic
numeric checker, and the fixed taxonomy. It gets the same *task*, in one
pass, with no structure.
"""
import llm_router


def single_prompt_check(transcript: str, note: str):
    """Returns (result, provider, model) - always log the provider/model,
    same as run_guard() does, so a downgraded run stays fully auditable."""
    prompt = f"""You are given a doctor-patient conversation transcript and
a clinical note that was generated from it. Carefully review the note
against the transcript and identify any documentation errors.

Look for BOTH kinds of error:
1. Anything stated in the note that the transcript does not support -
   fabricated details, wrong numbers or doses, altered severity, a
   denial reported as an affirmation (or vice versa), or something
   attributed to the wrong person.
2. Anything clinically relevant that the transcript states but the note
   leaves out entirely.

TRANSCRIPT:
{transcript}

NOTE:
{note}

Return ONLY a JSON array of objects, one per issue found, like:
[{{"issue": "the problematic text from the note, or the detail that is missing from it", "explanation": "why it's wrong"}}]
If there are no issues, return an empty array []. No markdown, just the JSON array."""
    result, provider, model = llm_router.call_core_reasoning(prompt, json_mode=True)
    if not isinstance(result, list):
        raise ValueError(f"Expected a JSON list, got: {result}")
    for item in result:
        item["source"] = "single_prompt_baseline"
    return result, provider, model
