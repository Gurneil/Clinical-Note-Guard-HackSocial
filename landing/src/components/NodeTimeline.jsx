import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";

import { PIPELINE_FILM } from "@/lib/site";

/**
 * The pipeline film with the nine nodes laid along it as a timeline. The film
 * is ~6s, which is far too quick to read against, so it plays slowed down and
 * the strip below doubles as the scrubber: click a node to seek to it.
 *
 * This card is deliberately dark — it's a media surface, not page furniture,
 * so it uses literal colors rather than the light-only token palette.
 */

const NODES = [
  {
    n: "0",
    tag: "Input",
    title: "Transcript input",
    body: "The conversation itself, and the ground truth everything downstream is measured against. In this benchmark it's synthetic text; in a clinic it's the encounter.",
  },
  {
    n: "1",
    tag: "Draft",
    title: "Draft the note",
    body: "Stands in for whatever ambient scribe a clinic already runs. Routed through a failover chain so one provider outage can't take it down.",
  },
  {
    n: "2",
    tag: "Split",
    title: "Extract atomic claims",
    body: "A whole note can't be verified at once. One fact at a time can. Decomposition happens before any judgment does.",
  },
  {
    n: "3",
    tag: "Check",
    title: "Entailment check",
    body: "Every claim against the transcript in one structured pass — exactly one verdict per claim, in order. A count mismatch is a raised error, not a silent pass.",
  },
  {
    n: "3b",
    tag: "Source",
    title: "Transcript confidence",
    body: "A verdict is only as good as the audio under it. Claims resting on audio the recogniser was guessing at get downgraded to unverifiable, with a timestamp to go listen to.",
  },
  {
    n: "4",
    tag: "Exact",
    title: "Deterministic numeric check",
    body: "Doses and vitals don't need judgment, they need an exact match. A regex can't have an off day — though the ablation says node 3 was already catching these.",
  },
  {
    n: "5",
    tag: "Mirror",
    title: "Omission check",
    body: "The same pass in reverse: facts out of the transcript, then checked against the note. This is the only node that can notice something missing.",
  },
  {
    n: "6",
    tag: "Label",
    title: "Classify flagged claims",
    body: "Each commission flag gets a category from a fixed, literature-grounded taxonomy — not a generic \"this seems wrong\" — so findings stay comparable across cases.",
  },
  {
    n: "7",
    tag: "Sign",
    title: "Human review",
    body: "Required, not optional. Every flag reaches a person with its evidence, and nothing is finalized until they say so. The system never auto-corrects.",
  },
];

// Slow enough that a node stays on screen long enough to read.
const RATE = 0.35;

export default function NodeTimeline() {
  const videoRef = useRef(null);
  const [active, setActive] = useState(0);
  const [progress, setProgress] = useState(0);
  const [playing, setPlaying] = useState(true);

  // Driven off requestAnimationFrame rather than `timeupdate`, which only
  // fires about four times a second — enough to switch nodes, far too coarse
  // for a line that's supposed to travel smoothly across one.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return undefined;
    video.playbackRate = RATE;

    let frame;
    const tick = () => {
      if (video.duration) {
        const span = video.duration / NODES.length;
        const index = Math.min(
          NODES.length - 1,
          Math.floor(video.currentTime / span)
        );
        setActive(index);
        setProgress(Math.min(1, (video.currentTime - index * span) / span));
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);

    const onPlay = () => setPlaying(true);
    const onPause = () => setPlaying(false);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    return () => {
      cancelAnimationFrame(frame);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
    };
  }, []);

  const seekTo = (index) => {
    const video = videoRef.current;
    setActive(index);
    setProgress(0);
    if (!video?.duration) return;
    // Land at the start of the segment so the line begins its travel there.
    video.currentTime = (video.duration / NODES.length) * (index + 0.02);
  };

  const toggle = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) video.play();
    else video.pause();
  };

  const node = NODES[active];

  return (
    <figure
      className="overflow-hidden rounded-2xl"
      style={{ background: "#14181b" }}
    >
      <div className="relative">
        <video
          ref={videoRef}
          className="block aspect-video w-full object-cover"
          src={`${import.meta.env.BASE_URL}${PIPELINE_FILM}`}
          autoPlay
          loop
          muted
          playsInline
        />

        <span className="pointer-events-none absolute left-5 top-4 font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
          The flow, end to end
        </span>

        <div
          className="absolute inset-x-0 bottom-0 flex items-end gap-4 p-5 pt-16"
          style={{
            background:
              "linear-gradient(to top, rgba(10,13,15,0.92) 20%, rgba(10,13,15,0))",
          }}
        >
          <button
            type="button"
            onClick={toggle}
            aria-label={playing ? "Pause the film" : "Play the film"}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/20 bg-white/10 text-white backdrop-blur transition-colors hover:bg-white/20"
          >
            {playing ? (
              <Pause className="h-3.5 w-3.5 fill-white" />
            ) : (
              <Play className="h-3.5 w-3.5 translate-x-px fill-white" />
            )}
          </button>
          <div className="min-w-0">
            <div className="font-display text-2xl leading-tight text-white md:text-3xl">
              {node.title}
            </div>
            <p className="mt-1 max-w-[62ch] font-body text-xs leading-relaxed text-white/65 md:text-sm">
              {node.body}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-5 border-t border-white/10 md:grid-cols-9">
        {NODES.map((item, index) => {
          const on = index === active;
          // The line fills this node's cell as its segment plays, then the
          // next node takes over. Cells already played keep a dim line, so
          // the strip reads as a timeline rather than a row of tabs.
          const fill = on ? progress : index < active ? 1 : 0;
          return (
            <button
              key={item.n}
              type="button"
              onClick={() => seekTo(index)}
              aria-current={on}
              className={`relative border-b border-r border-white/10 px-2 py-3 text-center transition-colors last:border-r-0 ${
                on ? "bg-white/[0.07]" : "hover:bg-white/[0.04]"
              }`}
            >
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-x-0 top-0 h-[2px] origin-left"
                style={{
                  background: "hsl(var(--accent))",
                  opacity: on ? 1 : 0.28,
                  transform: `scaleX(${fill})`,
                }}
              />
              <div
                className={`font-display text-lg leading-none ${
                  on ? "text-white" : "text-white/45"
                }`}
              >
                {item.n}
              </div>
              <div
                className={`mt-1 font-mono text-[9px] uppercase tracking-[0.14em] ${
                  on ? "text-white/75" : "text-white/35"
                }`}
              >
                {item.tag}
              </div>
            </button>
          );
        })}
      </div>

      <figcaption className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
        <span className="font-body text-xs text-white/70">
          <strong className="font-medium text-white">
            Four of the nine never call a model.
          </strong>{" "}
          Node 0 is data, 3b and 4 are plain Python, and node 7 is a person.
        </span>
        <span className="font-mono text-[10px] text-white/35">
          generated with higgsfield · minimax 2.3
        </span>
      </figcaption>
    </figure>
  );
}
