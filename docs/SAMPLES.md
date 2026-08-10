# Samples: Pipeline vs. Single-Prompt Baseline

Real output from `eval/raw_outputs.json` - the actual committed eval run (see `docs/ARCHITECTURE.md`, "Current auto-scored results", for the full 60-case numbers this document is drawn from; provider/model used for each case is recorded per-case below). Nothing here is paraphrased or hand-typed from a screenshot; this document is generated directly from that JSON by `docs/generate_samples_doc.py`, so re-running the eval and regenerating this file keeps it accurate.

**Case selection is deliberately not all wins for the pipeline** - see the rationale under each case heading. The goal is to show what actually happened, including the one case picked specifically because the pipeline over-flags relative to the baseline there.

Every case here is a text transcript, treated as ground truth. For what happens when the transcript itself is wrong - a live `--audio` run where the recogniser hallucinated an entire encounter and node 3b was the only thing that caught it - see [SAMPLES_AUDIO.md](SAMPLES_AUDIO.md). That run is not generated from `raw_outputs.json`, so it is kept in its own file rather than being overwritten every time this script runs.

---

## `case_01_numeric_medication_error`

**Why this case is included:** Catches the highest-severity category (numeric/medication error) twice over - by the deterministic regex check AND independently flagged by the LLM entailment step.

**Specialty:** Primary care - hypertension follow-up

<details><summary>Transcript</summary>

```
Doctor: Hi Mr. Alvarez, good to see you. How have you been feeling since we adjusted your blood pressure medication?
Patient: Pretty good, actually. No headaches or dizziness like before.
Doctor: That's great. Are you still taking the lisinopril 10 milligrams once a day?
Patient: Yes, every morning with breakfast.
Doctor: Any side effects, cough, swelling in your legs?
Patient: No, nothing like that.
Doctor: Let's check your blood pressure today... okay, it's reading 128 over 82. That's a nice improvement from last visit.
Patient: That's good to hear.
Doctor: I want you to keep taking the lisinopril at the same dose and come back in three months for a recheck.
Patient: Sounds good, thank you.
```

</details>

<details><summary>Note under test</summary>

```
Subjective: Patient reports feeling well since blood pressure medication adjustment. Denies headaches, dizziness, cough, or leg swelling. Taking lisinopril 20mg once daily each morning with breakfast.
Objective: Blood pressure 128/82, improved from previous visit.
Assessment: Hypertension, well-controlled on current regimen.
Plan: Continue lisinopril at current dose. Return to clinic in 3 months for recheck.
```

</details>

**Ground truth:** planted `numeric_medication_error` error

- Claim in the note: "Taking lisinopril 20mg once daily"
- Correct value: "lisinopril 10mg once daily"
- Transcript evidence: "Patient confirmed 'lisinopril 10 milligrams once a day'"

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `gemini/gemini-3.6-flash`

### Pipeline output

- **[numeric_medication_error]** Lisinopril dose is 20mg
  - explanation: The note states a Lisinopril dose of 20mg, but the transcript indicates a dose of 10mg.
  - evidence: "lisinopril 10 milligrams once a day"
  - source node: `llm_pipeline`
- **[numeric_medication_error]** 20mg
  - evidence: "This number/dose appears in the note but was not found anywhere in the transcript."
  - source node: `deterministic_check`
