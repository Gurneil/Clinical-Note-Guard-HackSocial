import {
  Callout,
  NextLinks,
  PageShell,
  Section,
  Source,
  Stats,
  Table,
} from "@/components/PageKit";
import { benchmark } from "@/lib/guard";

export default function Evidence() {
  return (
    <PageShell
      kicker="Evidence"
      title="What the run actually showed"
      lede="Decomposition-then-verify against a single open-ended prompt, over the same benchmark, scored the same way — including the parts that don't flatter the pipeline."
    >
      <Stats
        items={[
          { label: "Recall", value: "94%", note: "47 of 50 planted errors" },
          { label: "Severity-weighted", value: "93%", note: "numeric and negation count more" },
          { label: "False positives", value: "13", note: "across 6 clean controls" },
        ]}
      />

      <Section>
        <Table
          columns={["System", "Recall", "Severity-weighted", "False positives"]}
          rows={[
            ["Pipeline", "47/50 (94%)", "93%", "13"],
            ["Baseline", "41/50 (82%)", "87%", "9"],
          ]}
          caption="56 scored cases — 50 with a planted error, 6 clean controls. Of the 60, two errored outright, one was excluded for a provider mismatch, and one was skipped during grading. The baseline prompt was fixed to ask for omissions too, so this tests workflow structure rather than a prompt gap."
        />
        <Source>eval/scorecard_blind.csv, eval/raw_outputs.json</Source>
      </Section>

      <Callout tone="accent" title="Graded blind, by a human">
        A person graded every case seeing only "System A" and "System B",
        randomised per case, with no idea which was the pipeline — and the key
        stayed sealed until scoring ran. The automated proxy this project used
        while iterating predicted the result almost exactly: 88% vs 76%,
        against the human's 94% vs 82%. Harsher on both systems in absolute
        terms, and the same 12-point gap between them.
      </Callout>

      <Callout title="Which model produced this run">
        The free-tier Gemini quota (20/day) ran out three cases in, so the run
        used <code>gemini-3.6-flash</code> for 3 cases,{" "}
        <code>groq/llama-3.3-70b-versatile</code> for 2, and{" "}
        <code>featherless/Qwen2.5-7B-Instruct</code> for the other 53 — it
        mostly measures Qwen's judgment, not Gemini's.
      </Callout>

      <Section title="The trade-off">
        <p>
          The pipeline catches 6 more planted errors and raises more flags on
          notes with nothing wrong — roughly 2.2 per clean note against the
          baseline's 1.5. Decomposing into many atomic claims creates many
          independent chances for an over-literal judgment to misfire, where a
          single holistic read is more conservative and misses the subtler
          errors instead. A human reviews every flag either way.
        </p>
      </Section>

      <Section title="Does each node earn its place?">
        <p>
          Every flag records the node that produced it, so the committed run can
          be re-scored with any node withheld — no re-run, no extra API spend.
          These figures are auto-scored rather than human-graded: withholding a
          node changes which flags exist, so each configuration needs
          re-scoring, which a person cannot do blind. Given the proxy matched
          the human on the headline comparison above, the deltas are worth
          taking seriously.
        </p>
        <Table
          columns={["Configuration", "Recall", "False positives", "Delta"]}
          rows={[
            ["Full pipeline (3+4+5)", "45/51 (88.2%)", "15", "—"],
            ["Without node 3 (entailment)", "22/51 (43.1%)", "4", "+45.1"],
            ["Without node 4 (numeric)", "45/51 (88.2%)", "15", "+0.0"],
            ["Without node 5 (omission)", "43/51 (84.3%)", "11", "+3.9"],
          ]}
          caption="Node 3 is the engine: 23 planted errors were caught by it alone — and it raised 11 of the 15 false positives. Node 4 contributed zero marginal recall; every numeric error it caught, node 3 caught independently. It stays for reasons this benchmark doesn't confirm: no precision cost, determinism, and the highest-severity category."
        />
        <Source>eval/ablation_results.json</Source>
      </Section>

      <Section title="We tested the claim on a stronger model. It didn't hold.">
        <p>
          The result above used a 7B model for the reasoning both systems
          depend on. A second full run pinned a 70B model instead — roughly
          ten times the parameters. Both auto-scored by the same matcher, over
          the 44 planted-error cases that completed in both runs:
        </p>
        <Table
          columns={["Core-reasoning model", "Pipeline", "Baseline", "Gap"]}
          rows={[
            ["Qwen2.5-7B", "39/44 (89%)", "33/44 (75%)", "+14 pts"],
            ["Llama-3.3-70B", "39/44 (89%)", "40/44 (91%)", "−2 pts"],
          ]}
          caption="The pipeline scored identically on both. The baseline went from 33 to 40 once it had a competent model behind it — and two of the five cases it gained are omissions, the failure mode the pipeline has a dedicated node for."
        />
        <p>
          The honest reading is that decomposition compensates for a weak
          reasoner rather than adding capability on top of a strong one. It
          narrows the claim above rather than erasing it — that result is real
          on the model it used, and a weak reasoner is the situation any
          project on a free tier is actually in — but it stops being a general
          claim that workflow structure beats a single good prompt.
        </p>
        <p>
          This run is auto-scored rather than human-graded, covers 44 of 60
          cases (ten failed to rate limits, not difficulty), and is a single
          run per model.
        </p>
        <Source>eval/runs/README.md</Source>
      </Section>

      <Section title="What it was tested on">
        <p>
          {benchmark.totalCases} adversarial cases: each pairs a transcript with
          a note containing exactly one planted error of a known category, plus
          8 clean controls so false positives get measured too. Grading is
          blind — the grader sees "System A" and "System B" without knowing
          which is which. Every transcript, note and recording is synthetic:
          invented conversations about fictional patients. No real patient data
          is used or needed anywhere.
        </p>
      </Section>

      <NextLinks
        items={[
          {
            to: "/evidence/docs",
            title: "Docs →",
            blurb: "The architecture, prompts and samples documents themselves.",
          },
          {
            to: "/evidence/cost",
            title: "Cost & caveats →",
            blurb: "What it costs per note, and what this doesn't cover.",
          },
        ]}
      />
    </PageShell>
  );
}
