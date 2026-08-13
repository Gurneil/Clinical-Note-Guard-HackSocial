# Sample: what node 3b does when the transcript itself is wrong

Companion to `SAMPLES.md`. That document is generated from the committed
text-only eval run; this one is a live `--audio` run, captured verbatim,
because there is no committed audio eval to generate it from.

Everything below is one synthetic encounter (`case_01`, hypertension
follow-up) spoken by two Windows TTS voices - `data/audio/case_01_synthetic.wav`.
No real patient, no real clinician, no real audio anywhere.

Reproduce with:

```
python demo.py --audio data/audio/case_01_synthetic.wav
```

---

## Run 1: clean audio

Whisper heard it essentially correctly:

```
Hi Mr. Alvarez, good to see you. How have you been feeling since we adjusted
your blood pressure medication? Pretty good, actually. No headaches or
dizziness like before. That's great. Are you still taking the Lysinopril
10 mg once a day? ...
```

Mean confidence **0.85**, no segment below the floor, **zero unverifiable
flags**. Node 3b is silent, and the pipeline behaves exactly as it does on
a hand-written transcript.

One detail worth noticing even here: **"Lysinopril"**. Whisper misspelled
the drug name on clean, synthetic, unaccented speech. It did not affect the
dose, and node 3 still matched the claim - but drug names are the category
where recognisers are weakest, and this is what that looks like when
nothing else is going wrong.

---

## Run 2: the same encounter, degraded

The same audio with the speech attenuated to 25% and uniform hiss added -
roughly a bad speakerphone in a noisy room. Whisper did not fail loudly. It
returned this:

```
Hi, this is Alpera. I'm here for the studio. I'll let you back see my
station. This is your best destination. This is your best place. I think
I've got a big one. Okay. That's good. Are you still taking a little bit of
a 10-year-old? ... It's leading 178.83. It's a nice and beautiful from last
week. ... come back in a few months
```

Fluent. Grammatical. Entirely invented. There is no patient named Alpera,
no value of 178.83, and nobody said anything about a studio.

**Mean confidence 0.329. All 28 segments below the floor.**

### What the scribe then produced

Node 1 drafted a perfectly presentable clinical note from that fiction:

```
**Subjective**
* **Patient Name:** Alpera
* **Chief Complaint / History:** Patient states, "I think I've got a big one."
* **Medications:** Patient reports not taking a previously referenced medication.
* **Side Effects:** Denies any side effects.

**Objective**
* **Measurements/Vitals:** Value recorded at 178.83 (noted as an improvement from last week).

**Assessment**
* Patient's reading (178.83) shows positive progress compared to the previous week.

**Plan**
* **Activity:** Encouraged to move a little bit.
* **Follow-up:** Return for a follow-up visit in a few months.
```

### What nodes 2-6 concluded

Node 2 extracted 8 atomic claims. Node 3 checked every one against the
transcript and marked **all 8 supported** - and it was right to. Each claim
genuinely is entailed by the transcript it was given. The note faithfully
represents a conversation that never happened.

**This is the failure the rest of the pipeline cannot see.** Every node
before 3b measures the note against the transcript. When the transcript is
the thing that's wrong, a perfect score is exactly what a correct
implementation produces. Without node 3b, this run's headline output is
"8 claims checked, all supported" - a hallucinated encounter, certified
accurate, ready to sign.

### What node 3b concluded

```
UNVERIFIABLE - checked against unreliable audio

  claim:      Patient's name is Alpera
  node 3 said: supported  ->  now: unverifiable
  audio:      00:00-00:01 (confidence 0.3119)
  action:     Re-listen to 00:00-00:01 before signing.

  claim:      Patient's chief complaint is 'I think I've got a big one'
  node 3 said: supported  ->  now: unverifiable
  audio:      00:10-00:12 (confidence 0.3119)
  action:     Re-listen to 00:10-00:12 before signing.

  claim:      Patient denies taking a 10-year-old medication/treatment
  node 3 said: supported  ->  now: unverifiable
  audio:      00:19-00:20 (confidence 0.3119)
  action:     Re-listen to 00:19-00:20 before signing.

  claim:      Value noted at 178.83
  node 3 said: supported  ->  now: unverifiable
  audio:      00:32-00:35 (confidence 0.3593)
  action:     Re-listen to 00:32-00:35 before signing.

  ... 8 of 8 claims, every one downgraded
```

Every single "supported" verdict was withdrawn, each with the seconds of
audio a human should go and listen to.

---

## What this sample is and isn't evidence of

**It is** a demonstration that the mechanism does the thing it was built to
do, on real recogniser output, end to end, including the case that matters
most: a confident pass over an invented source.

**It is not** a measurement of how often this happens in practice. It is one
recording, degraded artificially, on one recogniser. The threshold that
made it fire was calibrated on this same recording
(`eval/asr_confidence_check.py`), which is a legitimate way to place a
threshold and not a legitimate way to claim generalisation.

**It also flatters the mechanism by construction.** The degradation was
severe enough that *everything* dropped below the floor, so node 3b had an
easy job. The genuinely hard case - clear audio for 49 seconds and one
mumbled dose - is the one that would test whether ~30-second-window
confidence is granular enough to isolate a single wrong number. On this
evidence, it probably is not. See `ARCHITECTURE.md`, "What this does not
solve".
