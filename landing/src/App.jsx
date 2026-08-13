import { useEffect, useMemo, useState } from "react";
import { HashRouter, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import { ChromeContext } from "@/lib/chrome";
import About from "@/pages/About";
import Cost from "@/pages/Cost";
import Docs from "@/pages/Docs";
import Evidence from "@/pages/Evidence";
import NotFound from "@/pages/NotFound";
import Pipeline from "@/pages/Pipeline";

function ScrollToTop() {
  const { pathname } = useLocation();
  // Block body: an arrow returning scrollTo's value makes React treat it as
  // a cleanup function.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    // mode="wait" so the outgoing page finishes before the next one rises in;
    // initial={false} keeps the first paint from competing with the hero's
    // own entrance choreography.
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.28, ease: "easeOut" }}
        className="flex flex-1 flex-col"
      >
        <Routes location={location}>
          <Route path="/" element={<Hero />} />
          <Route path="/evidence" element={<Evidence />} />
          <Route path="/evidence/docs" element={<Docs />} />
          <Route path="/evidence/cost" element={<Cost />} />
          <Route path="/about" element={<About />} />
          <Route path="/about/pipeline" element={<Pipeline />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  const [chromeHidden, setChromeHidden] = useState(false);
  const chrome = useMemo(
    () => ({ chromeHidden, setChromeHidden }),
    [chromeHidden]
  );

  // HashRouter so the sub-pages survive a refresh on plain static hosting
  // (the rest of this project ships as files, with no server to rewrite
  // paths). Swap to BrowserRouter if it lands somewhere with SPA fallback.
  return (
    <ChromeContext.Provider value={chrome}>
      <HashRouter>
        <ScrollToTop />
        {/* The hero still fills the first screen, but the page is allowed to
            scroll past it so the console can be read in full. */}
        <div className="flex min-h-screen flex-col bg-background">
          <Navbar />
          <AnimatedRoutes />
        </div>
      </HashRouter>
    </ChromeContext.Provider>
  );
}
