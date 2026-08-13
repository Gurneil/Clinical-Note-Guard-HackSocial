# landing/

The project site for Clinical Note Hallucination Guard, with the guard itself
running in the hero. Vite + React. This replaces the earlier static site,
which now exists only in git history (`git checkout 5921049 -- _archive/`).

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # -> dist/
```

## Pages

| Route | Page |
| --- | --- |
| `/` | Hero + the guard console |
| `/evidence` | Results — pipeline vs. baseline, the node ablation, the caveats |
| `/evidence/docs` | The project's own documents, as downloads |
| `/evidence/cost` | Cost and latency, and what the numbers don't cover |
| `/about` | Founder |
| `/about/pipeline` | AI flowchart — the film with the nine nodes along it |

The pipeline film appears in exactly one place, `/about/pipeline`, where the
node captions make it mean something. It is deliberately not linked from
anywhere else: on its own it explains nothing. The hero's play button goes to
that page rather than opening the video.

Every figure on these pages comes from `docs/ARCHITECTURE.md` and the
committed `eval/` output, with the caveats the docs attach to them — the
auto-scored-not-blind-graded proviso, the provider mix, the false-positive
trade-off. The benchmark page reads its totals live from the same bundled
data the console uses, so it can't drift. Nothing here is invented; if a
number needs updating, update the eval and regenerate.

Navigation lives in one place, `src/lib/nav.js`, which feeds both the navbar
dropdowns and the route list. Routing is `HashRouter` (see the comment in
`src/App.jsx`) so sub-pages survive a refresh on plain static hosting —
switch to `BrowserRouter` if it lands somewhere with SPA fallback.

On screens below `sm` the dropdowns degrade to plain links to each section's
index page, since there's no hover to open them there.

Routes cross-fade on navigation — the outgoing page fades up and out, then
the next rises in (`AnimatedRoutes` in `src/App.jsx`, `mode="wait"`). The
first paint doesn't animate, so it doesn't compete with the hero's own
entrance.

The navbar hides itself while the guard is full screen, via `ChromeContext`
in `src/lib/chrome.js` — the header sits outside the routes and the console
is several levels inside one, so the two need somewhere neutral to meet. It
stays in the layout at `opacity: 0` rather than unmounting, so nothing jumps
when the console closes.

## The console is the product, not a screenshot

The card in the hero is a working review console over the real benchmark:

- **Real data, real verdicts.** Every claim, flag, explanation and evidence
  quote comes from `eval/raw_outputs.json` — the same committed run every
  number in `docs/ARCHITECTURE.md` comes from. Nothing is simulated in the
  browser. Run Guard steps through the claims for legibility and then shows
  what the pipeline actually found, labelled "replay of committed run" with
  the core-reasoning model that produced it.
- **All 60 cases** are browsable and selectable, including the 8 clean
  controls (which correctly show no findings) and the cases that errored
  during the run — shown as `errored`, never as a silent pass.
- **Views:** Overview, Flags, Transcript, Note, Cases, Benchmark. The
  Transcript view highlights the evidence spans the pipeline cited; the Note
  view highlights the deterministic node's flagged values and lists every
  extracted claim with its verdict.
- **The human checkpoint is real.** Each flag has Confirm / Dismiss, and the
  reviewed count tracks it — matching the project's position that a flag is
  a prompt for review, never a decision.

### Every control does something

There are no decorative affordances in the console — if it looks clickable,
it works:

| Control | What it does |
| --- | --- |
| Bell | Notifications built from live state: unreviewed flags on this case, whether the case errored during the run, how many cases errored overall, and the auto-scored-not-blind-graded advisory |
| Avatar | Reviewer identity (a stated placeholder), reviewed count, reset decisions, jump to settings |
| Logo chevron | Links to How it works / Evidence / The benchmark |
| Customize | Checkboxes for which quick-action pills show, plus reset to defaults |
| Settings (sidebar) | Auto-run on case select, hide reviewed flags, reset review decisions — all live |
| Pipeline items | Extraction opens the extracted claims; Entailment / Numeric check / Omission filter the flags to that node, with live counts |
| Nodes card / "View all N" | Open the flags list, unfiltered |
| Play button (hero) | Plays the 6s pipeline film in a lightbox |

The navbar CTA is the one thing that can't be finished here: the repo has no
git remote, so there's no GitHub URL to point at. Set `GITHUB_USER` in
`src/lib/site.js` and the black button becomes "View on GitHub" with the mark;
until then it reads "Read the docs" and goes to `/evidence/docs`, because a
working control with an honest label beats a GitHub button that 404s.

### The docs page

`/evidence/docs` serves the project's own documents — README, ARCHITECTURE,
PROMPTS, SAMPLES, the taxonomy and the workflow flowchart — as downloads.
They're copies under `public/docs/`, so re-sync after editing any of them:

```bash
npm run sync:docs
```

That script also writes `src/data/docs.json` with each file's real byte size,
so the page can't advertise a stale figure.

### Regenerating the data

`landing/src/data/cases.json` is generated. After any new eval run:

```bash
python landing/scripts/build_cases.py
```

This used to live at `frontend/build_cases.py` and emit a second bundle for
the old static site, which this one replaced.

## Layout and interaction

The hero fills the first screen, and the page scrolls a little past it so the
console can be read in full without expanding (`min-h-screen` on the root in
`src/App.jsx`). Body scroll is locked while the full-screen layer is open.

- **Drag** the console by its top bar to move it around the page. The search
  box and buttons stop the drag so they stay clickable.
- **Expand** (top-right of the console, or the "Run the demo" CTA) pins it
  full screen. Esc or a click on the scrim closes it. The console stays
  mounted across both states, so expanding never loses your place.
  Full screen also scales the whole console up — see `.guard-zoom` in
  `src/index.css`, which uses CSS `zoom` (it reflows, unlike
  `transform: scale`) rather than a second set of sizes for every label,
  icon and padding. 1× below `sm`, 1.25× above, 1.45× past 1600px.
- **The badge** is draggable anywhere on the page, but stops at the navbar so
  it can't be parked on top of the nav links.
- The headline types itself out on load. The finished line is also rendered
  invisibly in the same grid cell, so nothing reflows as it types; it
  renders instantly under `prefers-reduced-motion`.

## Structure

| File | What's in it |
| --- | --- |
| `src/index.css` | Google Fonts import + all design tokens as HSL CSS variables |
| `tailwind.config.js` | Maps the tokens onto Tailwind (`bg-background`, `font-display`, …) |
| `src/lib/guard.js` | Loads the committed run, derives per-case state and benchmark totals, hand-rolled Bézier path builder |
| `src/components/GuardStage.jsx` | Where the console lives: drag, full screen |
| `src/components/GuardConsole.jsx` | Console shell — top bar, sidebar, view switching, run state |
| `src/components/guardViews.jsx` | The six views |
| `src/components/Hero.jsx` | Background video, badge, headline, CTAs |
| `src/components/Typewriter.jsx` | Types across style boundaries without reflow |
| `src/components/GlassBadge.jsx` | Draggable liquid-glass pill |
| `src/components/Navbar.jsx` | Logo link, hover dropdowns, hover shadows |
| `src/components/PageKit.jsx` | Shared page furniture — shell, tables, stats, callouts |
| `src/components/NodeTimeline.jsx` | The film with the nine nodes as a scrubber |
| `src/components/Founder.jsx` | Founder story and photo — **placeholder copy** |
| `src/pages/` | The five content pages |

Colors are only ever referenced through semantic tokens, never as raw
hex/rgb, so retheming means editing `:root` in `src/index.css` alone. Light
mode only.

## Things you'll probably want to change

- **The background video** (`VIDEO_SRC` in `src/components/Hero.jsx`) is a
  generic stock clip. The project's own pipeline film is already vendored at
  `public/pipeline-flow.mp4` (from the original static site) and used on the
  pipeline page and in the hero's play button — point `VIDEO_SRC` at
  `/pipeline-flow.mp4` if you want it as the backdrop too.
- **The pipeline diagram** (`src/components/PipelineFlow.jsx`) draws the
  mechanism rather than listing it: the note→transcript and transcript→note
  paths run as two columns and converge on the human checkpoint, colour-coded
  by method (LLM / deterministic / human). Connectors are only drawn from
  `md` up, where the two columns exist.
- There is no `Guard` nav link — the guard runs on the home page itself.
- **`Dr. Reyes`** is a placeholder name in the greeting and the `DR` avatar.
- **The founder section is placeholder copy.** The anecdote in
  `src/components/Founder.jsx` was written to fit the page, not from life —
  replace it with something that actually happened before this is published.
  The photo is real: `public/founder.jpg`, resized and re-encoded from
  `assets-src/moonlight-river.png` (2076 kB → 173 kB). Keep full-size
  originals in `assets-src/`, not `public/` — everything in `public/` ships
  in the build. If the file is ever missing the frame falls back to a
  labelled placeholder rather than a broken image.
- **The node timeline** (`src/components/NodeTimeline.jsx`) plays the film at
  0.35× because it's under six seconds and nine nodes don't fit into that at
  full speed. The strip under the video is the scrubber: the accent line
  travels across the active node's cell as its segment plays, hands over to
  the next node at the end, and leaves a dim line behind on the cells already
  played. It's driven by `requestAnimationFrame`, not `timeupdate` — that
  event only fires ~4×/second, which is fine for switching nodes and far too
  coarse for a line that has to move smoothly.
- **The scope statement** ("does not diagnose patients", "all data is
  synthetic") lives on `/evidence/cost` now that `/about` is the founder page.
  Don't drop it — it's the one claim the project can't afford to leave
  implied.
- Flag counts in the console are raised flags, not graded recall. The blind
  human-graded numbers are the citable ones; the Benchmark view says so.
