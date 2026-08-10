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

The pipeline instead forces the check to happen claim-by-claim (see
`src/pipeline.py`; the module docstring there is the authoritative,
always-current version of this table - this one is kept in sync by hand):

| Node | What it does | Model / method | Why this step exists |
|---|---|---|---|
| 0 | Transcript input | Human-sourced data | The ground truth everything else is checked against |
| 1 | Draft the note | `DRAFT_CHAIN`: Gemini Flash first, Groq/Featherless as failover | Simulates what an ambient scribe produces. Not fairness-linked to anything (the baseline has no drafting step), so it's routed through a chain rather than calling Gemini directly - a Gemini outage shouldn't take the live demo down. |
| 2 | Extract atomic claims | `EXTRACT_CHAIN`: Groq/Featherless (mechanical tier, deliberately Gemini-free) | You can't verify a whole note at once reliably; you can verify one fact at a time. This step forces decomposition before any judgment happens. |
| 3 | Entailment check, BATCHED (all claims for one case, one request) | `CORE_REASONING_CHAIN`: Gemini Flash first, Groq/Featherless as failover - fairness-linked with the single-prompt baseline (see "Engineering under real constraints" below) | Checks every claim against the transcript in one structured pass, requiring exactly one verdict per claim, in order (a count mismatch is a raised error, not silently accepted). Returns supported / contradicted / not_mentioned plus a quoted evidence excerpt. Catches errors of **commission**: something in the note that shouldn't be there. |
| 4 | Deterministic numeric/medication check | Plain Python regex, no LLM | Exact numbers (doses, vitals) don't need a model's judgment, they need an exact match. This node exists specifically because numeric/medication errors are the highest-severity failure category, and a deterministic check on them has zero ambiguity — the "right tool for the job" instead of routing everything through an LLM by default. |
| 5 | Omission check, BATCHED (all transcript facts for one case, one request) | `OMISSION_CHAIN`: Groq/Featherless (mechanical tier, no fairness constraint) | The mirror image of nodes 2+3: extracts atomic facts from the *transcript* instead of the note, then checks whether each is mentioned anywhere in the note. Catches errors of **omission** - a clinically relevant detail the transcript stated that the note left out entirely. `taxonomy.json` calls omission out explicitly as needing "a different detection approach" from the commission categories above; this is that approach. |
| 6 | Classify flagged claims | `CLASSIFY_CHAIN`: Groq/Featherless, fixed taxonomy | Every commission flag (from node 3) gets a specific category, not just a generic "this seems wrong." Node 5's flags skip this step - they're already known to be "omission." Constraining classification to a fixed, literature-grounded taxonomy keeps output auditable and comparable across cases. |
| 7 | Human review checkpoint | Human | Required, not optional. Nothing is finalized without a person confirming it. This mirrors the actual clinical requirement that a clinician signs off on any AI-assisted note. |

Note on model names: `gemini-2.5-flash`/`Flash-Lite` are referenced in
some earlier project notes and in the "example of iteration" section
below; the project has since moved to `gemini-3.6-flash` for the
fairness-critical comparison (node 1 and node 3) after `2.5-flash`
returned a live 404 for new API keys - see that section for the full
story. Nodes 2, 5, and 6 never used Gemini at all, by design (see
"Engineering under real constraints" below).

## Where human input is required

There are three distinct points, not one token human-in-the-loop box:

1. **The source data itself** — every transcript is written by a human
   (in a real deployment: the actual conversation) and stands as the
   ground truth everything downstream is checked against.
2. **Implicit in Node 0** — in a live deployment, the *patient and
   clinician* are the human input generating the raw transcript.
3. **Node 7, explicitly** — a human reviewer sees every flagged item with
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

`taxonomy.json` describes omission as needing "a different detection
approach" from the rest - that used to be aspirational. The original
pipeline only ever extracted claims *from the note* and checked them
against the transcript (node 2+3), which structurally cannot notice
something the transcript said that the note left out; an omission case
added to the benchmark would have scored 0% recall against a detector
that was never built to catch it. Node 5 (added after the initial
6-case starter benchmark) closes that gap by running the same
extract-then-check pattern in the opposite direction: atomic facts out
of the transcript, then a check for whether each one made it into the
note.

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
design, not a difference in raw model capability. The benchmark is 60
cases: 10 numeric_medication_error, 10 fabrication, 10 negation_error, 8
distortion, 7 misattribution, 7 omission, and 8 clean controls (see
`data/test_cases.json`). Expanded from an original 18-case starter set
specifically because 18 cases meant a 2-case swing in either system's
catch count read as an 8-13 percentage-point swing in the headline
number - not enough cases to say the workflow comparison, rather than
noise, was driving the result. 60 cases doesn't make every
per-category number tight (7-10 cases per category is still small), but
it moves the *overall* recall comparison onto much sturdier ground.

