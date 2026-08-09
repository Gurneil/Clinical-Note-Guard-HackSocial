"""
Clinical Note Hallucination Guard - main pipeline.

Six nodes:
  0. Input          - transcript + (in the live product) an AI-drafted note.
  1. draft_note              - transcript -> SOAP note draft (LLM, Gemini)
  2. extract_claims          - note -> list of atomic factual claims
                                (LLM, mechanical tier - Groq/Featherless)
  3. entailment_check_batch  - ALL claims for one case, checked in a
                                SINGLE request against the transcript
                                (LLM, core-reasoning tier - fairness-linked
                                with the baseline, see llm_router.py)
  4. deterministic_numeric_check - regex-based exact-match check for
                                numbers/doses/vitals, NO LLM at all
                                (UNCHANGED from the original design)
  5. classify_errors_batch   - ALL flagged claims for one case, classified
                                in a SINGLE request (LLM, mechanical tier)
  6. human_review_checkpoint - required human-in-the-loop step before
                                anything is finalized

Nodes 2-5 form `run_guard()`, which is what the eval harness calls
directly against (transcript, existing_note) pairs from the benchmark.
`run_full_pipeline()` chains node 1 in front of that, for the live demo.

--- Why batched entailment is still meaningfully different from the
single-prompt baseline (this changed from one-call-per-claim to
one-call-per-case, driven by a real free-tier rate limit, not a design
preference - see docs/ARCHITECTURE.md for the full story) ---

The baseline gets a whole note in prose and is asked, in one open-ended
instruction, to "find any issues." The pipeline forces a specific
structure the baseline never gets: claims are extracted into a clean,
atomic list FIRST (node 2, a separate call), and the entailment call is
then required to return exactly one verdict per claim, in order - not
"describe what's wrong," but "here are N claims, classify each one."
That per-claim coverage requirement is checked in code (see the count
assertion below): if the model skips or merges claims, that's caught and
raised as an error rather than silently accepted. The baseline has no
equivalent structural guarantee that it looked at every fact.
"""
import re

import llm_router
from config import EXTRACT_CHAIN, CLASSIFY_CHAIN, MODEL_DRAFT, TAXONOMY
import gemini_client


# ---------------------------------------------------------------------------
# Node 1: Draft the note (only used in the live demo, not in eval)
# ---------------------------------------------------------------------------
def draft_note(transcript: str) -> str:
    prompt = f"""You are an ambient clinical scribe. Read the following
doctor-patient conversation transcript and produce a structured SOAP note
(Subjective, Objective, Assessment, Plan). Only include information that
was actually discussed in the transcript.

TRANSCRIPT:
{transcript}

Return only the SOAP note, no preamble."""
    return gemini_client.call_model(prompt, model=MODEL_DRAFT)


# ---------------------------------------------------------------------------
# Node 2: Extract atomic claims from the note (mechanical tier)
# ---------------------------------------------------------------------------
def extract_claims(note: str) -> list[str]:
    prompt = f"""Break the following clinical note into a list of atomic,
independently-checkable factual claims. Each claim should be one discrete
fact (one symptom, one medication + dose, one vital sign, one plan item,
etc). Do not combine multiple facts into one claim.

NOTE:
{note}

Return ONLY a JSON array of strings, e.g. ["claim 1", "claim 2", ...].
No markdown, no explanation, just the JSON array."""
    result = llm_router.call_mechanical(EXTRACT_CHAIN, prompt, json_mode=True)
    if not isinstance(result, list):
        raise ValueError(f"Expected a JSON list of claims, got: {result}")
    return result


