import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronDown, Github } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useChrome } from "@/lib/chrome";
import { NAV } from "@/lib/nav";
import { REPO_URL } from "@/lib/site";

const HOVER_SHADOW =
  "transition-shadow hover:shadow-[0_2px_12px_rgba(0,0,0,0.10)]";

function NavDropdown({ item }) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef(null);
  const { pathname } = useLocation();

  // A small grace period, so moving the pointer diagonally from the trigger
  // into the panel doesn't close the menu on the way.
  const openNow = () => {
    clearTimeout(closeTimer.current);
    setOpen(true);
  };
  const closeSoon = () => {
    clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setOpen(false), 140);
  };

  useEffect(() => () => clearTimeout(closeTimer.current), []);
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const active = pathname === item.to || pathname.startsWith(`${item.to}/`);

  return (
    <div
      className="relative"
      onMouseEnter={openNow}
      onMouseLeave={closeSoon}
      onFocus={openNow}
      onBlur={closeSoon}
      onKeyDown={(event) => event.key === "Escape" && setOpen(false)}
    >
      <Link
        to={item.to}
        aria-expanded={open}
        aria-haspopup="true"
        className={`flex items-center gap-1 rounded-full px-3 py-1.5 text-sm ${HOVER_SHADOW} ${
          active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        {item.label}
        <ChevronDown
          className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </Link>

      {open && (
        <div className="absolute left-1/2 top-full z-50 w-[290px] -translate-x-1/2 pt-2">
          <div className="rounded-xl border border-border bg-background p-1.5 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.22)]">
            {item.items.map((sub) => (
              <Link
                key={sub.to}
                to={sub.to}
                className={`block rounded-lg px-3 py-2 ${
                  pathname === sub.to ? "bg-secondary" : "hover:bg-secondary/70"
                }`}
              >
                <div className="text-sm text-foreground">{sub.title}</div>
                <div className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                  {sub.blurb}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Navbar() {
  const { chromeHidden } = useChrome();

  return (
    // Kept in the layout while hidden, so nothing jumps when the full-screen
    // guard closes.
    <header
      aria-hidden={chromeHidden}
      className={`relative z-40 flex items-center justify-between px-6 py-5 font-body transition-opacity duration-200 md:px-12 lg:px-20 ${
        chromeHidden ? "pointer-events-none opacity-0" : "opacity-100"
      }`}
    >
      {/* No dropdown on the logo — it just goes home. */}
      <Link
        to="/"
        className={`rounded-lg px-2 py-1 text-xl font-semibold tracking-tight text-foreground ${HOVER_SHADOW}`}
      >
        ✦ NoteGuard
      </Link>

      {/* Kept on small screens too: there is no hover there, so the triggers
          fall back to plain links to each section's index page. */}
      <nav className="flex items-center gap-1 md:gap-4">
        {NAV.map((item) =>
          item.items ? (
            <NavDropdown key={item.label} item={item} />
          ) : (
            <Link
              key={item.label}
              to={item.to}
              className={`hidden rounded-full px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground sm:block ${HOVER_SHADOW}`}
            >
              {item.label}
            </Link>
          )
        )}
      </nav>

      <Button
        asChild
        className="hidden items-center gap-2 rounded-full px-5 text-sm font-medium sm:inline-flex"
      >
        {REPO_URL ? (
          <a href={REPO_URL} target="_blank" rel="noreferrer noopener">
            <Github className="h-4 w-4" />
            View on GitHub
          </a>
        ) : (
          <Link to="/evidence/docs">Read the docs</Link>
        )}
      </Button>
    </header>
  );
}