**A second, independent fairness gap was found and fixed alongside the
benchmark expansion**: the single-prompt baseline's prompt
(`src/baseline.py`) originally asked only for "inaccuracies,
fabrications, or discrepancies" - errors of commission - while the
pipeline runs a dedicated omission-detection node (Node 5) and the
benchmark scores both systems on omission cases. That meant part of the
pipeline's measured recall advantage was the baseline never having been
told to look for the failure mode it was being graded on, not the
workflow doing anything smarter. The baseline prompt now explicitly asks
for both directions (see the prompt's own docstring for the full
reasoning); what still differs between the two systems - and is the
actual thing this evaluation is testing - is workflow structure: atomic
claim decomposition, forced one-verdict-per-claim coverage, the
deterministic numeric tier, and the fixed taxonomy, none of which the
baseline gets.

Grading is done **blind**: the human grader sees each case's two outputs
labeled "System A" / "System B", randomized per case, without knowing
which is the pipeline and which is the baseline until after scoring is
complete. This guards against unconsciously grading generously in favor
of the system we built. `eval/compute_metrics.py --include-mismatches`
exists for debugging only - real reported numbers should always come
from the default (mismatch-excluded) run.

Metrics reported: recall (planted errors caught), severity-weighted
recall (numeric/medication and negation errors, the highest-risk
categories, count more), and false-positive rate on clean control cases.
Cases where the pipeline and baseline ended up on different providers
mid-run (a "fairness mismatch" - see the failover section below) are
excluded from these numbers by default, reported separately instead of
being silently folded into the headline result.

For a fully automated (non-blind) alternative that doesn't require a
human grading session, see `eval/auto_score.py` - it scores
`raw_outputs.json` directly against `ground_truth` using keyword/phrase
overlap rather than a person's judgment. It's a reasonable proxy for
iterating quickly and is what was used to produce the numbers in this
repo's `eval/` output during development, but it is *not* a replacement
for the blind human-grading workflow above for a final, citable result:
automated string matching can both over- and under-credit a system
relative to what a clinician would actually judge as "caught this
error." Both scripts read/write the same file formats, so either can be
used depending on whether a human grading session is available.

### Current auto-scored results (proxy, not blind-graded - see above)

From the eval run committed in `eval/raw_outputs.json` (60 cases, at
`temperature=0.0`, run against the omission-aware baseline prompt
described above). Provider mix for this run, taken directly from
`raw_outputs.json` rather than assumed: `gemini-3.6-flash` for the
first 3 cases before the daily quota (20 requests/day - see the
failover section below) was exhausted, `groq/llama-3.3-70b-versatile`
for 2 more cases, and `featherless/Qwen2.5-7B-Instruct` for the
remaining 53 - so, as with the original 18-case run, this reflects
mostly Featherless/Qwen's judgment quality, not Gemini's, simply because
one 60-case run burns through the free tier's daily cap almost
immediately. This is a real, disclosed constraint of running on free
tiers, not something the numbers below pretend isn't true.

Of the 60 cases, 2 failed outright (Groq's `llama-3.1-8b-instant`
returned malformed JSON on both retry attempts for the omission-check
batch on `case_05_misattribution` and `case_60_clean_control_conjunctivitis`
- recorded with their raw error in `raw_outputs.json` rather than
silently dropped or counted as "no error found") and 1 more
(`case_06_clean_control`) was excluded for a genuine fairness mismatch.
The numbers below are over the remaining 57 cases (51 with a planted
error, 6 clean controls) - see `eval/auto_scorecard.json` for the
per-case detail.

| | Recall | Severity-weighted recall | False positives (6 controls) |
|---|---|---|---|
| Pipeline | 45/51 (88%) | 92% | 15 |
| Baseline | 39/51 (76%) | 83% | 11 |

Read honestly, not just as "pipeline wins": at 57 scored cases (roughly
3x the original 18-case run), a 6-case recall gap is a materially more
trustworthy signal than the earlier run's 2-case gap was, and it
persists even after closing the baseline-prompt fairness gap described
above - so this reads as real evidence for the core claim this project
is testing, decomposition-then-verify catches more planted errors than
one open-ended prompt, not just an artifact of a small sample or an
unfair baseline. But the pipeline's false-positive count on clean notes
(15 across 6 controls, roughly 2.5/note) is still meaningfully higher
than the baseline's (11, roughly 1.8/note), for the same understood
reason as before: decomposing a note into many atomic claims/facts
creates many independent opportunities for an over-literal per-item
judgment to misfire (see the residual paraphrase-recognition gap
above), where the baseline's single holistic read tends to be more
conservative and simply misses subtler errors instead of flagging
borderline-fine things. That's a genuine precision/recall trade-off,
not a bug to hide - a system that misses roughly one in four real
errors is not obviously better than one that catches more real errors
at the cost of more false alarms for human review to dismiss. Which
trade-off is preferable depends on deployment context (a human is
reviewing every flag either way - see Node 7), and is exactly the kind
of judgment call worth surfacing to a grader rather than burying behind
a single "our system wins" headline number.

