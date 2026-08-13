/**
 * Copies the project's written docs into public/docs/ so the Docs page can
 * serve them as downloads, and writes src/data/docs.json with their real
 * sizes — so the page never advertises a stale figure.
 *
 * Run after editing any of the source docs:
 *     npm run sync:docs
 */
import { copyFileSync, mkdirSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const landing = resolve(here, "..");
const root = resolve(landing, "..");
const outDir = join(landing, "public", "docs");

const FILES = [
  {
    src: "README.md",
    title: "README",
    blurb: "Setup, how to run the pipeline and the eval, and the current status of the project.",
  },
  {
    src: "docs/ARCHITECTURE.md",
    title: "Architecture & reasoning",
    blurb: "Every node, why it exists, the evaluation methodology, the measured results and the known limitations.",
  },
  {
    src: "docs/PROMPTS.md",
    title: "Prompts",
    blurb: "Every prompt verbatim, what each constraint prevents, and the iterations behind them.",
  },
  {
    src: "docs/SAMPLES.md",
    title: "Samples",
    blurb: "Pipeline vs. baseline on four real cases, generated from the committed eval output.",
  },
  {
    src: "docs/SAMPLES_AUDIO.md",
    title: "Samples — audio",
    blurb: "A worked example of the audio path, including node 3b downgrading a verdict.",
  },
  {
    src: "taxonomy.json",
    title: "Error taxonomy",
    blurb: "The error categories, grounded in the ambient-scribe literature, that classification is constrained to.",
  },
  {
    src: "docs/workflow_flowchart.png",
    title: "Workflow flowchart",
    blurb: "The pipeline as a diagram — the required submission asset.",
  },
];

mkdirSync(outDir, { recursive: true });

const manifest = FILES.map((entry) => {
  const from = join(root, entry.src);
  const name = basename(entry.src);
  copyFileSync(from, join(outDir, name));
  return {
    file: name,
    path: entry.src,
    title: entry.title,
    blurb: entry.blurb,
    bytes: statSync(from).size,
  };
});

writeFileSync(
  join(landing, "src", "data", "docs.json"),
  `${JSON.stringify(manifest, null, 2)}\n`
);

const total = manifest.reduce((n, d) => n + d.bytes, 0);
console.log(`copied ${manifest.length} docs into public/docs (${Math.round(total / 1024)} kB)`);
for (const d of manifest) {
  console.log(`  ${d.file.padEnd(24)} ${String(Math.round(d.bytes / 1024)).padStart(4)} kB`);
}
