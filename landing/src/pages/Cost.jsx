import {
  Callout,
  NextLinks,
  PageShell,
  Section,
  Source,
  Stats,
  Table,
} from "@/components/PageKit";

const CAVEATS = [
  [
    "The transcript is assumed faithful",
    "Every benchmark case is hand-written text, so every number here measures note against transcript — never note against reality. If a transcript is wrong, the pipeline will confidently validate a note that matches it.",
  ],
  [
    "The numeric check is a pattern-matcher",
    "Node 4 recognises common formats — mg/mcg doses, blood pressures — not a full clinical NER system. It will miss numeric errors written unusually.",
  ],
  [
    "A residual paraphrase gap survives, deliberately",
    "\"Denies changes in weight, appetite, sleep, or energy\" — split into four atomic facts — is sometimes still marked contradicted against a transcript where the patient said \"everything's been stable\". Further prompt patches would overfit to this benchmark, so the false-positive rate is reported with it present.",
  ],
  [
    "Per-category numbers are thin",
    "60 cases is enough for the overall comparison to hold, but individual categories have only 7–10 each. A production benchmark would want dozens per category.",
  ],
];

export default function Cost() {
  return (
    <PageShell
      kicker="Evidence"
      title="What it costs, and what it doesn't cover"
      lede="A scalability claim is worth nothing without a number behind it. Every call records its provider, model, token counts — from the provider's own response metadata, never estimated — and wall-clock latency, failed calls included."
    >
      <Stats
        items={[
          { label: "Tokens per note", value: "5.5×", note: "pipeline vs. baseline" },
          { label: "Latency per note", value: "1.7×", note: "~12.8s vs. ~7.5s" },
          { label: "Actual spend", value: "$0", note: "free-tier API pricing" },
        ]}
      />

      <Section>
        <Table
          columns={["Measure", "Pipeline", "Baseline"]}
          rows={[
            ["LLM calls", "5.3", "1.0"],
            ["Tokens", "~3,280", "~600"],
            ["Wall-clock latency", "~12.8s", "~7.5s"],
          ]}
          caption="Measured over a fixed 7-case sample — one of each error category plus a clean control. Per-call cost doesn't depend on which case is checked, so this is real measured data at a fraction of a second eval run's budget."
        />
        <Source>eval/usage_summary.json</Source>
        <p>
          That's the direct price of decomposition — extraction, entailment,
          omission extraction, the omission check and classification, against
          the baseline's one call. It belongs next to the recall table when
          judging whether the accuracy is worth it, and the answer depends on
          note volume and reviewer cost at the deploying organisation.
        </p>
      </Section>

      <Section title="What these numbers don't cover">
        <div className="space-y-4">
          {CAVEATS.map(([title, body]) => (
            <div key={title}>
              <h3 className="font-body text-sm font-medium text-foreground">
                {title}
              </h3>
              <p className="mt-1 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Callout tone="warn" title="Scope">
        This project does not diagnose patients or recommend treatment. It's a
        documentation-reliability tool that assumes clinical judgment stays with
        a human at every step — nothing is ever auto-corrected, and a flag is a
        candidate for a person's decision.
      </Callout>

      <NextLinks
        items={[
          {
            to: "/evidence",
            title: "Results →",
            blurb: "The accuracy side of the trade-off.",
          },
          {
            to: "/evidence/docs",
            title: "Docs →",
            blurb: "The full architecture document, and everything else.",
          },
        ]}
      />
    </PageShell>
  );
}
