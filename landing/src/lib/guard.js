import rawCases from "@/data/cases.json";

/**
 * Everything the console knows comes from eval/raw_outputs.json by way of
 * frontend/build_cases.py. Nothing here invents a verdict: the console
 * replays what the pipeline actually produced on the committed run.
 */

export const NODES = {
  llm_pipeline: { key: "entailment", label: "Entailment" },
  deterministic_check: { key: "numeric", label: "Numeric check" },
  llm_pipeline_omission: { key: "omission", label: "Omission" },
};

export const CATEGORY_LABELS = {
  numeric_medication_error: "Numeric / medication",
  fabrication: "Fabrication",
  negation_error: "Negation",
  distortion: "Distortion",
  misattribution: "Misattribution",
  omission: "Omission",
  clean: "Clean control",
};

export const cases = rawCases.map((c, index) => {
  const flags = c.flags.map((f, i) => ({
    ...f,
    id: `${c.id}-${i}`,
    node: NODES[f.source]?.key ?? "entailment",
    nodeLabel: NODES[f.source]?.label ?? "Entailment",
  }));

  // A claim carries a verdict only if an entailment flag names it verbatim.
  // Deterministic and omission findings are not claim-scoped, so they stay
  // in the flag list rather than being pinned to a claim that never said it.
  const flaggedClaims = new Set(
    flags.filter((f) => f.node === "entailment").map((f) => f.claim)
  );

  return {
    ...c,
    index,
    flags,
    shortId: c.id.split("_").slice(0, 2).join("_"),
    category: c.planted?.category ?? "clean",
    categoryLabel: CATEGORY_LABELS[c.planted?.category ?? "clean"],
    claimStates: c.claims.map((text) => ({
      text,
      status: flaggedClaims.has(text) ? "contradicted" : "supported",
    })),
    counts: {
      entailment: flags.filter((f) => f.node === "entailment").length,
      numeric: flags.filter((f) => f.node === "numeric").length,
      omission: flags.filter((f) => f.node === "omission").length,
    },
  };
});

export const benchmark = (() => {
  const byCategory = {};
  for (const c of cases) {
    const bucket = (byCategory[c.category] ??= {
      label: c.categoryLabel,
      cases: 0,
      flagged: 0,
      flags: 0,
    });
    bucket.cases += 1;
    bucket.flags += c.flags.length;
    if (c.flags.length > 0) bucket.flagged += 1;
  }
  return {
    totalCases: cases.length,
    totalClaims: cases.reduce((n, c) => n + c.claims.length, 0),
    totalFlags: cases.reduce((n, c) => n + c.flags.length, 0),
    errored: cases.filter((c) => c.errored).length,
    byCategory: Object.values(byCategory).sort((a, b) => b.cases - a.cases),
    // Flags per case, in benchmark order, averaged into 20 buckets. Plotting
    // all 60 raw counts is legible but visually noisy at this size; the
    // buckets keep the real shape without the hash.
    series: Array.from({ length: 20 }, (_, i) => {
      const size = cases.length / 20;
      const slice = cases.slice(Math.round(i * size), Math.round((i + 1) * size));
      return slice.reduce((n, c) => n + c.flags.length, 0) / (slice.length || 1);
    }),
  };
})();

/**
 * Catmull-Rom control points expressed as cubic Béziers. Hand-rolled on
 * purpose: the chart is ~15 lines, a charting library would be 40kB.
 */
export function smoothPath(values, width, height, pad = 6) {
  const n = values.length;
  if (n < 2) return "";
  const max = Math.max(...values, 1);
  const pts = values.map((v, i) => [
    (i / (n - 1)) * width,
    height - pad - (v / max) * (height - pad * 2),
  ]);

  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < n - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d +=
      ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)}` +
      ` ${c2[0].toFixed(1)},${c2[1].toFixed(1)}` +
      ` ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}

/** Splits text so exact matches of `needles` can be highlighted in place. */
export function highlightSegments(text, needles) {
  const found = needles
    .map((needle) => ({ needle, at: needle ? text.indexOf(needle) : -1 }))
    .filter((m) => m.at !== -1)
    .sort((a, b) => a.at - b.at);

  const segments = [];
  let cursor = 0;
  for (const { needle, at } of found) {
    if (at < cursor) continue; // overlapping match, keep the earlier one
    if (at > cursor) segments.push({ text: text.slice(cursor, at) });
    segments.push({ text: needle, hit: true });
    cursor = at + needle.length;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}
