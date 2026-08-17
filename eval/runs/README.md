# Eval runs

Each folder is one complete evaluation run: `raw_outputs.json`, the blind
scorecard, the A/B key, and the automated scorecard. The run at `eval/`
(top level) is the **canonical** one — the one every number in
`docs/ARCHITECTURE.md` and on the project site is drawn from.

| Folder | Core-reasoning model | Cases scored | Graded |
| --- | --- | --- | --- |
| `core-gemini-qwen-mixed/` | `gemini-3.6-flash` ×3, `llama-3.3-70b` ×2, `Qwen2.5-7B` ×53 | 57 | blind, by hand (56 rows) + auto |
| `core-llama-3.3-70b/` | `llama-3.3-70b-versatile` on all 50 | 50 | auto only |

Reproduce the second one with:

```bash
CORE_CHAIN="groq:llama-3.3-70b-versatile" python eval/run_eval.py
```

---

## The robustness result, and it is not the flattering one

`README.md` carried this open question: *"the workflow-design claim should
hold on a stronger core-reasoning model too, but that isn't yet directly
confirmed."* It has now been tested. **It did not hold.**

Both runs, auto-scored by the same matcher, restricted to the **44
planted-error cases that completed in both** so nothing turns on which cases
happened to fail:

| Core-reasoning model | Pipeline | Baseline | Gap |
| --- | --- | --- | --- |
| Qwen2.5-7B | 39/44 (89%) | 33/44 (75%) | **+14 pts** |
| Llama-3.3-70B | 39/44 (89%) | 40/44 (91%) | **−2 pts** |

The pipeline scored **identically** on both models. The entire change is on
the baseline's side: it went from 33 to 40 once it had a competent model
behind it.

The five cases the baseline missed on 7B and caught on 70B:

- `case_33_negation_error_penicillin_allergy`
- `case_35_negation_error_loss_of_consciousness`
- `case_50_misattribution_medication_to_wrong_person`
- `case_51_omission_anticoagulant_medication`
- `case_52_omission_abnormal_vital_sign`

Two of those are omissions — the failure mode node 5 exists specifically to
catch. A single open-ended prompt on a 70B model found them without a
dedicated omission node.

### What this actually means

The honest reading is that **decomposition compensates for a weak reasoner
rather than adding capability on top of a strong one.** On this benchmark,
at this scale, structure substituted for model quality; it did not compound
with it. And the pipeline pays roughly 5.5× the tokens and 1.7× the latency
(see "Cost and latency") to arrive at the same place.

That is a genuinely useful finding for anyone choosing between "build a
workflow" and "use a better model", and it argues the two are alternatives
here, not complements.

### What this does not mean

- **It does not invalidate the blind-graded headline result.** That result is
  real: on the model the run actually used, the pipeline caught 6 more
  planted errors than the baseline, graded by a human who did not know which
  system was which. It says decomposition is worth a great deal when your
  reasoner is weak — which is the situation any project on a free tier is
  actually in.
- **It does not say the guard is useless.** Recall is only one axis. The
  pipeline still produces per-claim verdicts with quoted evidence and a
  category, which is what makes a flag reviewable; the baseline emits an
  unstructured issue list. Node 4 is deterministic. Node 3b is the only thing
  in either system that questions the transcript. None of that is measured by
  recall on planted errors.

### Caveats on this comparison, stated plainly

1. **Auto-scored, not blind human-graded.** The proxy earned some trust — on
   the canonical run it predicted the human's 12-point gap almost exactly
   (88/76 proxy vs 94/82 human) — but it has not been validated on this run.
2. **44 of 60 cases.** Ten failed in the 70B run: nine to Groq rate limits
   (a burst limit over the first eight cases, then the 100k tokens/day cap on
   the last) and one to malformed JSON. Those are infrastructure failures,
   not difficulty-related, so the exclusions should not bias the comparison —
   but they were not randomly sampled either.
3. **False positives rose for both systems** on 70B (16 and 17 across 6
   controls, against 15 and 11 on the canonical run). The control sets differ
   slightly, so treat the direction as a signal and not the magnitude.
4. **One run per model.** No repeated sampling, no confidence intervals.

### What would settle it — and why it can't be done

Re-running the ten failed cases would give a complete 60-case 70B run, which
blind human grading could then put on the same footing as the headline
number. That was attempted (`eval/rerun_failed.py`) and **is no longer
possible: Groq withdrew both models this project depends on.**

Within hours of the run above, `llama-3.1-8b-instant` (the mechanical tier)
and then `llama-3.3-70b-versatile` (the tier the whole robustness run is
built on) both began returning `404 model_not_found`. The 70B run is
therefore frozen at 44 comparable cases permanently, unless the model
returns or the run is repeated end-to-end on a different model.

Two things came out of that, both kept:

1. **The failover chain could not absorb it.** A retired model returns 404,
   which `llm_router` classified as a caller bug worth surfacing rather than
   an availability problem worth routing around — so cases died with
   Featherless sitting unused in the same chain. Fixed narrowly: 404s that
   name the model now fail over; a 404 from a bad URL, or any auth error,
   still surfaces immediately. Without that fix the live demo
   (`python demo.py`) would also have been dead, since it shares those
   chains.
2. **`eval/rerun_failed.py` refused to produce a false result.** With the
   core tier pinned to a single model and that model gone, it declined to
   merge anything rather than silently substituting a different model into
   an existing run. That check is the reason this section says "cannot"
   instead of quietly reporting a 60-case number that was really two models
   stitched together.

The wider lesson, which is worth more than the recovered cases would have
been: **a free-tier model catalogue is not a stable substrate for a
reproducible evaluation.** Every number in this project is reproducible only
in the sense that the run is committed and the provider/model is recorded per
case. It is not re-runnable on demand, and that limitation belongs next to
the results rather than in a footnote.