- **[omission]** Patient is taking lisinopril 10 milligrams once a day
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`

### Baseline output (single prompt, same transcript + note)

- lisinopril 20mg once daily
  - The note states the dosage of lisinopril is 20mg, but the transcript states it is 10 milligrams.

---

## `case_02_fabrication`

**Why this case is included:** A fabricated symptom the note claims was reported, that the transcript explicitly denies - the classic hallucination case this project exists to catch.

**Specialty:** Primary care - upper respiratory infection

<details><summary>Transcript</summary>

```
Doctor: What brings you in today?
Patient: I've had this cough for about five days now, kind of a dry cough. No fever that I've noticed.
Doctor: Any shortness of breath, chest pain, or sore throat?
Patient: A little bit of a sore throat, but no chest pain or trouble breathing.
Doctor: Any nausea, vomiting, or stomach issues?
Patient: No, none of that.
Doctor: Okay, let me listen to your lungs... they sound clear. Your throat looks a little red but no white patches. I think this is a viral upper respiratory infection.
Patient: Okay, so nothing serious?
Doctor: No, should resolve on its own. Drink plenty of fluids, rest, and use over-the-counter cough drops as needed. Come back if it gets worse or lasts more than two weeks.
Patient: Will do, thank you.
```

</details>

<details><summary>Note under test</summary>

```
Subjective: Patient reports a dry cough for 5 days, accompanied by fever and mild nausea. Also endorses mild sore throat. Denies chest pain or shortness of breath.
Objective: Lungs clear to auscultation bilaterally. Oropharynx mildly erythematous, no exudate.
Assessment: Viral upper respiratory infection.
Plan: Supportive care - fluids, rest, OTC cough drops as needed. Return if symptoms worsen or persist beyond 2 weeks.
```

</details>

**Ground truth:** planted `fabrication` error

- Claim in the note: "accompanied by fever and mild nausea"
- Correct value: "not mentioned; patient explicitly denied fever and denied nausea/vomiting"
- Transcript evidence: "Patient said 'No fever that I've noticed' and, on nausea/vomiting, 'No, none of that.'"

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `gemini/gemini-3.6-flash`

### Pipeline output

- **[negation_error]** Patient reports fever
  - explanation: A denial is flipped into an affirmation, or vice versa.
  - evidence: "No fever that I've noticed."
  - source node: `llm_pipeline`
- **[distortion]** Patient reports mild nausea
  - explanation: A detail that IS present in the transcript but has been altered in the note — e.g. the right symptom with the wrong severity, duration, or qualifier.
  - evidence: "No, none of that."
  - source node: `llm_pipeline`
- **[omission]** No fever
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** No nausea
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** No vomiting
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** No stomach issues
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`

### Baseline output (single prompt, same transcript + note)

- accompanied by fever and mild nausea
  - The patient explicitly denied having a fever ("No fever that I've noticed") and denied nausea ("No, none of that").

---

## `case_16_omission_drug_allergy`

**Why this case is included:** A safety-critical case the pipeline's Node 5 (omission check) exists specifically to catch, and that node 3's note-to-transcript direction structurally cannot: a documented drug allergy that never made it into the note at all.

**Specialty:** Primary care - new patient visit

<details><summary>Transcript</summary>

```
Doctor: Since this is your first visit with us, let's go over your history. Any allergies to medications?
Patient: Yes, I'm allergic to sulfa drugs. I broke out in hives the last time I took one, years ago.
Doctor: Good to know, we'll flag that in your chart. Any other allergies - food, environmental?
Patient: No, just the sulfa.
Doctor: Understood. Any current medications?
Patient: Just a daily multivitamin.
Doctor: Great, and what brings you in today?
Patient: Just establishing care, and I wanted a general checkup.
Doctor: Sounds good, let's do a quick exam and get some baseline labs ordered.
```

</details>

<details><summary>Note under test</summary>

```
Subjective: New patient establishing care, requesting general checkup. Reports taking a daily multivitamin, no other current medications.
Objective: Exam findings pending.
Assessment: New patient visit, no acute concerns.
Plan: Baseline labs ordered.
```

</details>

**Ground truth:** planted `omission` error

- Claim in the note: "known sulfa drug allergy (hives on prior exposure)"
- Correct value: "the note should document the sulfa allergy in the allergy section, since it is safety-critical for future prescribing"
- Transcript evidence: "Patient said 'I'm allergic to sulfa drugs. I broke out in hives the last time I took one'"

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `featherless/Qwen/Qwen2.5-7B-Instruct`

### Pipeline output

- **[omission]** Exam findings are pending
  - explanation: The claim states that exam findings are pending, but there is no mention of this in the transcript.
  - source node: `llm_pipeline`
- **[negation_error]** No acute concerns are present
  - explanation: The claim states that no acute concerns are present, but this is the opposite of what is stated in the transcript (i.e., acute concerns are present).
  - source node: `llm_pipeline`
