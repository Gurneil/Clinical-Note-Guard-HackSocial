import { NextLinks, PageShell } from "@/components/PageKit";

export default function NotFound() {
  return (
    <PageShell
      kicker="404"
      title="Nothing here"
      lede="That page doesn't exist — which is at least an honest verdict."
    >
      <NextLinks
        items={[
          { to: "/", title: "Home →", blurb: "The guard, running on the benchmark." },
          { to: "/evidence", title: "Evidence →", blurb: "What the committed run showed." },
        ]}
      />
    </PageShell>
  );
}
