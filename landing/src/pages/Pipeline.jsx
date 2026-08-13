import { PageShell } from "@/components/PageKit";
import NodeTimeline from "@/components/NodeTimeline";

export default function Pipeline() {
  return (
    <PageShell
      kicker="About"
      title="How the guard works"
      lede="Nine nodes. The first drafts a note the way an ambient scribe would; the rest take it apart and check it against what was actually said. Scrub the timeline to read what each one does."
    >
      <NodeTimeline />
    </PageShell>
  );
}
