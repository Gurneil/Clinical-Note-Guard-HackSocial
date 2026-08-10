# Clinical Note Hallucination Guard

A QA layer for AI-drafted clinical notes ("ambient scribe" style tools).
Instead of trusting a single model call to draft a note and hoping it's
accurate, this pipeline decomposes the note into individually-verifiable
claims, checks each one against the source transcript independently, and
flags anything unsupported before it reaches a human reviewer.

**This project does not diagnose patients or recommend treatment.** It is
a documentation-reliability tool that assumes clinical judgment stays
with a human at every step. All data used anywhere in this project is
synthetic — invented transcripts about fictional patients, written for
this project. No real patient data is used or needed anywhere.

## Why this exists

Real, current problem: studies on AI-generated clinical documentation
have found meaningful hallucination rates in AI-drafted notes, and every
clinical body involved agrees human review before signing is
non-negotiable. This project builds the QA layer that makes that review
faster and more systematic than a clinician just re-reading the whole
note and hoping they catch what's wrong.

## Project structure

```
clinical-note-guard/
├── LICENSE                 # MIT
├── taxonomy.json          # error categories, grounded in the literature
├── .env.example            # API key variable names (copy to .env, fill in, never commit)
├── smoke_test.py            # verifies every provider + the failover router, no eval cost
├── demo.py                  # interactive walkthrough of a single benchmark case
├── frontend/
│   ├── index.html          # project site: the problem, the pipeline film, a runnable
│   │                        # claim-by-claim demo of case_01, and the measured results.
│   │                        # Static, no build step - open the file in a browser.
│   └── media/
│       └── pipeline-flow.mp4  # 6s pipeline film shown in the site's pipeline section
│                              # (generated with Higgsfield / MiniMax 2.3)
├── data/
│   ├── audio/
│   │   └── case_01_synthetic.wav  # case_01 spoken by two Windows TTS voices, so
│   │                        # `--audio` is runnable without recording anything.
│   │                        # Synthetic speech of a synthetic transcript: still
│   │                        # no real patient, and no real clinician, anywhere.
│   └── test_cases.json    # synthetic benchmark: transcripts + notes +
│                           # ground truth for planted errors (60 cases)
├── src/
│   ├── _env.py                   # loads .env once, imported by the three files below
│   ├── config.py                 # provider/model failover chains, and why
│   ├── llm_router.py             # dispatch + automatic failover + fairness-linking
│   ├── gemini_client.py          # Gemini API wrapper
│   ├── openai_compat_client.py   # shared Groq + Featherless wrapper (both OpenAI-compatible)
│   ├── usage.py                  # per-call token/latency recorder - real cost data, not estimated
│   ├── transcribe.py             # node 0 for real audio: Whisper via Groq (or a local
│   │                              # faster-whisper failover), with per-segment confidence
│   ├── transcript_confidence.py  # node 3b: a verdict is only as good as the audio it was
│   │                              # checked against - downgrades claims resting on
│   │                              # unreliable audio to "unverifiable"
│   ├── pipeline.py               # the guard pipeline, nodes 0-7 (commission + omission + human checkpoint)
│   └── baseline.py               # single-prompt comparison baseline (now omission-aware, see ARCHITECTURE.md)
├── tests/                   # stdlib unittest, no real API calls, run before every change
│   ├── test_deterministic_check.py
│   ├── test_llm_router.py
│   ├── test_omission_check.py
│   ├── test_openai_compat_client.py
│   └── test_auto_score.py
├── eval/
│   ├── run_eval.py         # runs both systems, writes a BLINDED scorecard (resilient to a
│   │                        # single case erroring out - see run_eval.py's own comments)
│   ├── compute_metrics.py  # scores the filled-in blind scorecard by hand
│   ├── auto_score.py       # automated (non-blind) scoring proxy - see ARCHITECTURE.md
│   ├── ablation.py         # re-scores the committed run with each node withheld, to measure
│   │                        # what each node actually contributed (zero API calls)
│   ├── ablation_results.json # committed: the ablation table reported in ARCHITECTURE.md
│   ├── measure_usage.py    # measures real token/latency cost per note, pipeline vs. baseline
│   ├── asr_confidence_check.py    # calibrates node 3b's threshold: degrades audio in steps and
│   │                        # measures confidence against whether the clinical facts survived
│   ├── asr_confidence_results.json # committed: the calibration run reported in ARCHITECTURE.md
│   ├── raw_outputs.json    # committed: full output from the actual eval run reported in the docs
│   ├── scorecard_blind.csv # committed: blinded grading sheet from that same run
│   ├── blind_key.json      # committed: A/B -> pipeline/baseline key for that run
│   ├── auto_scorecard.json # committed: per-case auto_score.py detail for that run
│   └── usage_summary.json  # committed: per-case cost/latency detail from measure_usage.py
└── docs/
    ├── ARCHITECTURE.md            # reasoning behind every node + reported results (submission doc)
    ├── PROMPTS.md                 # every prompt, what each constraint prevents, and the
    │                              # iterations behind them (submission doc)
    ├── SAMPLES.md                 # pipeline vs. baseline on real cases (submission doc)
    ├── workflow_flowchart.png     # the required workflow diagram (submission asset)
    ├── generate_flowchart.py      # regenerates workflow_flowchart.png (dev tool, needs matplotlib)
    │                              # (see also eval/ablation.py - measures each node's marginal
    │                              #  contribution from the committed run, no API calls)
    └── generate_samples_doc.py    # regenerates SAMPLES.md from eval/raw_outputs.json (dev tool)
```

