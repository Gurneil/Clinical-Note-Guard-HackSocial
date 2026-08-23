# Pre-submission boosts — paste-ready

Four additions, ordered by leverage. Total time if you do all four: ~35 minutes.

---

## 1. Corrected workflow flowchart (do this one — it's a defect, not a polish)

The required flowchart labelled nodes 2, 5 and 6 as `Groq llama-3.1-8b-instant`.
`src/config.py` has said `openai/gpt-oss-20b` since Groq retired that model
mid-project. The generator's own docstring says the diagram exists so it
"doesn't silently drift out of sync with the code" — and it had drifted.

A judge who opens `config.py` next to the diagram finds the mismatch, and in a
project whose entire pitch is *our numbers are accurate and we say so when
they aren't*, that's the worst possible place to have one.

Fixed and regenerated. Both files are already written to your repo:

- `docs/generate_flowchart.py` — model labels corrected, plus two footer lines
  recording that the committed eval runs used the retired models
- `docs/workflow_flowchart.png` — regenerated
- `landing/public/docs/workflow_flowchart.png` — synced copy

Then:

```
git add docs/generate_flowchart.py docs/workflow_flowchart.png landing/public/docs/workflow_flowchart.png
git commit -m "Flowchart: name the models that are actually configured"
git push
```

Re-upload the PNG to Devpost, and redeploy the site if you want the hosted copy
current too.

---

## 2. Put a judge's tour at the top of "About the project"

Judges skim dozens of entries. Right now your write-up opens with Inspiration —
good prose, but it makes a judge work for 90 seconds before they know what to
click. Paste this **above** `## Inspiration`:

```markdown
## For a judge with 90 seconds

- **See it run:** https://clinicalnoteguard.netlify.app — the console on the
  homepage replays the real committed evaluation over all 60 benchmark cases.
  Nothing in it is simulated in the browser.
- **The required three files:** [workflow flowchart](https://clinicalnoteguard.netlify.app/docs/workflow_flowchart.png)
  · [samples vs. single-prompt](https://clinicalnoteguard.netlify.app/docs/SAMPLES.md)
  · [per-node documentation](https://clinicalnoteguard.netlify.app/docs/ARCHITECTURE.md)
  and [every prompt verbatim](https://clinicalnoteguard.netlify.app/docs/PROMPTS.md).
- **The headline number:** 94% of planted errors caught vs. a single prompt's
  82% — graded blind by a human, key sealed until scoring ran.
- **The number we'd rather you heard from us:** that advantage disappears on a
  10× larger reasoning model. It's in the write-up below, under "Then we tested
  that claim on a stronger model."
```

---

## 3. Give the Sustainability/Scalability criterion something to score

It's a full quarter of the rubric, and your Devpost page currently has nothing
on it — the cost/latency work is real, but it's buried at line 649 of a 45,000-
character architecture doc that most judges won't open. Judges score the Devpost
page. Paste this after `## Results`:

```markdown
## What it costs, and what it would take to run for real

Measured, not estimated — `src/usage.py` records provider, model, token counts
(from the provider's own response metadata) and wall-clock latency on every
call, failed calls included:

| Per note checked | Pipeline | Baseline |
|---|---|---|
| LLM calls | 5.3 | 1.0 |
| Tokens | ~3,280 | ~600 |
| Latency | ~12.8s | ~7.5s |

So the guard costs ~5.5× the tokens and ~1.7× the latency of a single prompt.
Whether that trades well depends on note volume and reviewer cost at the
deploying organisation — a question this project deliberately does not answer
on anyone's behalf. Actual spend to build and evaluate all of it: $0, on free
tiers.

Scaling it is an integration problem rather than a research one. The pipeline
is provider-agnostic by construction (`src/llm_router.py`), so a hospital
running an on-premise model swaps one config entry rather than rewriting nodes;
the two deterministic nodes never call a model at all. The real gates are the
ones any clinical-documentation tool faces — a BAA with whoever serves the
model, or a self-hosted one; latency inside the seconds a clinician will
actually wait at sign-off; and a false-positive rate low enough that reviewers
keep reading the flags. That last one is ours to fix, and it's the honest
weakness: 13 false positives across 6 clean controls.
```

---

## 4. Protect the negative result from a skim

"Then we tested that claim on a stronger model, and it didn't hold" is the most
admirable thing in your submission and the easiest to misread as *the project
doesn't work*. Give the skimming judge the frame before the finding. Add this
directly under that heading, before "The result above used a 7B model":

```markdown
*What still holds: on the model this actually runs on, the guard catches 94% of
planted errors against a single prompt's 82%, graded blind. What follows
narrows that claim rather than retracting it — and we ran the experiment
against ourselves rather than around it.*
```

---

## Optional, if you have a spare five minutes

- **`README.md`** — it opens with 18,000 characters and no image. Put
  `![Workflow](docs/workflow_flowchart.png)` under the first paragraph; a repo
  with a diagram at the top reads as finished before anyone reads a word.
- **`README.md`** — rename "Current status / what's left before submission" to
  "What's built", and move the single unchecked box into a short "What's next"
  section. Same information, minus the *unfinished project* first impression.
- **`submission/context.md` line 47** — still quotes the old auto-scored 45/51
  vs 39 while everything else quotes the blind-graded 47/50 vs 41/50.
