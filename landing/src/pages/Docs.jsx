import { Download } from "lucide-react";

import { Callout, NextLinks, PageShell, Section } from "@/components/PageKit";
import docs from "@/data/docs.json";

const kb = (bytes) =>
  bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} kB`;

export default function Docs() {
  return (
    <PageShell
      kicker="Evidence"
      title="Read the docs"
      lede="Everything the claims on this site rest on, as the files themselves. These are the working documents from the repository, not a summary written for a website."
    >
      <Section>
        <div className="space-y-2">
          {docs.map((doc) => (
            <a
              key={doc.file}
              href={`${import.meta.env.BASE_URL}docs/${doc.file}`}
              download={doc.file}
              className="flex items-start gap-4 rounded-lg border border-border bg-background p-4 transition-shadow hover:shadow-[0_2px_14px_rgba(0,0,0,0.07)]"
            >
              <Download className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-body text-sm font-medium text-foreground">
                    {doc.title}
                  </span>
                  <code className="font-mono text-xs text-muted-foreground">
                    {doc.path}
                  </code>
                </span>
                <span className="mt-1 block font-body text-sm leading-relaxed text-muted-foreground">
                  {doc.blurb}
                </span>
              </span>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {kb(doc.bytes)}
              </span>
            </a>
          ))}
        </div>
      </Section>

      <Callout title="Also in the repository">
        The committed eval output the numbers come from —{" "}
        <code>eval/raw_outputs.json</code>, <code>eval/auto_scorecard.json</code>,{" "}
        <code>eval/ablation_results.json</code>,{" "}
        <code>eval/usage_summary.json</code> — plus the blinded grading sheet
        and the scripts that produce all of it.
      </Callout>

      <NextLinks
        items={[
          {
            to: "/evidence",
            title: "Results →",
            blurb: "The short version of what these documents report.",
          },
          {
            to: "/evidence/cost",
            title: "Cost & caveats →",
            blurb: "What it costs per note, and what the numbers don't cover.",
          },
        ]}
      />
    </PageShell>
  );
}