# ---------------------------------------------------------------------------
# Node 3: Entailment check, BATCHED - all claims for one case in a single
# request against the transcript (core-reasoning tier, fairness-linked
# with the baseline). Requires the model to return exactly one verdict
# per input claim, in order; a count mismatch is treated as an error, not
# silently accepted, which is what preserves the per-claim coverage
# guarantee even though this is no longer one call per claim.
# ---------------------------------------------------------------------------
def entailment_check_batch(claims: list[str], transcript: str):
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
    prompt = f"""You are checking whether each of the following claims from
a clinical note is supported by a source transcript. Check EVERY claim
independently - your judgment on one claim must not influence any other.

TRANSCRIPT:
{transcript}

CLAIMS TO CHECK ({len(claims)} total, check each independently):
{numbered}

For EACH claim, decide exactly ONE status: "supported", "contradicted",
or "not_mentioned".

Return ONLY a JSON array with EXACTLY {len(claims)} objects, one per
claim, in the SAME ORDER as listed above:
[{{"claim_number": 1, "status": "supported" | "contradicted" | "not_mentioned",
   "evidence": "exact quote from the transcript, or empty string if not_mentioned"}}, ...]
No markdown, just the JSON array. You MUST return exactly {len(claims)} objects - do not skip or merge any."""
    result, provider, model = llm_router.call_core_reasoning(prompt, json_mode=True)
    if not isinstance(result, list) or len(result) != len(claims):
        got = len(result) if isinstance(result, list) else type(result).__name__
        raise ValueError(
            f"Expected exactly {len(claims)} entailment results, got {got}. "
            "The model likely skipped or merged claims when batching - this "
            "is exactly the coverage gap the original one-call-per-claim "
            "design existed to prevent, so it's checked explicitly here "
            "rather than silently accepted."
        )
    return result, provider, model


# ---------------------------------------------------------------------------
# Node 4: Deterministic numeric / medication cross-check. UNCHANGED.
# ---------------------------------------------------------------------------
# Note the negative lookahead (?!\s*/) on the dose pattern: without it,
# lab values like "58 mg/dL" (a glucose reading) get matched as if they
# were a medication dose "58mg", producing false positives. Found this
# during testing against case_04 (a glucose value, not a dose) before
# ever calling the API - caught by a standalone regex test, not by luck.
_DOSE_RE = re.compile(r"\b\d+(\.\d+)?\s*(mg|mcg|milligrams?|micrograms?)\b(?!\s*/)", re.IGNORECASE)
_BP_RE = re.compile(r"\b\d{2,3}\s*(/|over)\s*\d{2,3}\b", re.IGNORECASE)


def _normalize(s: str) -> str:
    s = s.lower()
    s = s.replace(" over ", "/")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"milligrams?", "mg", s)
    s = re.sub(r"micrograms?", "mcg", s)
    s = s.replace(" mg", "mg").replace(" mcg", "mcg")
    return s


def _extract_numeric_tokens(text: str) -> set[str]:
    tokens = set()
    for m in _DOSE_RE.finditer(text):
        tokens.add(_normalize(m.group(0)))
    for m in _BP_RE.finditer(text):
        tokens.add(_normalize(m.group(0)))
    return tokens


def deterministic_numeric_check(note: str, transcript: str) -> list[dict]:
    note_tokens = _extract_numeric_tokens(note)
    transcript_tokens = _extract_numeric_tokens(transcript)
    unmatched = note_tokens - transcript_tokens
    return [
        {
            "category": "numeric_medication_error",
            "flagged_value": tok,
            "reason": "This number/dose appears in the note but was not found anywhere in the transcript.",
            "source": "deterministic_check",
        }
        for tok in sorted(unmatched)
    ]