## Setup

1. Install Python 3.10+ (you're on 3.12, that's fine).
2. `pip install -r requirements.txt`
3. Get a free Gemini API key (no credit card) at
   https://aistudio.google.com/apikey
4. Optional but recommended - free automatic failover if Gemini's quota
   runs out mid-run:
   - Groq: free key (no card) at https://console.groq.com
   - Featherless: key from your account dashboard at https://featherless.ai
5. Set whichever keys you have. Two ways to do this - never hardcode a
   key in any source file either way:

   **Recommended: a `.env` file.** Copy `.env.example` to `.env` in the
   project root and fill in whichever keys you have:
   ```
   GEMINI_API_KEY=your-key-here
   GROQ_API_KEY=your-key-here
   FEATHERLESS_AI_API_KEY=your-key-here
   ```
   `.env` is already in `.gitignore` and is never committed. It's loaded
   automatically (see `src/_env.py`) regardless of which directory you
   run a command from, so this is the easiest option if you're running
   commands from different folders (`src/`, `eval/`, project root).

   **Alternative: shell environment variables**, if you'd rather not use
   a file:
   ```
   export GEMINI_API_KEY="your-key-here"
   export GROQ_API_KEY="your-key-here"             # optional
   export FEATHERLESS_AI_API_KEY="your-key-here"   # optional
   ```
   Windows PowerShell: `$env:GEMINI_API_KEY="your-key-here"` (same for the others)
   Windows Command Prompt: `set GEMINI_API_KEY=your-key-here` (same for the others)

   Either way, `FEATHERLESS_API_KEY` is also accepted as an alias for
   `FEATHERLESS_AI_API_KEY` — both names work.

**Verify your keys actually work before running the eval:**
```
D:\Python312\python.exe smoke_test.py
```
One minimal call per provider (so confirming Gemini costs 1 request out
of its tight free-tier daily quota - 20/day observed for
gemini-3.6-flash, see docs/ARCHITECTURE.md), plus a test of the failover
router itself. Providers with no key set are reported as SKIPPED — never
silently omitted.

   Note: if `python` isn't recognized on PATH (common when Python is
   installed somewhere like `D:\Python312`), use the full path to your
   interpreter for every command below, e.g.
   `D:\Python312\python.exe -m pip install -r requirements.txt`.

   Gemini alone is NOT enough to run the full pipeline: extraction,
   classification, and the omission check (`EXTRACT_CHAIN`,
   `CLASSIFY_CHAIN`, `OMISSION_CHAIN` in `src/config.py`) are Groq →
   Featherless only, deliberately Gemini-free (see config.py's own
   comments for why) - so you need at least one of Groq or Featherless
   set as well, or those nodes have nothing to call. Gemini alone is
   enough for `single_prompt_check()` (the baseline) and, on its own,
   `entailment_check_batch()` - but not a full `run_guard()` call. Any
   provider with no key set is automatically skipped with a loud warning,
   not a silent error (see src/llm_router.py) - use `smoke_test.py` to
   confirm what you actually have working before running the eval.

## Running things

**Live demo** (draft a note from a transcript, then guard-check it, with
an interactive human review at the end):
```
python demo.py                # pick a benchmark transcript from a menu
python demo.py 3               # run case #3 directly, skip the menu
python demo.py 3 --no-review   # skip the interactive y/n review prompts
```
This is `pipeline.run_full_pipeline()` end to end - the only way to run
it from the command line rather than a hand-typed `python -c "..."`.

**Sanity-check your Gemini key works:**
```bash
cd src
python -c "from gemini_client import call_model; print(call_model('Say hi in 5 words.', model='gemini-3.6-flash'))"
```

**Sanity-check the full failover-aware baseline call path** (this is the
one that actually exercises the router):
```bash
cd src
python -c "from baseline import single_prompt_check; print(single_prompt_check('Patient reports headache for 2 days.', 'Subjective: Patient reports headache for 2 days and nausea.'))"
```
Expected: a tuple of `(result, provider, model)` - if Gemini's quota is
exhausted, you should see it print a downgrade message and come back
with `provider='groq'` (or `'featherless'`) instead of hanging or crashing.

**Run the full evaluation** (this is the core deliverable — it runs the
pipeline and the baseline across every case in the benchmark):
```bash
cd eval
python run_eval.py
```
This writes `raw_outputs.json` (full detail) and `scorecard_blind.csv`
(a blinded grading sheet — fill in the 4 blank columns by hand without
looking at `blind_key.json` first, so you're not unconsciously grading
generously in favor of the system you built).

