# Bounty 2 — feedback form

Everything between the lines below is meant to be typed or pasted straight
into Google Forms, in order. Guidance for you (not for the form) is at the
bottom.

Set the form to **collect responses without sign-in**, and share every file
you submit as **"Anyone with the link can view"** — staff warned on Aug 10
that unshared files score zero.

---

## PASTE 1 — Form title

```
Clinical Note Hallucination Guard — reviewer feedback
```

## PASTE 2 — Form description

```
Thanks for testing this. It's a tool that checks AI-drafted medical notes for things the doctor and patient never actually said, before a clinician signs them.

Open it here: https://clinicalnoteguard.netlify.app

Please keep it open in another tab while you answer — most questions ask you to try something specific. It takes about 10 minutes. No account, no download, nothing to install.

Be blunt in the last section. Polite feedback is useless to me; the point is to find what's broken or confusing while there's still time to fix it.

Everything in the tool is synthetic — invented conversations about fictional patients. There is no real patient data anywhere in it.
```

---

## SECTION 1 — About you

**Section title:** `About you`

**Q1** · Short answer · *required*
```
Your name
```
Description:
```
So I can credit your review in the submission.
```

**Q2** · Multiple choice · *required*
```
Which describes you best?
```
Options:
```
Student
Work in healthcare
Work in software
None of these
```

**Q3** · Multiple choice
```
Before today, did you know that AI tools already draft clinical notes from doctor–patient conversations?
```
Options:
```
Yes
No
I'd heard something about it
```

---

## SECTION 2 — First impressions

**Section title:** `First impressions`

**Section description:**
```
Spend one minute on the home page. Don't click anything yet.
```

**Q4** · Paragraph · *required*
```
In your own words, what does this product do?
```

**Q5** · Paragraph · *required*
```
Who do you think it's built for?
```

**Q6** · Linear scale 1–5
```
How clear was that from the page?
```
Labels: `1 = Had to guess` · `5 = Immediately obvious`

---

## SECTION 3 — Using the guard

**Section title:** `Using the guard`

**Section description:**
```
On the home page, press "Run the demo". It opens the review console full screen on a case called case_01.
```

**Q7** · Paragraph
```
The card says "13 of 14 claims" and "3 flagged". What do you think those numbers mean?
```

**Q8** · Paragraph · *required*
```
Open the Flags view and read one flag. Could you tell what the system thought was wrong, and why it thought so? What was missing?
```

**Q9** · Paragraph
```
Each flag has Confirm and Dismiss. Was it clear what those do — and what happens after you press one?
```

**Q10** · Paragraph
```
Was there anything you expected to be able to do and couldn't?
```

---

## SECTION 4 — Trust

**Section title:** `Trust`

**Q11** · Paragraph · *required*
```
The site openly says a fallback model produced most of its results, and shows its own false-positive count. Did you notice that? Did it make you trust the project more, or less?
```

**Q12** · Paragraph
```
Would you want a tool like this checking a note before a doctor signed it? Why, or why not?
```

---

## SECTION 5 — The blunt bit

**Section title:** `The blunt bit`

**Section description:**
```
This section is what the improvement plan gets built from, so please don't be nice.
```

**Q13** · Paragraph · *required*
```
What is the single worst thing about this project?
```

**Q14** · Paragraph · *required*
```
If I could only change one thing, what should it be?
```

**Q15** · Paragraph
```
Anything else?
```

---
---

# Notes for you (do not paste)

## How many, and who

**Aim for 5.** The bounty requires 3+, so three is a pass and five reads as
effort without costing much more.

**The mix matters more than the count.** Try to get one of each:

- **Someone non-technical.** Q4 asks what the product does in their own
  words. If a normal person can't answer that after a minute on the home
  page, that is the most valuable thing you will learn this week, and no
  amount of technical praise substitutes for it.
- **Someone technical.** They will push on the methodology and the numbers,
  which is where the project is strongest and where you want a quotable
  reaction.
- **Someone near healthcare** — a nursing or med student, a pharmacy tech, a
  relative who works in a clinic. One sentence from someone who has actually
  read a clinical note outweighs five from people who haven't.

Family and friends count. The hackathon Discord's general channel is the
fastest route to a technical reviewer; offering to review theirs in exchange
usually gets you a proper paragraph back.

## After the responses land

The second half of the bounty is a plan addressing the grievances. Send the
responses over and we'll turn them into that document — and implement the
cheap fixes before submitting, which is far stronger than promising them.
