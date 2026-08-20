# YouTube upload — description and settings

## Setting: Unlisted

Pick **Unlisted**. Anyone with the link can watch, it works embedded on
Devpost, and it stays off your channel page and out of search — so a first
hackathon video isn't the top result for your name forever.

**Do NOT pick Private.** Private means only Google accounts you individually
invite can watch, which would leave judges staring at an error page. That is
the one setting that silently fails a submission.

Public is also fine if you want it discoverable. Unlisted is the safer
default and gives judges identical access.

After uploading, **open the link in a private/incognito window** and confirm
it plays. Staff have scored submissions zero for links that turned out not to
be shareable.

---

## Description — paste this

```
Clinical Note Hallucination Guard — a QA layer that catches AI hallucinations in clinical notes before a clinician signs off.

Built for ReverieHacks 2026 · ML Prompt Engineering track

AI scribes already draft clinical notes from doctor-patient conversations in real clinics. They also fabricate: a wrong dose, a symptom nobody mentioned, a "denies" flipped to a "reports". This decomposes the drafted note into individually checkable claims, verifies each one against the source transcript, and flags anything unsupported for a human — before the note is signed. It never edits a note itself.

Try it: https://clinicalnoteguard.netlify.app

CHAPTERS
0:00 What this is
0:20 The problem
0:50 Catching a real error
1:40 How the pipeline works
2:20 Running it live
3:00 The evidence — including the result that went against us
3:50 Cost, and what this isn't

Graded blind by a human who couldn't tell which system was which, the pipeline caught 47 of 50 planted errors against a single prompt's 41. Then the same claim was tested on a model ten times larger and stopped holding — decomposition compensates for a weak reasoner rather than adding capability on top of a strong one. That result is published rather than buried, because a tool built to catch other people's mistakes shouldn't hide its own.

Every transcript, note and recording in this project is synthetic — invented conversations about fictional patients. No real patient data is used anywhere. It does not diagnose patients or recommend treatment.
```

---

## Two things to fix before you paste

1. **The timestamps are from the script, not your edit.** Scrub your finished
   video and correct each one. YouTube turns them into clickable chapters
   only if the first is `0:00` and there are at least three, each at least
   10 seconds apart. Judges use them to jump straight to the evidence — worth
   the two minutes.

2. **Add the repo link once you've pushed** — `github.com/Gurneil/Clinical-Note-Guard`
   is still 404. Put it under the "Try it" line as:
   `Code: https://github.com/Gurneil/Clinical-Note-Guard`
   A dead link in the description is worse than no link.