Two things worth doing before treating either number as final: (1) rerun
on a day with a full, unused Gemini quota (or spread the run across
multiple days) so the fairness-critical comparison is actually measuring
Gemini-vs-Gemini rather than Featherless-vs-Featherless most of the
time - the workflow-design claim should hold on a stronger model too,
but that's not yet directly confirmed at 60-case scale; and (2) the
blind human grading pass described above, which is still the project's
stated methodology and has not yet been run at the 60-case scale (see
"Current status" in the README).

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

During evaluation, Gemini's free tier turned out to be tight enough that
a single benchmark case (which was originally making one entailment call
per claim, ~12 claims for a typical case) could exhaust it on its own.
Worth correcting honestly rather than repeating uncritically: earlier
project notes documented this as "5 requests/minute," but that figure
was never actually confirmed against a real error at the time - it
looks to have come from Google's generic published rate-limit page
rather than from a limit this project had actually hit. The first real
429 this project observed directly, via `smoke_test.py`, told a
different story: `quotaId:
"GenerateRequestsPerDayPerProjectPerModel-FreeTier"`, `limit: 20` - a
**daily** cap of 20 requests for `gemini-3.6-flash`, not a per-minute
one. Free-tier limits can differ by metric and by account and may
change over time; the failover code doesn't depend on knowing the exact
number either way, since it reacts to whatever 429/503 actually comes
back rather than pre-counting requests - but the documentation
shouldn't repeat a number that direct evidence has since contradicted.
Two changes followed from the general shape of the constraint (tight
enough that a handful of calls can exhaust it), driven by the actual
limitation rather than decided upfront:

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

Mechanical nodes (claim extraction, classification, and the newer
omission check - node 5) have no such constraint - the baseline has no
equivalent step to match against - so they fail over independently and
were moved off Gemini entirely, to keep 100% of Gemini's tight free-tier
budget free for the fairness-critical comparison.

Error handling is asymmetric on purpose: a 429 (quota exhausted) fails
immediately with no retry, because retrying a quota error a few seconds
later essentially never helps regardless of whether the underlying
window is a minute or a day, and every second spent retrying is a
second not spent trying the next provider. A 503
(transient overload) gets a short bounded retry, since that genuinely
is often temporary. Any other error (bad API key, malformed request)
fails immediately and is never silently swallowed by a provider
switch - a real bug should surface loudly, not get masked as "oh, it
just failed over."

## Reproducibility: pinning temperature after catching ourselves almost trusting a lucky run

Running the full 18-case eval twice in a row, with no code changes in
between, produced meaningfully different results: 100% pipeline recall
on one run, 87% on the next. Neither run was wrong - both are real
model outputs - but reporting whichever one happened to run last (or
worse, running it repeatedly and keeping the best number) would have
been exactly the kind of quiet result manipulation this project
explicitly rules out. The cause: neither LLM client pinned a
`temperature`, so every call sampled at the provider's default
(non-zero) temperature. Every node in this pipeline - claim extraction,
entailment checking, omission checking, classification - is a
judgment/extraction task, not a creative one, so there is no reason to
sample instead of taking the model's single best answer. Both clients
now default to `temperature=0.0`. This doesn't guarantee byte-identical
output on every provider (some providers still have minor residual
nondeterminism even at temperature 0, particularly for quantized models
served through aggregators like Featherless), but it removes the single
largest source of run-to-run noise. Numbers reported anywhere in this
project's `eval/` output or documentation were produced after this fix
was in place, not before - and should still be read as one run of a
noisy process, not a guaranteed-reproducible ground truth, especially
on any category that only has 2-3 benchmark cases.

## Cost and latency (measured, not estimated)

Sustainability/scalability claims are only worth something if backed by a
real number, not "should be efficient." `src/usage.py` records every LLM
call's provider, model, token counts (from the provider's own response
metadata, never estimated locally), and wall-clock latency - failed calls
included, since a failover that burns a 20-second timeout before falling
back to the next provider is a real cost of the multi-provider design, not
a free retry. `eval/measure_usage.py` runs both systems on a fixed,
diverse 7-case sample (one of each error category plus a clean control)
and reports the aggregate - a small sample rather than all 60 cases,
because per-call cost doesn't depend on which case is being checked or
whether the answer was right, so this is real measured data at a fraction
of the API budget a full second eval run would cost (see the free-tier
constraints discussed above).

