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
├── taxonomy.json          # error categories, grounded in the literature
├── .env.example            # API key variable names (copy to .env, fill in, never commit)
├── smoke_test.py            # verifies every provider + the failover router, no eval cost
├── data/
│   └── test_cases.json    # synthetic benchmark: transcripts + notes +
│                           # ground truth for planted errors (18 cases)
├── src/
│   ├── _env.py                   # loads .env once, imported by the three files below
│   ├── config.py                 # provider/model failover chains, and why
│   ├── llm_router.py             # dispatch + automatic failover + fairness-linking
│   ├── gemini_client.py          # Gemini API wrapper
│   ├── openai_compat_client.py   # shared Groq + Featherless wrapper (both OpenAI-compatible)
│   ├── pipeline.py               # the guard pipeline, nodes 0-7 (commission + omission + human checkpoint)
│   └── baseline.py               # single-prompt comparison baseline
├── tests/                   # stdlib unittest, no real API calls, run before every change
│   ├── test_deterministic_check.py
│   ├── test_llm_router.py
│   ├── test_omission_check.py
│   ├── test_openai_compat_client.py
│   └── test_auto_score.py
├── eval/
│   ├── run_eval.py         # runs both systems, writes a BLINDED scorecard
│   ├── compute_metrics.py  # scores the filled-in blind scorecard by hand
│   ├── auto_score.py       # automated (non-blind) scoring proxy - see ARCHITECTURE.md
│   ├── raw_outputs.json    # committed: full output from the actual eval run reported in the docs
│   ├── scorecard_blind.csv # committed: blinded grading sheet from that same run
│   ├── blind_key.json      # committed: A/B -> pipeline/baseline key for that run
│   └── auto_scorecard.json # committed: per-case auto_score.py detail for that run
└── docs/
    ├── ARCHITECTURE.md            # reasoning behind every node + reported results (submission doc)
    ├── SAMPLES.md                 # pipeline vs. baseline on real cases (submission doc)
    ├── workflow_flowchart.png     # the required workflow diagram (submission asset)
    ├── generate_flowchart.py      # regenerates workflow_flowchart.png (dev tool, needs matplotlib)
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

## Current status / what's left before submission

- [x] Taxonomy defined (grounded in ambient-scribe literature)
- [x] Pipeline built: 6 automated nodes (extraction, entailment, deterministic
      numeric check, omission check, classification, plus draft for the live
      demo) + a required human review checkpoint
- [x] Benchmark: 18 cases - 3 numeric_medication_error, 3 fabrication, 3
      negation_error, 2 distortion, 2 misattribution, 2 omission, 3 clean
      controls
- [x] Full eval run against all 18 cases, committed (`eval/raw_outputs.json`
      and friends) - see `docs/ARCHITECTURE.md`, "Current auto-scored results"
- [x] Required workflow flowchart (`docs/workflow_flowchart.png`)
- [x] Required documentation (`docs/ARCHITECTURE.md`) - taxonomy, per-node
      reasoning, failover engineering, reproducibility fixes, real results,
      known limitations, all as they actually happened rather than planned
- [x] Required samples document (`docs/SAMPLES.md`) - pipeline vs. baseline
      on 4 real cases, generated directly from the committed eval output
- [ ] **Blind human grading pass.** The numbers currently in `docs/` come
      from `eval/auto_score.py`, an automated proxy explicitly labeled as
      such everywhere it's cited - not the blind human-graded workflow
      (`compute_metrics.py` + `scorecard_blind.csv`) that's this project's
      own stated methodology. Filling in the blind scorecard by hand is the
      one remaining step before treating any number here as a final,
      citable result. Do this WITHOUT looking at `blind_key.json` first.
- [ ] Samples/demo VIDEO, if the written `docs/SAMPLES.md` document isn't
      sufficient for the submission (the track requirements say
      video **or** document; a document is provided).