**After grading the scorecard (blind, human):**
```bash
python compute_metrics.py
```
This prints recall, severity-weighted recall, and false-positive counts
for both systems side by side. Cases where the pipeline and baseline
ended up on different providers mid-run are excluded by default (pass
`--include-mismatches` to score them anyway - not recommended for a
final result).

**Or, without a human grading session (automated proxy):**
```bash
python auto_score.py
```
Scores `raw_outputs.json` directly against `ground_truth` using
keyword/phrase matching instead of a person's judgment. Faster to
iterate with, but not a substitute for the blind human-graded numbers
above in a final write-up - see "Evaluation methodology" in
`docs/ARCHITECTURE.md` for why.

**Measure real cost/latency** (a small, diverse 7-case sample, not the
full 60 - see the script's own docstring for why that's still a valid
measurement):
```bash
python measure_usage.py
```
Writes `usage_summary.json` and prints an average tokens/calls/latency
table for the pipeline vs. the baseline - see `docs/ARCHITECTURE.md`,
"Cost and latency", for the numbers from the committed run.

## Current status / what's left before submission

- [x] Taxonomy defined (grounded in ambient-scribe literature)
- [x] Pipeline built: 6 automated nodes (extraction, entailment, deterministic
      numeric check, omission check, classification, plus draft for the live
      demo) + a required human review checkpoint
- [x] Benchmark: 60 cases - 10 numeric_medication_error, 10 fabrication, 10
      negation_error, 8 distortion, 7 misattribution, 7 omission, 8 clean
      controls. Expanded from an original 18-case starter set because 18
      cases meant a 2-case swing read as an 8-13 point swing in the
      headline recall number - not a believable margin (see
      `docs/ARCHITECTURE.md`, "Evaluation methodology").
- [x] Baseline prompt fixed to be omission-aware (`src/baseline.py`) - it
      previously asked only for commission errors while being scored on
      omission cases the pipeline had a dedicated node for, which meant
      part of the measured recall gap was an unfair prompt, not the
      workflow design being tested. See the prompt's own docstring.
- [x] Full eval run against all 60 cases, committed (`eval/raw_outputs.json`
      and friends) - see `docs/ARCHITECTURE.md`, "Current auto-scored results"
- [x] `run_eval.py` hardened against a single case's API failure discarding
      the whole run's results (a real bug hit while producing this run -
      see the script's own comments)
- [x] Real cost/latency measurement (`eval/measure_usage.py`,
      `eval/usage_summary.json`) - see `docs/ARCHITECTURE.md`, "Cost and
      latency"
- [x] Required workflow flowchart (`docs/workflow_flowchart.png`)
- [x] Required documentation (`docs/ARCHITECTURE.md`) - taxonomy, per-node
      reasoning, failover engineering, reproducibility fixes, real results,
      known limitations, all as they actually happened rather than planned
- [x] Required samples document (`docs/SAMPLES.md`) - pipeline vs. baseline
      on 4 real cases, generated directly from the committed eval output
- [x] Prompt-engineering record (`docs/PROMPTS.md`) - every prompt verbatim,
      what each constraint prevents, and the iterations behind them
- [x] Node ablation (`eval/ablation.py`) - each node's marginal contribution
      measured from the committed run, no API calls. Reports node 4 as
      contributing zero additional recall, which is not the flattering
      result but is the measured one
- [x] Audio mode + node 3b (`src/transcribe.py`, `src/transcript_confidence.py`)
      - the transcript treated as a model output rather than as ground
      truth, with the confidence threshold calibrated by experiment
      (`eval/asr_confidence_check.py`) and a worked example in
      `docs/SAMPLES_AUDIO.md`
- [x] LICENSE (MIT)
- [x] Project site (`frontend/index.html`) - static, no build step. Not a
      track requirement for ML Prompt Engineering; included because it
      explains the workflow to a reader who won't run the code, and it
      doubles as the backdrop for a demo video.
- [ ] **Blind human grading pass.** The numbers currently in `docs/` come
      from `eval/auto_score.py`, an automated proxy explicitly labeled as
      such everywhere it's cited - not the blind human-graded workflow
      (`compute_metrics.py` + `scorecard_blind.csv`) that's this project's
      own stated methodology. Filling in the blind scorecard by hand is the
      one remaining step before treating any number here as a final,
      citable result. Do this WITHOUT looking at `blind_key.json` first.
- [ ] **Rerun on a full, fresh Gemini quota.** This eval run's core-reasoning
      comparison landed on `featherless/Qwen2.5-7B-Instruct` for 53 of 60
      cases because the daily 20-request Gemini cap was exhausted early in
      an earlier same-day run - see `docs/ARCHITECTURE.md`, "Current
      auto-scored results". The workflow-design claim should hold on a
      stronger core-reasoning model too, but that isn't yet directly
      confirmed at the full 60-case scale.
- [ ] Samples/demo VIDEO, if the written `docs/SAMPLES.md` document isn't
      sufficient for the submission (the track requirements say
      video **or** document; a document is provided).