# ---------------------------------------------------------------------------
# Node 5: Classify flagged claims, BATCHED - all flagged claims for one
# case in a single request (mechanical tier).
# ---------------------------------------------------------------------------
def classify_errors_batch(flagged: list[dict]):
    if not flagged:
        return []
    categories = "\n".join(f"- {c['id']}: {c['definition']}" for c in TAXONOMY["categories"])
    numbered = "\n".join(
        f'{i + 1}. claim: "{f["claim"]}" | status: {f["status"]} | evidence found: "{f.get("evidence", "")}"'
        for i, f in enumerate(flagged)
    )
    prompt = f"""Classify each of the following flagged claims into exactly
ONE category from this list:

{categories}

FLAGGED CLAIMS ({len(flagged)} total):
{numbered}

Return ONLY a JSON array with EXACTLY {len(flagged)} objects, in the SAME
ORDER as listed above:
[{{"item_number": 1, "category": "<one of the ids above>", "explanation": "one sentence"}}, ...]
No markdown, just the JSON array."""
    result = llm_router.call_mechanical(CLASSIFY_CHAIN, prompt, json_mode=True)
    if not isinstance(result, list) or len(result) != len(flagged):
        got = len(result) if isinstance(result, list) else type(result).__name__
        raise ValueError(f"Expected exactly {len(flagged)} classifications, got {got}.")
    return result


# ---------------------------------------------------------------------------
# Nodes 2-5 chained: the guard itself, run against any (transcript, note) pair
# ---------------------------------------------------------------------------
def run_guard(transcript: str, note: str, verbose: bool = False) -> dict:
    claims = extract_claims(note)
    if verbose:
        print(f"  extracted {len(claims)} claims")

    entailment_results, core_provider, core_model = entailment_check_batch(claims, transcript)
    if verbose:
        print(f"  entailment checked via {core_provider}/{core_model}")

    flagged_raw = []
    for claim_text, ent in zip(claims, entailment_results):
        if ent.get("status") in ("contradicted", "not_mentioned"):
            flagged_raw.append({
                "claim": claim_text,
                "status": ent.get("status"),
                "evidence": ent.get("evidence", ""),
            })

    classifications = classify_errors_batch(flagged_raw)
    flagged = []
    for f, c in zip(flagged_raw, classifications):
        flagged.append({
            **f,
            "category": c.get("category"),
            "explanation": c.get("explanation"),
            "source": "llm_pipeline",
        })

    numeric_flags = deterministic_numeric_check(note, transcript)

    return {
        "claims_checked": claims,
        "llm_flags": flagged,
        "deterministic_flags": numeric_flags,
        "all_flags": flagged + numeric_flags,
        "core_reasoning_provider": core_provider,
        "core_reasoning_model": core_model,
    }


# ---------------------------------------------------------------------------
# Node 6: Human review checkpoint (required, not optional) - UNCHANGED
# ---------------------------------------------------------------------------
def human_review_checkpoint(guard_result: dict, interactive: bool = True) -> dict:
    flags = guard_result["all_flags"]
    if not flags:
        print("\n[Human Review] No flags raised. Note approved as-is.")
        return {"approved_flags": [], "note_status": "approved_no_changes"}

    if not interactive:
        return {"approved_flags": flags, "note_status": "pending_review"}

    print(f"\n[Human Review] {len(flags)} item(s) flagged for review:\n")
    approved = []
    for i, flag in enumerate(flags, 1):
        label = flag.get("claim") or flag.get("flagged_value")
        category = flag.get("category")
        print(f"  {i}. [{category}] {label}")
        print(f"     reason: {flag.get('explanation') or flag.get('reason')}")
        decision = input("     Confirm this is a real error? (y/n/skip): ").strip().lower()
        if decision == "y":
            approved.append(flag)
    print(f"\n[Human Review] {len(approved)} of {len(flags)} flags confirmed by reviewer.")
    return {"approved_flags": approved, "note_status": "reviewed"}


# ---------------------------------------------------------------------------
# Full pipeline: draft -> guard -> human checkpoint (used for the live demo)
# ---------------------------------------------------------------------------
def run_full_pipeline(transcript: str, interactive: bool = True) -> dict:
    note = draft_note(transcript)
    guard_result = run_guard(transcript, note, verbose=True)
    review = human_review_checkpoint(guard_result, interactive=interactive)
    return {
        "draft_note": note,
        "guard_result": guard_result,
        "review": review,
    }
