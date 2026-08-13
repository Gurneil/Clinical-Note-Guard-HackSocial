import { Check, ChevronRight, X } from "lucide-react";

import { benchmark, highlightSegments, smoothPath } from "@/lib/guard";

const NODE_TONE = {
  entailment: "text-accent",
  numeric: "text-amber-500",
  omission: "text-indigo-400",
};

function FlagChart() {
  const { series } = benchmark;
  const line = smoothPath(series, 300, 80);
  return (
    <svg viewBox="0 0 300 80" preserveAspectRatio="none" className="h-20 w-full">
      <defs>
        <linearGradient id="guardChartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.15" />
          <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${line} L300,80 L0,80 Z`} fill="url(#guardChartFill)" />
      <path
        d={line}
        fill="none"
        stroke="hsl(var(--accent))"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ReviewButtons({ flag, decision, onDecide }) {
  if (decision) {
    return (
      <span
        className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] ${
          decision === "accepted"
            ? "bg-emerald-50 text-emerald-600"
            : "bg-secondary text-muted-foreground"
        }`}
      >
        {decision === "accepted" ? "Confirmed" : "Dismissed"}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => onDecide(flag.id, "accepted")}
        title="This is a real error"
        className="flex items-center gap-1 whitespace-nowrap rounded-full border border-border px-2 py-0.5 text-[10px] text-foreground hover:bg-secondary"
      >
        <Check className="h-2.5 w-2.5" /> Confirm
      </button>
      <button
        type="button"
        onClick={() => onDecide(flag.id, "dismissed")}
        title="False positive — not an error"
        className="flex items-center gap-1 whitespace-nowrap rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-secondary"
      >
        <X className="h-2.5 w-2.5" /> Dismiss
      </button>
    </span>
  );
}

