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
├── data/
│   └── test_cases.json    # synthetic benchmark: transcripts + notes +
│                           # ground truth for planted errors
├── src/
│   ├── config.py               # provider/model failover chains, and why
│   ├── llm_router.py            # dispatch + automatic failover + fairness-linking
│   ├── gemini_client.py         # Gemini API wrapper
│   ├── openai_compat_client.py  # shared Groq + Featherless wrapper (both OpenAI-compatible)
│   ├── pipeline.py              # the 6-node guard pipeline
│   └── baseline.py              # single-prompt comparison baseline
├── eval/
│   ├── run_eval.py         # runs both systems, writes a BLINDED scorecard
│   └── compute_metrics.py  # scores the filled-in scorecard
└── docs/
    └── ARCHITECTURE.md     # reasoning behind every node (submission doc)
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
5. Set whichever keys you have as environment variables - never hardcode
   a key in any file:
   ```
   export GEMINI_API_KEY="your-key-here"
   export GROQ_API_KEY="your-key-here"             # optional
   export FEATHERLESS_AI_API_KEY="your-key-here"   # optional
   ```
   Windows PowerShell: `$env:GEMINI_API_KEY="your-key-here"` (same for the others)
   Windows Command Prompt: `set GEMINI_API_KEY=your-key-here` (same for the others)

   (`FEATHERLESS_API_KEY` is also accepted as an alias for
   `FEATHERLESS_AI_API_KEY` — both names work.)

**Verify your keys actually work before running the eval:**
```
D:\Python312\python.exe smoke_test.py
```
One minimal call per provider (so confirming Gemini costs 1 of its 5
requests/minute), plus a test of the failover router itself. Providers
with no key set are reported as SKIPPED — never silently omitted.

   Note: if `python` isn't recognized on PATH (common when Python is
   installed somewhere like `D:\Python312`), use the full path to your
   interpreter for every command below, e.g.
   `D:\Python312\python.exe -m pip install -r requirements.txt`.

   Only Gemini is required to run anything at all. Groq/Featherless are
   optional - if their keys aren't set, they're automatically skipped,
   not an error (see src/llm_router.py).

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

**After grading the scorecard:**
```bash
python compute_metrics.py
```
This prints recall, severity-weighted recall, and false-positive counts
for both systems side by side.

## Current status / what's left before submission

- [x] Taxonomy defined (grounded in ambient-scribe literature)
- [x] Pipeline built (5 automated nodes + human checkpoint)
- [x] Starter benchmark: 6 cases (5 planted errors across 5 categories + 1 clean control)
- [ ] Expand benchmark to ~15-20 cases (2-3 per category + several controls)
- [ ] Run full eval, fill in blind scorecard, compute final metrics
- [ ] Build the required workflow flowchart PNG
- [ ] Write the required documentation (docs/ARCHITECTURE.md is the seed for this)
- [ ] Record the samples/demo video comparing pipeline vs. baseline