- **[omission]** Patient is allergic to sulfa drugs
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** Patient broke out in hives after taking sulfa drugs
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** A quick exam will be performed
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`

### Baseline output (single prompt, same transcript + note)

_(no issues found)_

---

## `case_18_clean_control_annual_physical`

**Why this case is included:** Reported for balance, not just wins: a clean note where the pipeline over-flags more than the baseline does. This is the real, documented precision trade-off from ARCHITECTURE.md's 'Known limitations' section, shown with actual output rather than just described in prose.

**Specialty:** Primary care - annual physical, no complaints

<details><summary>Transcript</summary>

```
Doctor: How have you been feeling overall this year?
Patient: Really good, no complaints. No chest pain, no shortness of breath, sleeping well, eating well.
Doctor: Any changes in weight, appetite, or energy levels?
Patient: No, everything's been pretty stable.
Doctor: Great. Let's do a quick exam... heart and lungs sound normal, abdomen is soft and non-tender, everything looks good.
Patient: Glad to hear it.
Doctor: I'll order your routine annual labs - cholesterol panel and basic metabolic panel. Keep up with the exercise and diet, and I'll see you again next year unless something comes up sooner.
Patient: Will do, thank you.
```

</details>

<details><summary>Note under test</summary>

```
Subjective: Patient reports feeling well overall, no complaints. Denies chest pain, shortness of breath, or changes in weight, appetite, sleep, or energy.
Objective: Heart and lungs normal on auscultation. Abdomen soft, non-tender.
Assessment: Routine annual physical, no acute concerns.
Plan: Routine annual labs ordered (lipid panel, basic metabolic panel). Continue current diet and exercise. Follow up in 1 year or sooner if needed.
```

</details>

**Ground truth:** clean control - no planted error

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `featherless/Qwen/Qwen2.5-7B-Instruct`

### Pipeline output

- **[negation_error]** Patient denies changes in weight
  - explanation: The patient denies changes in weight, but this is not mentioned in the transcript.
  - source node: `llm_pipeline`
- **[negation_error]** Patient denies changes in appetite
  - explanation: The patient denies changes in appetite, but this is not mentioned in the transcript.
  - source node: `llm_pipeline`
- **[negation_error]** Patient denies changes in sleep
  - explanation: The patient denies changes in sleep, but this is not mentioned in the transcript.
  - source node: `llm_pipeline`
- **[negation_error]** Patient denies changes in energy
  - explanation: The patient denies changes in energy, but this is not mentioned in the transcript.
  - source node: `llm_pipeline`
- **[omission]** Routine annual labs ordered (lipid panel)
  - explanation: Routine annual labs ordered (lipid panel) is a clinically relevant detail that was stated in the transcript but is entirely missing from the note.
  - source node: `llm_pipeline`
- **[omission]** Sleeping well
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** Eating well
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`

### Baseline output (single prompt, same transcript + note)

- Patient reports feeling well overall, no complaints. Denies chest pain, shortness of breath, or changes in weight, appetite, sleep, or energy.
  - The transcript mentions that the patient has been sleeping well and eating well, which are not included in the note.
- Plan: Routine annual labs ordered (lipid panel, basic metabolic panel).
  - The transcript mentions ordering a 'cholesterol panel' and 'basic metabolic panel', but the note only lists 'lipid panel'.

---

## Observations (read against the actual output above, not asserted separately)

- **`case_01`: the deterministic and LLM checks catch the same error two different ways, plus the omission node adds a third, independent signal.** Node 4's regex flags the bare `20mg` token with zero ambiguity; node 3's entailment flags the same dose in context ("Lisinopril dose is 20mg"); node 5's omission check separately notices the transcript's correct `10 milligrams` never made it into the note at all. Three nodes converging on one real error is what "decompose then verify from multiple angles" is supposed to produce - the baseline gets the same catch with its one call, but with no structural reason it had to.

- **`case_02`: the pipeline decomposes what the baseline reports as one issue into several separately-judged claims.** The baseline's single call correctly flags the fabricated fever and nausea together, in one sentence. The pipeline's node 3 catches the same two fabrications as `negation_error`/`distortion` flags, and node 5 separately (and somewhat redundantly) flags the transcript's four individual denials ("No fever", "No nausea", "No vomiting", "No stomach issues") as omissions from the note - even though the note's fabricated line covers that same ground in spirit, just incorrectly. This is a real instance of the documented precision cost of decomposition (see `docs/ARCHITECTURE.md`, "Known limitations"): the same real error surfaces as multiple flags instead of one.

- **`case_16`: the clearest pipeline-vs-baseline gap in this sample set.** The baseline's single holistic read produced zero issues on a note that is missing a documented, safety-critical drug allergy (sulfa, with a prior hives reaction) entirely. It is not that the baseline model "disagreed" - a whole-note free-form review, with no structural requirement to check every transcript fact against the note, simply has no mechanism that would surface an omission like this. That structural gap is exactly what node 5 exists to close.

- **`case_18`: the honest cost of that same decomposition, on a genuinely clean note.** Breaking a note into many atomic claims/facts (7 checkable items here) creates 7 independent chances for a false positive instead of 1. Here the pipeline raises 7 flags - 4 of them ("denies changes in weight, appetite, sleep, or energy" atomized into four separate negation claims) arguably shouldn't be flags at all, since the note's single summarizing sentence does cover all four. The baseline's single-pass read raises 2 flags instead of 0 on this same clean note - fewer false alarms than the pipeline, but not zero either. Neither system is precision-perfect on this note; the pipeline is further from it. See `docs/ARCHITECTURE.md`, "Known limitations", for the full discussion.
