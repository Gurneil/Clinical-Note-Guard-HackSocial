import { motion } from "framer-motion";

/**
 * Draggable liquid-glass pill.
 *
 * Over a near-white hero, a lightly tinted panel reads as flat paint - the
 * glass only becomes legible when the fill is thin enough to let the video
 * through and the edges do the work: a bright top rim, a darker bottom rim
 * where the "thickness" catches shadow, and a specular sweep across the top
 * half. The blur is heavy and saturated so what shows through is visibly
 * refracted rather than just dimmed.
 *
 * The entrance animation and the drag offset live on two nested elements on
 * purpose - both want to own `y`, and sharing one motion value makes the
 * badge snap back to the entrance origin the first time you pick it up.
 */
export default function GlassBadge({ children, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`z-30 ${className}`}
    >
      <motion.div
        drag
        dragElastic={0.18}
        // top: 0 keeps the badge out of the navbar - drag it up there and it
        // would sit on the nav links, or read as hidden behind them.
        dragConstraints={{ top: 0, bottom: 520, left: -440, right: 440 }}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 1.06 }}
        title="Drag me"
        className="relative inline-flex cursor-grab select-none items-center overflow-hidden rounded-full px-5 py-2 text-sm text-foreground/75 active:cursor-grabbing font-body"
        style={{
          background:
            "linear-gradient(140deg, rgba(255,255,255,0.30) 0%, rgba(255,255,255,0.10) 45%, rgba(255,255,255,0.22) 100%)",
          backdropFilter: "blur(22px) saturate(200%) brightness(1.06)",
          WebkitBackdropFilter: "blur(22px) saturate(200%) brightness(1.06)",
          boxShadow: [
            // top rim light and bottom shade: the glass's own thickness
            "inset 0 1px 0.5px rgba(255,255,255,0.95)",
            "inset 0 -1px 1px rgba(255,255,255,0.30)",
            "inset 0 0 20px rgba(255,255,255,0.18)",
            // hairline edge, then a soft cast shadow so it floats
            "0 0 0 1px rgba(255,255,255,0.45)",
            "0 1px 2px rgba(16,24,32,0.06)",
            "0 10px 30px -6px rgba(16,24,32,0.18)",
          ].join(", "),
        }}
      >
        {/* specular sweep across the upper half */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-1/2"
          style={{
            background:
              "linear-gradient(to bottom, rgba(255,255,255,0.55), rgba(255,255,255,0))",
          }}
        />
        {/* a brighter glint at the top-left, where a curved edge would catch light */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -left-2 -top-6 h-12 w-24 rotate-[18deg]"
          style={{
            background:
              "radial-gradient(closest-side, rgba(255,255,255,0.55), rgba(255,255,255,0))",
          }}
        />
        <span className="relative">{children}</span>
      </motion.div>
    </motion.div>
  );
}
