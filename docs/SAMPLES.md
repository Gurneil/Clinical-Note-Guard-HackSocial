# Samples: Pipeline vs. Single-Prompt Baseline

Real output from `eval/raw_outputs.json` - the actual committed eval run (see `docs/ARCHITECTURE.md`, "Current auto-scored results", for the full 18-case numbers this document is drawn from; provider/model used for each case is recorded per-case below). Nothing here is paraphrased or hand-typed from a screenshot; this document is generated directly from that JSON by `docs/generate_samples_doc.py`, so re-running the eval and regenerating this file keeps it accurate.

**Case selection is deliberately not all wins for the pipeline** - see the rationale under each case heading. The goal is to show what actually happened, including the one case picked specifically because the pipeline over-flags relative to the baseline there.

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

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `featherless/Qwen/Qwen2.5-7B-Instruct`

### Pipeline output

- **[numeric_medication_error]** Lisinopril dose is 20mg
  - explanation: The note states a specific dose of Lisinopril that is not mentioned in the transcript.
  - source node: `llm_pipeline`
- **[numeric_medication_error]** 20mg
  - evidence: "This number/dose appears in the note but was not found anywhere in the transcript."
  - source node: `deterministic_check`
- **[omission]** Patient is taking lisinopril 10 milligrams once a day
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`

### Baseline output (single prompt, same transcript + note)

- Denies headaches, dizziness, or leg swelling.
  - The patient mentioned he had no headaches or dizziness but did not specifically deny leg swelling.
- Taking lisinopril 20mg once daily each morning with breakfast.
  - The patient is actually taking lisinopril 10mg once daily, not 20mg.

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

**Provider/model this case actually ran on** (both systems, fairness-linked - see `llm_router.py`): `featherless/Qwen/Qwen2.5-7B-Instruct`

### Pipeline output

- **[omission]** Patient reports fever
  - explanation: The claim is not mentioned in the transcript, indicating a missing detail.
  - source node: `llm_pipeline`
- **[omission]** Patient reports mild nausea
  - explanation: The claim is not mentioned in the transcript, indicating a missing detail.
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

- Patient reports a dry cough for 5 days, accompanied by fever and mild nausea.
  - The patient did not mention having a fever or nausea in the transcript.
- Denies chest pain or shortness of breath.
  - The patient mentioned having a little bit of a sore throat but denied chest pain or shortness of breath in the transcript.

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

- **[negation_error]** No acute concerns are present
  - explanation: The claim is a denial that is flipped into an affirmation.
  - source node: `llm_pipeline`
- **[omission]** Patient is allergic to sulfa drugs
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** Patient broke out in hives after taking sulfa drugs
  - explanation: This fact was stated in the transcript but does not appear anywhere in the note.
  - source node: `llm_pipeline_omission`
- **[omission]** Patient has no other allergies
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

_(no issues found)_

---

## Observations (read against the actual output above, not asserted separately)

- **`case_02`: a real categorization slip, not a detection miss.** The two fabricated-symptom claims (fever, nausea) were correctly flagged by node 3 (entailment) - but `classify_errors_batch` (node 6) labeled them `omission` instead of `fabrication`. The error was still caught and would still reach a human reviewer; the taxonomy label attached to it was wrong. Worth fixing before treating per-category precision as reliable, and left visible here rather than cleaned up for the writeup.

- **`case_16`: the clearest pipeline-vs-baseline gap in this sample set.** The baseline's single holistic read produced zero issues on a note that is missing a documented, safety-critical drug allergy entirely. It is not that the baseline model "disagreed" - a whole-note free-form review, with no structural requirement to check every transcript fact against the note, simply has no mechanism that would surface an omission like this. That structural gap is exactly what node 5 exists to close.

- **`case_18`: the honest cost of that same decomposition.** Breaking a note into many atomic claims/facts (7 checkable items here) creates 7 independent chances for a false positive instead of 1. The baseline's conservative, non-decomposed read caught nothing wrong here (correctly - it's a clean note) partly because it never atomizes "denies changes in weight, appetite, sleep, or energy" into four separately-judged claims the way the pipeline does. See `docs/ARCHITECTURE.md`, "Known limitations", for the full discussion.