Measured on this repo's providers (mixed Gemini/Groq/Featherless per the
sticky failover tier - see `eval/usage_summary.json` for the full
per-case breakdown):

| | Pipeline | Baseline |
|---|---|---|
| LLM calls per note | 5.3 | 1.0 |
| Tokens per note | ~3,280 | ~600 |
| Wall-clock latency per note | ~12.8s | ~7.5s |

Read honestly: the pipeline costs roughly **5.5x the tokens and ~1.7x the
latency** of the baseline per note checked. That is a real, direct cost of
decomposition (multiple calls: extraction, entailment, omission-fact
extraction, omission-check, classification, vs. the baseline's single
call) and it is the number that should sit next to the recall table above
when judging whether the accuracy gain is "worth it" for a given
deployment - not a question this project answers on the team's behalf,
since the right trade-off depends on note volume and review-staff cost at
the deploying organization. All measurements here are on free-tier
API pricing (actual spend: $0); this project does not publish a
per-request dollar estimate because per-token prices vary by provider,
change over time, and this project has not verified current pricing
against any provider's own page - reporting an unverified number would be
worse than reporting none. Anyone wanting a dollar figure can multiply the
token counts above by their own negotiated or published provider rate.

## Known limitations (documented honestly, not hidden)

- The deterministic numeric check (Node 4) is a pattern-matcher for
  common formats (mg/mcg doses, blood-pressure readings written as
  "x/y" or "x over y"), not a full clinical NER system. It will miss
  numeric errors in less common formats.
- The omission check (Node 5) depends on the extraction prompt's notion
  of "clinically relevant" - in practice it has flagged both genuinely
  important omissions (a documented drug allergy, a medication
  interaction discussion) and borderline ones (a doctor's verbal
  reassurance like "should resolve on its own" that's arguably implied
  rather than a discrete fact). This is a real precision/recall
  trade-off in the extraction prompt, not yet tuned, and worth narrowing
  before treating omission recall as a headline metric on the same
  footing as the commission categories.
- Both node 3 (entailment) and node 5 (omission) were patched, during
  real eval runs, to explicitly credit clinical-terminology paraphrases
  and combined/summarized restatements as "supported"/"mentioned"
  rather than requiring near-literal wording (see the two "Fix real
  false-positive sources" commits). A residual case survived even that
  fix: a note line like "Denies changes in weight, appetite, sleep, or
  energy" - extracted as 4 separate atomic transcript facts - sometimes
  still gets marked contradicted/omitted against a transcript where the
  patient just said "everything's been stable," because recognizing
  that a general statement implies several specific negations is a
  harder inference than a direct synonym match. Deliberately NOT chased
  further with more prompt patches: each fix so far targeted a clear,
  generalizable gap: past that, additional narrow patches risk
  overfitting the prompts to this specific benchmark rather than
  producing genuinely more robust reasoning. This is the honest edge of
  what zero-shot prompting gets you here - the residual false-positive
  rate below is reported with this still present, not after
  hand-tuning it away.
- The benchmark is 60 cases (10 numeric_medication_error, 10
  fabrication, 10 negation_error, 8 distortion, 7 misattribution, 7
  omission, 8 clean controls) - up from an original 18-case starter set
  specifically because 18 cases meant the headline recall comparison
  could swing 8-13 points from a 2-case difference, which wasn't a
  believable margin. 60 cases is large enough that the overall
  pipeline-vs-baseline comparison holds up to a 6-case gap being a real
  signal rather than noise, but individual categories still only have
  7-10 cases each, too few for tight per-category confidence; a
  production benchmark would want dozens of cases per category, not
  under 10.
- The deterministic numeric checker (Node 4) only recognizes mg/mcg
  doses and blood-pressure readings written as "x/y" or "x over y" - a
  weight in kilograms, a bare lab value with no unit, an insulin dose in
  units, or a medication-name substitution with no numeric change at all
  are real numeric_medication_error cases it will not catch (see
  `tests/test_deterministic_check.py`,
  `test_numeric_cases_outside_the_regex_format_are_not_caught_deterministically`,
  which exists specifically to keep this limitation from silently
  regressing into a false claim of coverage). Node 3's LLM entailment
  check is the second line of defense for exactly these cases, not a
  redundant check.
- Blind human grading (the default methodology - see "Evaluation
  methodology" above) requires an actual human grading session, which
  wasn't run for the numbers in this repo's `eval/` output; those were
  produced by `eval/auto_score.py`, an automated proxy, and are labeled
  as such everywhere they're reported. A true blind grading pass by a
  qualified reviewer, before treating any number here as a final
  submission result, is a recommended next step, not an optional one.
- All data is synthetic. This is a deliberate scope choice for safe
  prototyping without any real patient data, not a claim that the system
  has been validated on real clinical documentation.
