# Demo video — script

Target **about 4½ minutes**.

**How to read this:** lines in `[ ]` are what you do on screen. Everything else
is what you say. Each line is one breath — pause at the line break. Don't try
to say two lines as one sentence; the short lines are what stops it sounding
read.

Say it in your own words if a line feels wrong in your mouth. The meaning
matters, the wording doesn't.

Record at **1920×1080**, in six separate clips — one per section. Stitch them
after.

---

## Intro · Who you are — 20 seconds

`[ Live site, home page, top. Or your webcam if you'd rather — either is fine,
   and you only need it for these 20 seconds. ]`

Hi — I'm Gurneil.

This is Clinical Note Hallucination Guard.

I'm submitting to the ML Prompt Engineering track.

`[ beat ]`

It's a tool that checks AI-written medical notes for things that were never
actually said.

Let me show you why that matters.

---

## 1 · The problem — 30 seconds

`[ Live site, home page, top ]`

AI scribes listen to a doctor's appointment and write up the medical note.

They're being used in real clinics right now.

They also make things up.

A wrong dose. A symptom nobody mentioned. A "no" that turns into a "yes".

`[ pause a beat ]`

Everyone agrees a human has to check these notes before signing them.

But that means reading a full page of text, and hoping you spot the one wrong
sentence.

And the wrong sentence reads exactly like the right ones.

---

## 2 · What it does — 50 seconds

`[ Press "Run the demo". Wait for the console to open. ]`

This is my tool, running on a real test case.

It took the note apart into fourteen separate claims.

Then it checked every one of them against what the doctor and patient actually
said.

Thirteen are fine. One isn't.

`[ Click "Flags". Point at the first one. ]`

Here it is.

The note says the patient takes twenty milligrams of lisinopril.

The transcript says ten.

And it shows you the proof — the actual words from the conversation.

So instead of re-reading the whole note, you're checking one line.

`[ Click "Confirm" so the counter moves. ]`

It never changes the note itself.

Every flag goes to a person. Confirm, or dismiss.

That step is required. It's not optional.

---

## 3 · How it works — 40 seconds

`[ About → AI flowchart. Let the timeline run a few seconds, then click node 5. ]`

There are nine steps.

Two of them never use AI at all.

The dose check is just plain code — a number either matches or it doesn't. You
don't need a model for that.

`[ node 5 highlighted ]`

The one I'd point at is this one.

The earlier steps read the note and check it against the conversation.

That can't catch something the note left out completely.

So this step runs it backwards. It takes the facts from the conversation, and
checks whether each one made it into the note.

---

## 4 · It actually runs — 40 seconds

`[ Terminal, full screen, big font ]`

**Run these two lines BEFORE you start recording, then clear the screen** — so
the take opens on a clean prompt and the only thing on camera is the command
that matters:

```powershell
cd D:\clinical-note-guard
Set-Alias python D:\Python312\python.exe
cls
```

`[ Now start recording, and type: ]`

```
python demo.py 3 --no-review
```

This is the real thing running. Not a recording.

It writes a note from the transcript, breaks it into claims, and checks every
one of them.

`[ Let it run. Say nothing for a few seconds. Trim the slow bit later. ]`

**Then say whichever of these matches what you actually get:**

**If it raises flags:**

> And there it is. It found something in a note it wrote itself, thirty
> seconds ago.

**If it raises none — which is common, and fine:**

> This time it found nothing, and it says so.
>
> That matters as much as catching things. A checker that flags something on
> every note is a checker people stop reading.

> ⚠️ Unlike the site, this drafts a **fresh** note every run, so it doesn't
> always contain an error. Both outcomes are real and both are worth showing.
> Don't re-roll it ten times hunting for a catch — you have a limited daily
> quota, and the caught error is already on screen in section 2.

---

## 5 · The evidence — 50 seconds

**This is the most important part of the video. Slow down here.**

`[ Evidence page, results table ]`

Sixty test cases. Each one has a single error hidden in it.

Plus clean cases with nothing wrong, to see how often it cries wolf.

I graded them blind — while I was scoring, I couldn't tell which system was
which.

My pipeline caught forty-seven out of fifty. A single prompt caught forty-one.

`[ Scroll to the stronger-model section. Pause before speaking. ]`

Then I tested that on a model ten times bigger.

And it stopped being true.

My pipeline scored exactly the same. The simple prompt caught up.

`[ beat ]`

So here's what I think that actually means.

Breaking the note down helps a lot when the model is weak.

It doesn't add much on top of a model that's already strong.

That's a smaller claim than the one I started with.

I'm showing you it because it's the result.

A tool built to catch other people's mistakes shouldn't hide its own.

---

## 6 · Cost, and close — 30 seconds

`[ Evidence → Cost & caveats ]`

All of this is measured, not guessed.

It costs about five and a half times the tokens of a single prompt, and takes
roughly twice as long.

All on free API tiers. I spent nothing.

`[ Home page or the flowchart ]`

Every conversation in this project is made up. Fictional patients, written for
the test.

There's no real patient data anywhere in it, and it never diagnoses anyone.

It's a documentation check that keeps a human in charge — and tells you
honestly how well it works.

---

## Delivery notes

- **Read it once out loud before recording.** Any line you stumble on, change
  it. It's your video.
- **Slower than feels natural.** Everyone rushes their first take.
- **Don't apologise anywhere**, especially in section 5. "It stopped being
  true" is a finding, not a confession. Say it like one.
- If you fluff a line, pause for two seconds and say it again — the silence
  makes it easy to cut.

## Before you record

- [ ] Redeploy the site so it matches what you're showing
- [ ] Record 10 seconds, play it back, check the audio
- [ ] Focus Assist on (Win+N) so no notifications pop up
- [ ] Browser full screen, bookmarks bar hidden
- [ ] Terminal font 16pt or bigger
- [ ] **`python` is not on your PATH.** The `python.exe` Windows finds is a
      Microsoft Store placeholder that just prints an error. Use the alias
      above, or the full path `D:\Python312\python.exe`
- [ ] **Dry-run the demo once**, from `D:\clinical-note-guard`:
      `D:\Python312\python.exe demo.py 3 --no-review`. It makes live API calls
      and the free tiers run out. If it errors on rate limits, skip section 4
      rather than recording a failure — everything else in the video works
      without it

## After

- [ ] Under 6 minutes
- [ ] Track name said in the intro: ML Prompt Engineering
- [ ] Export 1080p (Clipchamp is built into Windows and is enough)
- [ ] Upload unlisted to YouTube
- [ ] **Open the link in a private window** to confirm it plays
