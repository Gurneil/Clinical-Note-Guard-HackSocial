# Architecture & Reasoning

## The problem this addresses

AI "ambient scribe" tools that draft clinical notes from doctor-patient
conversations are one of the most actively deployed categories of
healthcare AI right now. Their central risk is well documented: models
can produce fluent, confident-sounding notes that contain details never
actually said — fabricated symptoms, altered severity, wrong doses, or
flipped negations. Every clinical body involved in this space agrees
that AI-drafted notes require human review before being signed; the open
problem is that reviewing a whole note by eye, hoping to notice what's
wrong, is slow and unreliable. This project builds the systematic check
that review should be able to lean on.

Note: hallucinations aren't unique to AI-generated notes — some research
has found them in physician-authored notes too, sometimes at similar or
higher rates. The point of this project isn't "AI is uniquely dangerous."
It's that documentation errors are a known risk regardless of source, and
a structured QA layer is the right response to that risk whether the
draft came from a model or a tired resident at 2am.

## Why this can't be one prompt

The obvious naive approach is: "give a model the transcript and the note,
ask it to point out any errors." We test that directly as our baseline.
The problem with it is that it asks a model to do three different jobs
in one pass — read a long note, silently decompose it into individual
facts, and judge each one against a long transcript — all without any
structure forcing it to actually check every claim. Long documents are
exactly where single-pass review is weakest: it's easy for a model (or a
person) to skim past one wrong number in a paragraph that otherwise reads
fine.

The pipeline instead forces the check to happen claim-by-claim:

| Node | What it does | Model / method | Why this step exists |
|---|---|---|---|
| 0 | Transcript input | Human-sourced data | The ground truth everything else is checked against |
| 1 | Draft the note | Gemini Flash | Simulates what an ambient scribe produces |
| 2 | Extract atomic claims | Gemini Flash-Lite | You can't verify a whole note at once reliably; you can verify one fact at a time. This step forces decomposition before any judgment happens. |
| 3 | Entailment check, per claim | Gemini Flash, one independent call per claim | Checks each claim in isolation against the transcript, so no claim can get lost in a long list. Returns supported / contradicted / not_mentioned plus a quoted evidence excerpt — every decision is auditable, not just asserted. |
| 4 | Deterministic numeric/medication check | Plain Python, no LLM | Exact numbers (doses, vitals) don't need a model's judgment, they need an exact match. This node exists specifically because numeric/medication errors are the highest-severity failure category, and a deterministic check on them has zero ambiguity — the "right tool for the job" instead of routing everything through an LLM by default. |
| 5 | Classify flagged claims | Gemini Flash-Lite, fixed taxonomy | Every flag gets a specific category, not just a generic "this seems wrong." Constraining classification to a fixed, literature-grounded taxonomy (rather than free-form explanation) keeps output auditable and comparable across cases. |
| 6 | Human review checkpoint | Human | Required, not optional. Nothing is finalized without a person confirming it. This mirrors the actual clinical requirement that a clinician signs off on any AI-assisted note. |

## Where human input is required

There are three distinct points, not one token human-in-the-loop box:

1. **The source data itself** — every transcript is written by a human
   (in a real deployment: the actual conversation) and stands as the
   ground truth everything downstream is checked against.
2. **Implicit in Node 0** — in a live deployment, the *patient and
   clinician* are the human input generating the raw transcript.
3. **Node 6, explicitly** — a human reviewer sees every flagged item with
   its category and evidence, and must actively confirm it before it
   affects the final note. The system never auto-corrects or auto-removes
   content; it only surfaces candidates for a human decision.

## Error taxonomy

See `taxonomy.json`. Categories are adapted from failure modes described
in the ambient-scribe and clinical-documentation-quality literature —
fabrication, distortion, omission, misattribution — plus two
clinically-motivated subtypes broken out on their own because a small
textual change carries outsized risk: numeric/medication errors (checked
deterministically, see Node 4) and negation errors (a denial flipped to
an affirmation or vice versa).

## Evaluation methodology

Standard practice in hallucination-detection research is to test against
an adversarial set with deliberately injected, known errors, since that
gives clean ground truth (as opposed to relying on however many errors a
model happens to produce naturally, which varies run to run and isn't
labeled). This project follows that pattern: each benchmark case pairs a
transcript with a note containing exactly one planted error of a known
category, plus at least one clean control case with no error at all, to
measure false positives, not just recall.

Both the pipeline and the single-prompt baseline are run against the
identical benchmark, using the identical underlying model where
comparable (Gemini Flash for both the baseline and the pipeline's
strongest node) — so that any measured difference reflects the workflow
design, not a difference in raw model capability.

Grading is done **blind**: the human grader sees each case's two outputs
labeled "System A" / "System B", randomized per case, without knowing
which is the pipeline and which is the baseline until after scoring is
complete. This guards against unconsciously grading generously in favor
of the system we built.

