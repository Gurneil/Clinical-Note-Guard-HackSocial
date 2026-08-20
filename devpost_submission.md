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

Nine nodes, each doing one job instead of asking a single prompt to do
everything at once. Node 0 is the transcript itself and node 3b only runs
in audio mode (both described below); these seven run on every note:

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

Across 56 cases, **graded blind by a human** — every case shown as
"System A" and "System B", randomised per case, with the key sealed until
scoring ran:

| | Recall | Severity-weighted recall | False positives (6 controls) |
|---|---|---|---|
| Pipeline | 47/50 (94%) | 93% | 13 |
| Baseline (single prompt) | 41/50 (82%) | 87% | 9 |

The automated proxy used during development predicted this almost exactly
— 88% vs 76%, the same 12-point gap — which says the cheap scorer was a
trustworthy instrument for the comparison it was used for, and harsher
than a human on both systems in absolute terms.

The pipeline catches meaningfully more planted errors than a single
open-ended prompt, even after fixing the baseline prompt to be
omission-aware so the comparison isn't just measuring an unfair
baseline. The trade-off: more false positives on clean notes, since
decomposing into many atomic claims creates more independent chances
for an over-literal judgment to misfire.

### Then we tested that claim on a stronger model, and it didn't hold

The result above used a 7B model for the reasoning both systems depend
on. We re-ran everything with a 70B model pinned in its place — about
ten times the parameters — and scored both runs with the same matcher
over the 44 planted-error cases that completed in both:

| Core-reasoning model | Pipeline | Baseline | Gap |
|---|---|---|---|
| Qwen2.5-7B | 39/44 (89%) | 33/44 (75%) | **+14 pts** |
| Llama-3.3-70B | 39/44 (89%) | 40/44 (91%) | **−2 pts** |

The pipeline scored identically on both. The baseline went from 33 to 40
once it had a competent model behind it — and two of the five cases it
gained are omissions, the failure mode our pipeline has a whole
dedicated node for.

The honest reading: **decomposition compensates for a weak reasoner
rather than adding capability on top of a strong one.** Structure
substituted for model quality here; it did not compound with it. And the
pipeline pays ~5.5× the tokens to arrive at the same place.

That narrows our claim rather than erasing it. The blind-graded result is
real on the model that run used, and "worth a great deal when your
reasoner is weak" is the situation any team on a free tier is actually
in. What it stops being is a general claim that workflow structure beats
a single good prompt. We'd rather report that than have a judge discover
it — and the experiment was in our own README as an open question before
we ran it.

(Caveats: auto-scored rather than blind human-graded, 44 of 60 cases —
ten lost to rate limits, not difficulty — and one run per model. Detail
in `eval/runs/README.md`.)

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
- **A provider withdrew two models mid-project.** Groq retired both models
  we were using, hours after a 60-case run that had been using them
  successfully. Our failover chain was built for providers going *down*,
  not for models being *removed* — a retired model returns 404, which we'd
  classified as a caller bug worth surfacing rather than an availability
  problem worth routing around, so calls died with a working fallback
  sitting unused in the same chain. Fixed narrowly: 404s that name the
  model now fail over; a 404 from a bad URL still surfaces. The
  replacement model's free tier caps at 8,000 tokens/minute against the
  ~580,000 a 60-case run needs, which makes a complete second evaluation
  run arithmetically impossible on a free tier. That ceiling is stated in
  `eval/runs/README.md` rather than left implied.
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

Decomposition-then-verify beats a single "find the errors" prompt when
the underlying reasoner is weak — and stops beating it when the reasoner
is strong. That was not the answer we expected, and finding it required
running the experiment against our own claim rather than around it.

The other lesson is that fairness in an eval — same provider per case,
same information in both prompts, an honest baseline — matters as much as
the pipeline design. Two separate times, the first version of a number we
were proud of turned out to be measuring an unfair comparison rather than
a real advantage.

## What's next

- **Finish the stronger-model check properly.** It's auto-scored over 44
  of 60 cases, with ten lost to rate limits. Re-running those and
  blind-grading the result would put that finding on the same footing as
  the headline number.
- **Tune node 5's notion of "clinically relevant"**, which currently
  flags genuinely important omissions and borderline ones at the same
  weight — the main driver of the false-positive rate.
- **Test whether node 4 earns its place on a model other than this one.**
  It contributed zero marginal recall here; if that holds across models,
  it's defence-in-depth rather than coverage, and should be justified as
  such or dropped.
```

---

## Built with (tags)

```
python, gemini-api, groq, featherless-ai, llama, qwen, whisper, faster-whisper, prompt-engineering, llm-as-judge, regex, html, css, javascript, unittest, json
```

---

## "Try it out" links

Live site — the guard runs in the browser on all 60 benchmark cases:
```
https://clinicalnoteguard.netlify.app
```

Repository (**[YOU]** — push before submitting; the link is already wired
into the site's "View on GitHub" button):
```
https://github.com/Gurneil/Clinical-Note-Guard
```

---

## Project Media

**[YOU]** — upload images (3:2 ratio, JPG/PNG/GIF, ≤5MB each, up to 15):
- `docs/workflow_flowchart.png` — the required workflow diagram, already made for this purpose
- A screenshot of the project site — the hero with the guard console,
  and/or the nine-node flow timeline on the "How the guard works" page
- A screenshot of the results table / scorecard, or `demo.py` running in a terminal

**Video demo** — **[YOU]**. The track requirements say video *or* document,
and `docs/SAMPLES.md` satisfies that. But in 2025 the organisers made a
video mandatory partway through the hackathon (Discord, Aug 16 2025:
"each team will be required to provide a video... detailing the function of
and the inspiration behind your project, and how it appeals to each of our
rubric categories"). Assume one is expected. Script in
`submission/demo-video-script.md`.

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