export function OverviewView({
  activeCase,
  phase,
  progress,
  decisions,
  onDecide,
  onOpenNode,
  onOpenFlags,
  hideReviewed = false,
}) {
  const claims = activeCase.claimStates;
  const shown = phase === "running" ? claims.slice(0, progress) : claims;
  const supported = shown.filter((c) => c.status === "supported").length;
  const reviewed = activeCase.flags.filter((f) => decisions[f.id]).length;
  const listed = hideReviewed
    ? activeCase.flags.filter((f) => !decisions[f.id])
    : activeCase.flags;

  return (
    <>
      <div className="mt-3 flex flex-col gap-3 lg:flex-row">
        {/* Claims card */}
        <div className="flex-1 basis-0 rounded-lg border border-border bg-background p-3">
          <div className="flex items-center gap-1 text-muted-foreground">
            <span>Claims Verified</span>
            {phase === "done" && <Check className="h-3 w-3 text-accent" />}
          </div>
          <div className="mt-1 flex items-baseline">
            <span className="text-lg font-semibold tracking-tight text-foreground">
              {supported}
            </span>
            <span className="ml-1 text-xs text-muted-foreground">
              of {claims.length} claims
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-[10px]">
            <span className="text-muted-foreground">{activeCase.categoryLabel}</span>
            <span className={activeCase.flags.length ? "text-accent" : "text-emerald-600"}>
              {activeCase.flags.length} flagged
            </span>
            <span className="text-muted-foreground">
              {reviewed} of {activeCase.flags.length} reviewed
            </span>
          </div>

          {phase === "running" && (
            <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-accent transition-[width] duration-100"
                style={{ width: `${(progress / claims.length) * 100}%` }}
              />
            </div>
          )}

          <div className="mt-2">
            <FlagChart />
          </div>
          <div className="text-[9px] text-muted-foreground">
            Flags per case across all {benchmark.totalCases} benchmark cases
          </div>
        </div>

        {/* Nodes card */}
        <div className="flex-1 basis-0 rounded-lg border border-border bg-background p-3">
          <div className="flex items-center justify-between">
            <span className="text-foreground">Nodes</span>
            <button
              type="button"
              onClick={onOpenFlags}
              className="text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              All flags
            </button>
          </div>
          <div className="mt-1">
            {[
              { key: "entailment", label: "Entailment" },
              { key: "omission", label: "Omission" },
              { key: "numeric", label: "Numeric check" },
            ].map((node) => (
              <button
                key={node.key}
                type="button"
                onClick={() => onOpenNode(node.key)}
                className="flex w-full items-center justify-between rounded-md py-3 text-xs hover:bg-secondary/60"
              >
                <span className="text-muted-foreground">{node.label}</span>
                <span className="flex items-center gap-1 text-foreground">
                  {activeCase.counts[node.key]}{" "}
                  {activeCase.counts[node.key] === 1 ? "flag" : "flags"}
                  <ChevronRight className="h-3 w-3 text-muted-foreground" />
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Flags table */}
      <div className="mt-3 rounded-lg border border-border bg-background p-3">
        <div className="flex items-center justify-between">
          <span className="text-foreground">Recent Flags</span>
          {listed.length > 4 ? (
            <button
              type="button"
              onClick={onOpenFlags}
              className="text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              View all {listed.length}
            </button>
          ) : (
            <span className="text-[10px] text-muted-foreground">
              {activeCase.shortId}
            </span>
          )}
        </div>

        {phase === "idle" ? (
          <div className="py-4 text-center text-[10px] text-muted-foreground">
            Not run yet — press Run Guard.
          </div>
        ) : activeCase.errored ? (
          <div className="py-4 text-center text-[10px] text-amber-600">
            This case errored out during the committed eval run — no output to
            show. It is counted as an error in the reported numbers, not as a
            clean pass.
          </div>
        ) : activeCase.flags.length === 0 ? (
          <div className="py-4 text-center text-[10px] text-emerald-600">
            No findings. {activeCase.hasError
              ? "The planted error was missed on this case."
              : "Clean control — correctly left alone."}
          </div>
        ) : listed.length === 0 ? (
          <div className="py-4 text-center text-[10px] text-muted-foreground">
            Every flag on this case has been reviewed.
          </div>
        ) : (
          <div className="-mx-1 mt-2 overflow-x-auto px-1">
          <table className="w-full min-w-[420px] text-left">
            <thead>
              <tr className="text-[10px] text-muted-foreground">
                <th className="w-[92px] font-normal">Case</th>
                <th className="font-normal">Finding</th>
                <th className="w-[92px] font-normal">Node</th>
                <th className="w-[150px] font-normal">Review</th>
              </tr>
            </thead>
            <tbody>
              {listed.slice(0, 4).map((flag) => (
                <tr key={flag.id} className="align-top text-[10px]">
                  <td className="py-1.5 text-muted-foreground">
                    {activeCase.shortId}
                  </td>
                  <td className="py-1.5 pr-2 text-foreground">{flag.claim}</td>
                  <td className={`py-1.5 ${NODE_TONE[flag.node]}`}>
                    {flag.nodeLabel}
                  </td>
                  <td className="py-1.5">
                    <ReviewButtons
                      flag={flag}
                      decision={decisions[flag.id]}
                      onDecide={onDecide}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </>
  );
}

export function FlagsView({
  activeCase,
  decisions,
  onDecide,
  nodeFilter,
  setNodeFilter,
  hideReviewed = false,
}) {
  const flags = activeCase.flags
    .filter((f) => (nodeFilter ? f.node === nodeFilter : true))
    .filter((f) => (hideReviewed ? !decisions[f.id] : true));

  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-1.5">
        {[
          { key: null, label: `All (${activeCase.flags.length})` },
          { key: "entailment", label: `Entailment (${activeCase.counts.entailment})` },
          { key: "omission", label: `Omission (${activeCase.counts.omission})` },
          { key: "numeric", label: `Numeric (${activeCase.counts.numeric})` },
        ].map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() => setNodeFilter(chip.key)}
            className={`rounded-full px-2.5 py-1 text-[10px] ${
              nodeFilter === chip.key
                ? "bg-primary text-primary-foreground"
                : "border border-border bg-background text-foreground hover:bg-secondary"
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>

      <div className="mt-2 space-y-2">
        {flags.length === 0 && (
          <div className="rounded-lg border border-border bg-background p-4 text-center text-[10px] text-muted-foreground">
            {hideReviewed && activeCase.flags.length > 0
              ? "Nothing left unreviewed here — reviewed flags are hidden in settings."
              : `Nothing flagged by this node on ${activeCase.shortId}.`}
          </div>
        )}
        {flags.map((flag) => (
          <div
            key={flag.id}
            className="rounded-lg border border-border bg-background p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-xs text-foreground">{flag.claim}</div>
                <div className="mt-0.5 flex items-center gap-2 text-[10px]">
                  <span className={NODE_TONE[flag.node]}>{flag.nodeLabel}</span>
                  <span className="text-muted-foreground">{flag.category}</span>
                </div>
              </div>
              <ReviewButtons
                flag={flag}
                decision={decisions[flag.id]}
                onDecide={onDecide}
              />
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
              {flag.why}
            </p>
            {flag.evidence && (
              <p className="mt-1.5 border-l-2 border-accent/40 pl-2 text-[10px] italic leading-relaxed text-muted-foreground">
                Transcript: “{flag.evidence}”
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function TranscriptView({ activeCase }) {
  const evidence = activeCase.flags.map((f) => f.evidence).filter(Boolean);
  const segments = highlightSegments(activeCase.transcript, evidence);
  return (
    <div className="mt-3 rounded-lg border border-border bg-background p-3">
      <div className="text-foreground">Source transcript</div>
      <div className="mt-0.5 text-[10px] text-muted-foreground">
        {activeCase.specialty} · synthetic, no real patient
      </div>
      <pre className="mt-2 whitespace-pre-wrap font-body text-[11px] leading-relaxed text-muted-foreground">
        {segments.map((seg, i) =>
          seg.hit ? (
            <mark key={i} className="bg-accent/15 text-foreground">
              {seg.text}
            </mark>
          ) : (
            <span key={i}>{seg.text}</span>
          )
        )}
      </pre>
    </div>
  );
}

export function NoteView({ activeCase }) {
  // Only the deterministic node's flagged values are literal note substrings;
  // entailment claims are paraphrases, so highlighting them would be a guess.
  const literals = activeCase.flags
    .filter((f) => f.node === "numeric")
    .map((f) => f.claim);
  const segments = highlightSegments(activeCase.note, literals);

  return (
    <div className="mt-3 space-y-3">
      <div className="rounded-lg border border-border bg-background p-3">
        <div className="text-foreground">Note under test</div>
        <div className="mt-0.5 text-[10px] text-muted-foreground">
          What the scribe drafted — unsigned
        </div>
        <pre className="mt-2 whitespace-pre-wrap font-body text-[11px] leading-relaxed text-muted-foreground">
          {segments.map((seg, i) =>
            seg.hit ? (
              <mark key={i} className="bg-amber-100 text-foreground">
                {seg.text}
              </mark>
            ) : (
              <span key={i}>{seg.text}</span>
            )
          )}
        </pre>
      </div>

      <div className="rounded-lg border border-border bg-background p-3">
        <div className="text-foreground">
          Extracted claims ({activeCase.claims.length})
        </div>
        <div className="mt-2 space-y-1">
          {activeCase.claimStates.map((claim) => (
            <div
              key={claim.text}
              className="flex items-start gap-2 text-[10px] leading-relaxed"
            >
              {claim.status === "supported" ? (
                <Check className="mt-0.5 h-2.5 w-2.5 shrink-0 text-emerald-600" />
              ) : (
                <X className="mt-0.5 h-2.5 w-2.5 shrink-0 text-red-500" />
              )}
              <span
                className={
                  claim.status === "supported"
                    ? "text-muted-foreground"
                    : "text-foreground"
                }
              >
                {claim.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CasesView({ cases, activeId, onSelect, query }) {
  return (
    <div className="mt-3 rounded-lg border border-border bg-background p-3">
      <div className="flex items-center justify-between">
        <span className="text-foreground">Benchmark cases</span>
        <span className="text-[10px] text-muted-foreground">
          {cases.length} shown{query ? ` for “${query}”` : ""}
        </span>
      </div>
      <div className="mt-2 max-h-[420px] space-y-0.5 overflow-y-auto pr-1">
        {cases.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onSelect(c.index)}
            className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[10px] ${
              c.id === activeId
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:bg-secondary/60"
            }`}
          >
            <span className="w-16 shrink-0 font-medium text-foreground">
              {c.shortId}
            </span>
            <span className="flex-1 truncate">{c.specialty}</span>
            <span className="shrink-0 rounded-full bg-secondary px-1.5 text-[9px]">
              {c.categoryLabel}
            </span>
            <span
              className={`w-14 shrink-0 text-right ${
                c.flags.length ? "text-accent" : "text-muted-foreground"
              }`}
            >
              {c.errored
                ? "errored"
                : `${c.flags.length} ${c.flags.length === 1 ? "flag" : "flags"}`}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Toggle({ label, hint, checked, onChange }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-border bg-background p-3">
      <span>
        <span className="block text-xs text-foreground">{label}</span>
        <span className="mt-0.5 block text-[10px] leading-relaxed text-muted-foreground">
          {hint}
        </span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-accent"
      />
    </label>
  );
}

export function SettingsView({ settings, setSettings, onReset, reviewed, total }) {
  return (
    <div className="mt-3 space-y-2">
      <Toggle
        label="Run the guard when a case is selected"
        hint="Off means a case opens on its committed result without replaying the claim-by-claim pass."
        checked={settings.autoRun}
        onChange={(autoRun) => setSettings((s) => ({ ...s, autoRun }))}
      />
      <Toggle
        label="Hide flags I've already reviewed"
        hint="Applies to the flags list and the overview table. Reviewed means confirmed or dismissed."
        checked={settings.hideReviewed}
        onChange={(hideReviewed) => setSettings((s) => ({ ...s, hideReviewed }))}
      />

      <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-background p-3">
        <span>
          <span className="block text-xs text-foreground">Review decisions</span>
          <span className="mt-0.5 block text-[10px] text-muted-foreground">
            {reviewed} of {total} reviewed on this case
          </span>
        </span>
        <button
          type="button"
          onClick={onReset}
          disabled={reviewed === 0}
          className="rounded-full border border-border px-2.5 py-1 text-[10px] text-foreground hover:bg-secondary disabled:opacity-40 disabled:hover:bg-transparent"
        >
          Reset
        </button>
      </div>

      <p className="px-1 text-[10px] leading-relaxed text-muted-foreground">
        These settings affect this console only. Review decisions live in the
        page and are cleared when you switch case or reload — nothing is
        written anywhere, and no decision here changes the committed run.
      </p>
    </div>
  );
}

export function BenchmarkView() {
  return (
    <div className="mt-3 space-y-3">
      <div className="flex flex-col gap-3 lg:flex-row">
        {[
          { label: "Cases", value: benchmark.totalCases },
          { label: "Claims extracted", value: benchmark.totalClaims },
          { label: "Flags raised", value: benchmark.totalFlags },
        ].map((stat) => (
          <div
            key={stat.label}
            className="flex-1 basis-0 rounded-lg border border-border bg-background p-3"
          >
            <div className="text-muted-foreground">{stat.label}</div>
            <div className="mt-1 text-lg font-semibold tracking-tight text-foreground">
              {stat.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-border bg-background p-3">
        <div className="text-foreground">By planted error category</div>
        <div className="-mx-1 mt-2 overflow-x-auto px-1">
        <table className="w-full min-w-[360px] text-left">
          <thead>
            <tr className="text-[10px] text-muted-foreground">
              <th className="font-normal">Category</th>
              <th className="w-20 font-normal">Cases</th>
              <th className="w-24 font-normal">With flags</th>
              <th className="w-20 font-normal">Flags</th>
            </tr>
          </thead>
          <tbody>
            {benchmark.byCategory.map((row) => (
              <tr key={row.label} className="text-[10px]">
                <td className="py-1.5 text-foreground">{row.label}</td>
                <td className="py-1.5 text-muted-foreground">{row.cases}</td>
                <td className="py-1.5 text-muted-foreground">{row.flagged}</td>
                <td className="py-1.5 text-muted-foreground">{row.flags}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
          Counts are raised flags, not graded recall — a flag is not credited as
          a catch until a human grades it. {benchmark.errored} case
          {benchmark.errored === 1 ? "" : "s"} errored during the committed run
          and are shown as errored rather than clean. Graded numbers live in
          docs/ARCHITECTURE.md.
        </p>
      </div>
    </div>
  );
}
