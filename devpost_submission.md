# Devpost Submission — Ready-to-Paste Content

Copy each section into the matching field on the "Project details" and
"Additional info" pages. Notes on the few things you still need to do
yourself are marked **[YOU]**.

---

## Project overview

**Project name** (41 char limit)
```
Clinical Note Hallucination Guard
```
(33 characters)

**Elevator pitch**
```
A QA layer that catches AI hallucinations in clinical notes before a clinician signs off.
```

---

## Project details → About the project

```markdown
## Inspiration

AI "ambient scribe" tools that draft clinical notes from doctor-patient
conversations are one of the most actively deployed categories of
healthcare AI right now. Studies on AI-generated clinical documentation
have found meaningful hallucination rates — fabricated symptoms, altered
severity, wrong doses, flipped negations. Every clinical body involved
agrees AI-drafted notes need human review before signing. The open
problem is that reviewing a whole note by eye, hoping to catch what's
wrong, is slow and unreliable. We wanted to build the systematic check
that review can actually lean on.

**This project does not diagnose patients or recommend treatment.** It's
a documentation-reliability tool that keeps clinical judgment with a
human at every step. All data used anywhere in the project is
synthetic — invented transcripts about fictional patients. No real
patient data is used or needed anywhere.

## What it does

Instead of trusting one model call to draft a note and hoping it's
accurate, the pipeline decomposes the note into individually-verifiable
claims, checks each one against the source transcript independently,
and flags anything unsupported before it reaches a human reviewer. It
catches both errors of **commission** (something in the note that
wasn't said) and **omission** (something said that the note left out) —
across a taxonomy grounded in the ambient-scribe literature: fabrication,
distortion, omission, misattribution, numeric/medication errors, and
negation errors.

## How we built it

Seven-node pipeline, each node doing one job instead of asking a single
prompt to do everything at once:

1. **Draft** the note from the transcript (simulates the ambient scribe)
2. **Extract** atomic claims from the note
3. **Entailment check** — batch-verify every claim against the transcript,
   supported / contradicted / not_mentioned, with a quoted evidence excerpt
4. **Deterministic numeric/medication check** — plain regex, no LLM,
   because exact doses and vitals don't need a model's judgment
5. **Omission check** — the mirror image of 2+3: extract facts from the
   *transcript* and check whether the note covers each one
6. **Classify** every flagged claim into the fixed taxonomy
7. **Human review checkpoint** — required, not optional; nothing is
   finalized without a person confirming it

Multi-provider failover (Gemini → Groq → Featherless) keeps the pipeline
running through free-tier rate limits, with the core-reasoning
comparison against our single-prompt baseline fairness-linked to the
same provider per case so the comparison isn't accidentally testing two
different models. A dedicated node (3b) treats the transcript itself as
a model output rather than ground truth when running in audio mode —
downgrading claims resting on low-confidence transcription to
"unverifiable" instead of silently trusting a bad transcript.

We built a 60-case synthetic benchmark (numeric/medication errors,
fabrication, negation, distortion, misattribution, omission, and clean
controls), a blinded scorecard workflow for human grading, and an
automated scoring proxy for fast iteration.

## Results

Across 57 scored cases (auto-scored proxy, not yet blind-graded — see
"What's next"):

| | Recall | Severity-weighted recall | False positives (6 controls) |
|---|---|---|---|
| Pipeline | 45/51 (88%) | 92% | 15 |
| Baseline (single prompt) | 39/51 (76%) | 83% | 11 |

The pipeline catches meaningfully more planted errors than a single
open-ended prompt, even after fixing the baseline prompt to be
omission-aware so the comparison isn't just measuring an unfair
baseline. The trade-off: more false positives on clean notes, since
decomposing into many atomic claims creates more independent chances
for an over-literal judgment to misfire.

## Challenges we ran into

- **Free-tier rate limits mid-eval.** Gemini's 20-request/day cap meant
  a single 60-case run burns through the quota almost immediately, so
  most of a given run's core-reasoning judgments come from the failover
  model rather than Gemini. We built the router to fail over
  automatically and log which provider actually handled each case,
  rather than silently assuming the intended model ran.
- **An unfair baseline was inflating our own result.** Our baseline
  prompt originally only asked about commission errors while being
  scored on omission cases the pipeline had a dedicated node for. Fixing
  that closed part of the recall gap — the honest number is smaller than
  the first one we measured, and we kept the fix.
- **A too-small benchmark.** An 18-case starter set meant a 2-case swing
  read as an 8–13 point swing in the headline recall number — not a
  believable margin. We expanded to 60 cases specifically to make the
  measured gap trustworthy rather than noise.
- **Malformed JSON from smaller models mid-batch**, and a single failing
  case discarding an entire eval run — both hardened against directly in
  `run_eval.py` after hitting them for real.
- **The transcript isn't ground truth in audio mode.** A verdict is only
  as good as the audio it was checked against, so node 3b calibrates a
  confidence threshold (via a dedicated degradation experiment) instead
  of trusting ASR output blindly.

## Accomplishments we're proud of

- Node ablation shows real evidence for *which* pipeline nodes are
  earning their keep — including one node (deterministic numeric check)
  contributing zero additional recall on this benchmark, and reporting
  that honestly instead of hiding it.
- A full cost/latency measurement of pipeline vs. baseline, not an
  estimate.
- A reproducibility fix: pinning temperature after discovering that
  temperature alone swung a run between very different results.

## What we learned

Decomposition-then-verify beats a single "find the errors" prompt, but
it isn't free — precision drops as recall rises, and a documentation QA
tool needs both measured, not just the flattering one. Fairness in an
eval (same provider per case, same prompt information, an honest
baseline) matters as much as the pipeline design itself.

## What's next

- The blind human-graded scorecard is the project's own stated
  methodology; the numbers above are the automated proxy, labeled as
  such everywhere they're cited. Filling in the blind scorecard is the
  one remaining step before treating any number here as final.
- Rerunning the full 60-case comparison on a fresh Gemini quota, since
  this run's core-reasoning comparison landed mostly on the failover
  model rather than Gemini.
```

