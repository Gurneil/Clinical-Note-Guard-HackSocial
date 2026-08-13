import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import GlassBadge from "@/components/GlassBadge";
import GuardStage from "@/components/GuardStage";
import Typewriter from "@/components/Typewriter";

const VIDEO_SRC = `${import.meta.env.BASE_URL}pipeline-flow.mp4`;

const HEADLINE = [
  { text: "AI Notes, " },
  { text: "Verified", italic: true },
  { text: " Claim by Claim" },
];

const fadeUp = (y, duration, delay = 0) => ({
  initial: { opacity: 0, y },
  animate: { opacity: 1, y: 0 },
  transition: { duration, delay, ease: "easeOut" },
});

export default function Hero() {
  const stageRef = useRef(null);

  return (
    <section className="relative flex-1 w-full overflow-hidden">
      {/* The project's own pipeline film, run at low opacity as a moving
          texture rather than a backdrop. At full strength it is a dark clip
          under dark text — unreadable. Faint, it gives the hero some life
          without costing contrast, and it is our asset rather than a stock
          clip streamed from someone else's CDN. */}
      <video
        className="absolute inset-0 z-0 h-full w-full object-cover opacity-[0.16]"
        src={VIDEO_SRC}
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
      />

      <div className="relative z-10 flex flex-col items-center w-full px-6 pb-14">
        {/* 1. Badge — drag it anywhere on the page */}
        <GlassBadge className="mb-6">Now with audio-aware verification ✨</GlassBadge>

        {/* 2. Headline */}
        <motion.h1
          {...fadeUp(16, 0.6, 0.1)}
          className="text-center font-display text-5xl md:text-6xl lg:text-[5rem] leading-[0.95] tracking-tight text-foreground max-w-xl"
        >
          <Typewriter segments={HEADLINE} startDelay={450} speed={45} />
        </motion.h1>

        {/* 3. Subheadline */}
        <motion.p
          {...fadeUp(16, 0.6, 0.2)}
          className="mt-4 text-center text-base md:text-lg text-muted-foreground max-w-[650px] leading-relaxed font-body"
        >
          Every AI-drafted note is decomposed into individually checkable
          claims, each one verified against the source transcript—so anything
          unsupported is flagged before a clinician signs.
        </motion.p>

        {/* 4. CTA buttons */}
        <motion.div
          {...fadeUp(16, 0.6, 0.3)}
          className="mt-5 flex items-center gap-3"
        >
          <Button
            onClick={() => stageRef.current?.openAndRun()}
            className="rounded-full px-6 py-5 text-sm font-medium font-body"
          >
            Run the demo
          </Button>
          {/* Goes to the flow, not to the bare film — the film explains
              nothing on its own. */}
          <Button
            asChild
            variant="ghost"
            className="h-11 w-11 rounded-full border-0 bg-background p-0 shadow-[0_2px_12px_rgba(0,0,0,0.08)] hover:bg-background/80"
            title="See how it works"
          >
            <Link to="/about/pipeline" aria-label="See how it works">
              <Play className="h-4 w-4 fill-foreground" />
            </Link>
          </Button>
        </motion.div>

        {/* 5. The guard itself — drag it by its top bar, or expand to full screen */}
        <GuardStage ref={stageRef} />
      </div>
    </section>
  );
}
