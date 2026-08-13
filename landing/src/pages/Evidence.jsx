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
          { label: "Recall", value: "88%", note: "45 of 51 planted errors" },
          { label: "Severity-weighted", value: "92%", note: "numeric and negation count more" },
          { label: "False positives", value: "15", note: "across 6 clean controls" },
        ]}
      />

      <Section>
        <Table
          columns={["System", "Recall", "Severity-weighted", "False positives"]}
          rows={[
            ["Pipeline", "45/51 (88%)", "92%", "15"],
            ["Baseline", "39/51 (76%)", "83%", "11"],
          ]}
          caption="57 scored cases — 51 with a planted error, 6 clean controls. Of the 60, two errored outright and one was excluded for a provider mismatch. The baseline prompt was fixed to ask for omissions too, so this tests workflow structure rather than a prompt gap."
        />
        <Source>eval/auto_scorecard.json, eval/raw_outputs.json</Source>
      </Section>

      <Callout tone="warn" title="Auto-scored, not blind human-graded">
        These come from <code>eval/auto_score.py</code>, which matches outputs
        against ground truth by keyword overlap rather than a person's
        judgment. Blind human grading — the project's stated methodology — has
        not been run at 60-case scale. Nothing here is a final, citable result
        until it has.
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
          notes with nothing wrong — roughly 2.5 per clean note against the
          baseline's 1.8. Decomposing into many atomic claims creates many
          independent chances for an over-literal judgment to misfire, where a
          single holistic read is more conservative and misses the subtler
          errors instead. A human reviews every flag either way.
        </p>
      </Section>

      <Section title="Does each node earn its place?">
        <p>
          Every flag records the node that produced it, so the committed run can
          be re-scored with any node withheld — no re-run, no extra API spend.
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