---

## Built with (tags)

```
python, gemini-api, groq, featherless-ai, llama, qwen, whisper, faster-whisper, prompt-engineering, llm-as-judge, regex, html, css, javascript, unittest, json
```

---

## "Try it out" links

**[YOU]** — the repo isn't pushed to GitHub yet (no git remote configured
locally). Push it, then add:
```
https://github.com/<your-username>/clinical-note-guard
```
Also consider a second link to the project site if you host it: build with
`cd landing && npm run build` and deploy `landing/dist/` (it uses a hash
router, so plain static hosting like GitHub Pages works without rewrites).
It walks through the pipeline and replays the committed eval run
claim-by-claim in the browser.

---

## Project Media

**[YOU]** — upload images (3:2 ratio, JPG/PNG/GIF, ≤5MB each, up to 15):
- `docs/workflow_flowchart.png` — the required workflow diagram, already made for this purpose
- A screenshot of the project site (`landing/`) — the hero with the guard console,
  and/or the nine-node flow timeline on the "How the guard works" page
- A screenshot of the results table / scorecard, or `demo.py` running in a terminal

**Video demo link** — optional per your own README: the track requires a
video *or* a document, and `docs/SAMPLES.md` (pipeline vs. baseline on 4
real cases) already satisfies that. Skip the video unless you want one.

---

## Additional info (judges/organizers only)

**Track:**
```
ML & Prompt Engineering
```
(`docs/PROMPTS.md` is explicitly written as a submission doc for this
track — every prompt verbatim, what each constraint prevents, and the
iteration history.)

**Anything else you'd like us to know?**
```
All data in this project is synthetic (invented transcripts about
fictional patients) — no real patient data is used or needed anywhere.
The headline numbers in docs/ARCHITECTURE.md are from an automated
scoring proxy (eval/auto_score.py), explicitly labeled as such; the
blind human-graded pass (the project's own stated methodology) is the
one step still open before treating those numbers as final — see
"Current status" in README.md.
```