Metrics reported: recall (planted errors caught), severity-weighted
recall (numeric/medication and negation errors, the highest-risk
categories, count more), and false-positive rate on clean control cases.

## Example of iteration during development

Before ever calling the API, the deterministic numeric checker (Node 4)
was tested standalone against the benchmark. It initially produced a
false positive on case_04: it flagged "58 mg/dL" (a blood glucose lab
value from the transcript) as an unmatched medication dose, because the
regex for "dose" (`\d+\s*mg`) also matches the start of "mg/dL" lab-value
units. Fixed with a negative lookahead excluding `mg`/`mcg` matches
immediately followed by a slash. This is left in here deliberately as a
concrete example of the "design deterministic check -> test against
known cases -> find a real failure -> fix it" loop, rather than claiming
the first version of anything worked perfectly.

Second example: during initial setup, `gemini-2.5-flash` (the model
originally specified in `config.py`) returned a live `404 NOT_FOUND` from
the API with the message "no longer available to new users." Google had
moved new API keys onto the 3.x model generation. Fixed by updating
`config.py` to `gemini-3.6-flash` / `gemini-3.5-flash-lite`, both of
which are confirmed free-tier as of this writing. Lesson: pin model
names in one config file, not scattered through the codebase, specifically
because this kind of provider-side change is going to keep happening.

## Engineering under real constraints: multi-provider failover

During evaluation, Gemini's free tier turned out to allow only 5
requests/minute for `gemini-3.6-flash` - tight enough that a single
benchmark case (which was making one entailment call per claim, ~12
claims for a typical case) could exhaust it on its own. Two changes
followed from that, driven by the actual constraint rather than
decided upfront:

**1. Entailment moved from one call per claim to one call per case,
batched.** The original design deliberately checked each claim in a
separate, independent call, specifically to avoid the failure mode
where a model skims past one wrong fact buried in a long list - the
same failure mode the single-prompt baseline is vulnerable to. Batching
gives some of that up. What's preserved: claims are still extracted
into a clean atomic list *before* verification (a structural step the
baseline never gets), and the entailment call is required to return
exactly one verdict per input claim, in the same order - checked in
code (`len(result) != len(claims)` raises an error rather than
silently accepting a mismatched batch). That forced-coverage check is
the concrete thing standing in for "no claim gets lost," now that it's
one call instead of many. This is a real trade-off, documented
honestly rather than glossed over - not "batching was always the plan."

**2. Automatic failover across three providers, with a fairness
constraint that took real design work.** Groq and Featherless were
added as free/low-cost alternate providers (both OpenAI-API-compatible,
confirmed from their own docs) so a Gemini quota exhaustion doesn't
stop the whole evaluation. The subtlety: the entailment node and the
single-prompt baseline being compared against each other **must** use
the same underlying model for the comparison to mean anything (see the
fairness note in config.py). A naive per-call failover would let the
pipeline end up tested against Groq while the baseline stayed on
Gemini (or vice versa) purely by chance of which call happened to hit
the rate limit first - which would quietly invalidate every case's
comparison. The fix: a single shared, sticky "core-reasoning tier"
(`llm_router.py`) used by both the entailment node and the baseline.
If the active tier's provider fails on a quota/availability error, both
downgrade together, and the tier only ever moves down the chain, never
flaps back up mid-run. Whichever tier was active for a given case is
recorded in that case's result (`core_reasoning_provider` /
`core_reasoning_model` in `raw_outputs.json`), and `run_eval.py`
explicitly checks and warns if the pipeline and baseline ever end up
mismatched for the same case - which given the sticky design shouldn't
happen, but is verified rather than assumed.

Mechanical nodes (claim extraction, error classification) have no such
constraint - the baseline has no equivalent step to match against - so
they fail over independently and were moved off Gemini entirely, to
keep 100% of Gemini's tight 5 RPM budget free for the fairness-critical
comparison.

Error handling is asymmetric on purpose: a 429 (quota exhausted) fails
immediately with no retry, because retrying a per-minute quota error a
few seconds later essentially never helps, and every second spent
retrying is a second not spent trying the next provider. A 503
(transient overload) gets a short bounded retry, since that genuinely
is often temporary. Any other error (bad API key, malformed request)
fails immediately and is never silently swallowed by a provider
switch - a real bug should surface loudly, not get masked as "oh, it
just failed over."

## Known limitations (documented honestly, not hidden)

- The deterministic numeric check (Node 4) is a pattern-matcher for
  common formats (mg/mcg doses, blood-pressure readings written as
  "x/y" or "x over y"), not a full clinical NER system. It will miss
  numeric errors in less common formats.
- The benchmark is intentionally small during development; the
  submission version should be expanded to ~15-20 cases across all
  taxonomy categories plus multiple clean controls, per the plan in
  README.md.
- All data is synthetic. This is a deliberate scope choice for safe
  prototyping without any real patient data, not a claim that the system
  has been validated on real clinical documentation.
