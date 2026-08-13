# Demo video — script

Target **4 minutes**. The 2025 organisers asked for a video covering what the
project does, the inspiration, and how it maps to each rubric category
(Innovation, Problem Solving, Sustainability/Scalability, User Experience &
Design). This script hits all four without ever announcing "and now, user
experience" — the mapping should be visible to a judge with the rubric open,
not narrated.

Record at **1920×1080**. Two sources: your browser on
`https://clinicalnoteguard.netlify.app`, and a terminal in
`D:\clinical-note-guard`. Do a dry run of the terminal section first — the
live pipeline takes ~13 seconds per note and you don't want to discover a
rate limit on camera.

Watch the 2026 opening-ceremony recording for this year's rubric before
recording; the categories above are from 2025 and may have shifted.

---

## 0:00–0:30 — The problem, on screen

**Screen:** the live site's home page, scrolled to the top.

> AI scribes now draft clinical notes from doctor–patient conversations, and
> they're deployed in real clinics today. They also make things up: a wrong
> dose, a symptom nobody mentioned, a "denies" flipped to a "reports".
>
> Everyone agrees a human has to review these before signing. The problem is
> that reviewing a page of fluent prose and hoping to spot the one wrong
> sentence is slow and unreliable — because the wrong sentence reads exactly
> like the right ones.

---

## 0:30–1:20 — What it does, shown not told

**Screen:** press **Run the demo**. Let the console open on `case_01`.

> This is the guard running on a real benchmark case. It took the drafted
> note apart into fourteen individually checkable claims and verified each
> one against the transcript.
>
> Thirteen check out. One doesn't.

**Screen:** click **Flags**, then read one flag aloud.

> The note says the patient is on lisinopril 20mg. The transcript says ten.
> The flag carries the evidence — the actual words from the conversation —
> and a category, so a reviewer can settle it in seconds instead of
> re-reading the whole note.
>
> And it never fixes anything. Every flag goes to a person: confirm, or
> dismiss. That's node 7, and it's required, not optional.

**Screen:** click **Confirm** on one flag so the counter moves.

---

## 1:20–2:00 — The workflow (the track's actual subject)

**Screen:** navigate to **About → AI flowchart**. Let the timeline play, then
click node 5.

> Nine nodes. Two of them never call a model at all — the numeric check is a
> regex, because a dose either matches the transcript or it doesn't, and node
> 3b is plain Python.
>
> Node 5 is the one I'd point at. Nodes 2 and 3 walk the *note* against the
> transcript, which structurally cannot notice something the note left out.
> So node 5 runs the same pass in reverse: facts out of the transcript,
> checked against the note.

---

## 2:00–2:40 — It actually runs

**Screen:** terminal, full screen.

```
python demo.py 3 --no-review
```

> This is the live pipeline, not a replay — drafting a note, decomposing it,
> checking each claim, and stopping at the human checkpoint.

Let it run. Don't talk over the whole thing; let a few seconds of real output
breathe. Cut the dead time in the edit if it drags.

---

## 2:40–3:30 — The evidence, including the part that went against us

**Screen:** the site's **Evidence** page. Scroll to the results table.

> Sixty synthetic cases, each with one planted error, plus clean controls to
> measure false alarms. Graded blind by a human who couldn't tell which
> system was which: the pipeline caught 47 of 50, the single-prompt baseline
> 41.

**Screen:** scroll to the stronger-model section.

> Then I tested that claim on a model ten times the size — and it stopped
> holding. The pipeline scored exactly the same. The baseline caught up.
>
> The honest reading is that decomposition compensates for a weak reasoner
> rather than adding capability on top of a strong one. That narrows what I
> can claim. I'm showing it because it's the result, and because a QA tool
> that hides its own bad measurement has no business asking anyone to trust
> it.

*This is the most important thirty seconds in the video. Don't rush it and
don't apologise for it.*

---

## 3:30–4:00 — Cost, and close

**Screen:** **Evidence → Cost & caveats**.

> All of it measured, not estimated: 5.5× the tokens and 1.7× the latency of
> a single prompt, on free-tier APIs, zero spend.
>
> Every transcript and every recording in this project is synthetic —
> invented conversations about fictional patients. No real patient data
> anywhere, and it never diagnoses anything. It's a documentation check that
> keeps a human in the loop, and tells you honestly how well it works.

**Screen:** end on the home page or the flowchart.

---

## Checklist before uploading

- [ ] Under 6 minutes
- [ ] Says the track name ("ML Prompt Engineering") somewhere, or shows it
- [ ] Audio is audible — test 10 seconds and play it back before the full take
- [ ] The stronger-model finding is in it
- [ ] Uploaded unlisted-or-public on YouTube/Drive, and the link **actually
      opens in a private browser window** (staff have had submissions score
      zero for unshared links)
