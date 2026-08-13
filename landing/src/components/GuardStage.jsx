import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion, useDragControls, useMotionValue } from "framer-motion";

import GuardConsole from "@/components/GuardConsole";
import { useChrome } from "@/lib/chrome";

const FROSTED = {
  background: "rgba(255, 255, 255, 0.4)",
  border: "1px solid rgba(255, 255, 255, 0.5)",
  boxShadow: "var(--shadow-dashboard)",
};

/**
 * Owns where the console lives: draggable by its top bar while docked in the
 * hero, or pinned full screen. The console itself stays mounted across both,
 * so expanding never loses the case you were reviewing.
 *
 * The entrance animation deliberately sits on the inner element: a transformed
 * ancestor would become the containing block for `position: fixed`, and the
 * full-screen state would then be positioned against the hero instead of the
 * viewport.
 */
const GuardStage = forwardRef(function GuardStage(_props, ref) {
  const [expanded, setExpanded] = useState(false);
  const consoleRef = useRef(null);
  const dragControls = useDragControls();
  const { setChromeHidden } = useChrome();
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const setExpandedAt = useCallback(
    (next) => {
      // Drop any drag offset first, so the full-screen layer isn't nudged by
      // wherever the card happened to be sitting.
      x.set(0);
      y.set(0);
      setExpanded(next);
      // The navbar would otherwise sit in the margin around the full-screen
      // console, reading as part of its UI.
      setChromeHidden(next);
    },
    [setChromeHidden, x, y]
  );

  // Leaving the page while expanded shouldn't strand the navbar hidden.
  useEffect(() => () => setChromeHidden(false), [setChromeHidden]);

  useImperativeHandle(
    ref,
    () => ({
      run: () => consoleRef.current?.run(),
      openAndRun: () => {
        setExpandedAt(true);
        consoleRef.current?.run();
      },
    }),
    [setExpandedAt]
  );

  useEffect(() => {
    if (!expanded) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") setExpandedAt(false);
    };
    window.addEventListener("keydown", onKey);
    // The page scrolls now, so hold it still behind the full-screen layer.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [expanded, setExpandedAt]);

  const startDrag = (event) => {
    if (expanded) return;
    if (!event.target.closest?.("[data-drag-handle]")) return;
    dragControls.start(event);
  };

  return (
    <>
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setExpandedAt(false)}
            className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      <motion.div
        style={{ x, y }}
        drag={!expanded}
        dragListener={false}
        dragControls={dragControls}
        dragMomentum={false}
        dragElastic={0.06}
        dragConstraints={{ top: -220, bottom: 220, left: -340, right: 340 }}
        onPointerDown={startDrag}
        className={
          expanded
            ? "fixed inset-0 z-50 p-3 md:p-8"
            : "relative mt-8 w-full max-w-5xl"
        }
      >
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
          className={`rounded-2xl p-3 md:p-4 ${
            expanded ? "h-full overflow-hidden" : "overflow-hidden"
          }`}
          style={FROSTED}
        >
          <GuardConsole
            ref={consoleRef}
            expanded={expanded}
            onToggleExpand={() => setExpandedAt(!expanded)}
          />
        </motion.div>
      </motion.div>
    </>
  );
});

export default GuardStage;
