# Clinical Note Hallucination Guard — what it is

*The "contextualise your product" section the staff asked for on Aug 10. One
page; turn it into a slide if you're submitting a deck.*

**Track:** ML Prompt Engineering

---

## The problem

AI "ambient scribes" — tools that listen to a doctor–patient conversation and
draft the clinical note — are one of the most widely deployed categories of
healthcare AI right now. They produce fluent, confident notes that sometimes
contain things nobody said: a wrong dose, a symptom never mentioned, a denial
flipped into a confirmation.

Every clinical body agrees a human must review these notes before signing.
The unsolved part is *how*. Reviewing a page of fluent prose and hoping to
notice the one wrong sentence is slow and unreliable — because the wrong
sentence reads exactly like the right ones.

## Who it's for

The clinician or scribe who has to sign the note, and the health system
responsible for what's in it. Not patients, and not as a replacement for
anyone's judgment.

## What it does

It decomposes the drafted note into individually checkable claims, verifies
each one against the source transcript independently, and surfaces anything
unsupported — with the evidence — to a human, before the note is signed.

Nine nodes: draft, extract claims, entailment check, transcript-confidence
check, deterministic numeric check, omission check, classification, and a
required human review checkpoint. Four of the nine never call a model —
two are plain Python, one is the input, one is the person.

**It never corrects anything.** Every flag is a candidate for a human
decision, never a decision.

## What makes it different from "ask a model to find errors"

That single-prompt approach is the baseline this project measures itself
against, on the identical 60-case benchmark with the identical model. The
pipeline catches 45 of 51 planted errors against the baseline's 39, and the
error it finds is the *first flag a reviewer reads* in 35 of those cases.

It also costs 5.5× the tokens, and raises more false alarms on clean notes.
Both of those are published on the site rather than buried.

## What it is not

- It does not diagnose patients or recommend treatment.
- Every transcript, note and audio file is synthetic — invented conversations
  about fictional patients. No real patient data is used or needed anywhere.
- The headline numbers are currently auto-scored; the blind human-graded pass
  is in progress and the site says so.

## Try it

**https://clinicalnoteguard.netlify.app**

- **The site** — the hero embeds a working review console over the real
  committed evaluation: all 60 cases, real verdicts, real flags. Nothing in
  it is simulated in the browser.
- **The CLI** — `python demo.py` runs the whole pipeline end to end on a
  benchmark case, including the interactive human review.
