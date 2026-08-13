import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  CreditCard,
  FileText,
  Flag,
  Layers,
  LayoutGrid,
  Maximize2,
  Minimize2,
  Play,
  Search,
  Settings,
  Stethoscope,
} from "lucide-react";

import { benchmark, cases } from "@/lib/guard";
import {
  BenchmarkView,
  CasesView,
  FlagsView,
  NoteView,
  OverviewView,
  SettingsView,
  TranscriptView,
} from "@/components/guardViews";

const SIDEBAR = [
  { view: "overview", label: "Overview", icon: LayoutGrid },
  { view: "flags", label: "Flags", icon: Flag, badge: true },
  { view: "transcript", label: "Transcript", icon: FileText },
  { view: "note", label: "Note", icon: Stethoscope },
  { view: "cases", label: "Cases", icon: CreditCard },
  { view: "benchmark", label: "Benchmark", icon: Layers },
];

// Each pipeline entry goes somewhere that actually shows that node's work.
const PIPELINE = [
  { label: "Extraction", view: "note" },
  { label: "Entailment", node: "entailment" },
  { label: "Numeric check", node: "numeric" },
  { label: "Omission", node: "omission" },
  { label: "Settings", view: "settings" },
];

const ACTIONS = [
  { key: "run", label: "Run guard" },
  { key: "transcript", label: "Transcript" },
  { key: "note", label: "Note" },
  { key: "flags", label: "Flags" },
  { key: "cases", label: "Cases" },
  { key: "benchmark", label: "Benchmark" },
];

const DEFAULT_PILLS = ACTIONS.map((a) => a.key);

function Popover({ children, align = "right" }) {
  return (
    <div
      className={`absolute top-full z-50 mt-1.5 w-64 rounded-xl border border-border bg-background p-1.5 text-left shadow-[0_12px_40px_-12px_rgba(0,0,0,0.25)] ${
        align === "right" ? "right-0" : "left-0"
      }`}
    >
      {children}
    </div>
  );
}

function MenuItem({ children, onClick, to, sub }) {
  const className =
    "block w-full rounded-lg px-2.5 py-1.5 text-left hover:bg-secondary/70";
  const body = (
    <>
      <div className="text-foreground">{children}</div>
      {sub && (
        <div className="mt-0.5 text-[10px] leading-relaxed text-muted-foreground">
          {sub}
        </div>
      )}
    </>
  );
  if (to) {
    return (
      <Link to={to} className={className}>
        {body}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      {body}
    </button>
  );
}

const GuardConsole = forwardRef(function GuardConsole(
  { expanded = false, onToggleExpand },
  ref
) {
  const [caseIndex, setCaseIndex] = useState(0);
  const [view, setView] = useState("overview");
  const [phase, setPhase] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [decisions, setDecisions] = useState({});
  const [nodeFilter, setNodeFilter] = useState(null);
  const [query, setQuery] = useState("");
  const [menu, setMenu] = useState(null);
  const [pills, setPills] = useState(DEFAULT_PILLS);
  const [settings, setSettings] = useState({
    autoRun: true,
    hideReviewed: false,
  });
  const searchRef = useRef(null);

  const activeCase = cases[caseIndex];

  const run = useCallback(() => {
    setPhase("running");
    setProgress(0);
    setView("overview");
  }, []);

  useImperativeHandle(ref, () => ({ run }), [run]);

  // Step through the claims so the check reads as work being done, then
  // settle on the committed result. Nothing is computed here - the verdicts
  // were produced by the real pipeline run.
  useEffect(() => {
    if (phase !== "running") return undefined;
    const total = activeCase.claims.length;
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= total) {
          clearInterval(id);
          setPhase("done");
          return total;
        }
        return p + 1;
      });
    }, 70);
    return () => clearInterval(id);
  }, [phase, activeCase.claims.length]);

  // Kick off once on mount so the hero isn't a dead screenshot.
  useEffect(() => {
    const id = setTimeout(run, 1400);
    return () => clearTimeout(id);
  }, [run]);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") setMenu(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!menu) return undefined;
    const onDown = (event) => {
      if (!event.target.closest?.("[data-menu-root]")) setMenu(null);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [menu]);

  const selectCase = useCallback(
    (index) => {
      setCaseIndex(index);
      setDecisions({});
      setNodeFilter(null);
      setProgress(0);
      setView("overview");
      setPhase(settings.autoRun ? "running" : "idle");
    },
    [settings.autoRun]
  );

  const decide = useCallback((flagId, verdict) => {
    setDecisions((prev) => ({ ...prev, [flagId]: verdict }));
  }, []);

  const openNode = useCallback((node) => {
    setNodeFilter(node);
    setView("flags");
    setMenu(null);
  }, []);

  const resetDecisions = useCallback(() => {
    setDecisions({});
    setMenu(null);
  }, []);

  const filteredCases = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return cases;
    return cases.filter((c) =>
      [c.id, c.specialty, c.categoryLabel, c.note]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [query]);

  const unreviewed = activeCase.flags.filter((f) => !decisions[f.id]).length;

  const notifications = useMemo(() => {
    const list = [];
    if (unreviewed > 0) {
      list.push({
        id: "unreviewed",
        text: `${unreviewed} flag${unreviewed === 1 ? "" : "s"} on ${
          activeCase.shortId
        } awaiting review`,
        action: () => {
          setNodeFilter(null);
          setView("flags");
          setMenu(null);
        },
      });
    }
    if (activeCase.errored) {
      list.push({
        id: "errored",
        text: `${activeCase.shortId} errored during the committed run — no output to show`,
      });
    }
    list.push({
      id: "errored-total",
      text: `${benchmark.errored} of ${benchmark.totalCases} cases errored in this run`,
      action: () => {
        setView("benchmark");
        setMenu(null);
      },
    });
    list.push({
      id: "proxy",
      text: "Reported numbers are auto-scored, not blind human-graded",
      to: "/evidence",
    });
    return list;
  }, [activeCase.errored, activeCase.shortId, unreviewed]);

  const visibleActions = ACTIONS.filter((a) => pills.includes(a.key));

  const shared = {
    activeCase,
    decisions,
    onDecide: decide,
    hideReviewed: settings.hideReviewed,
  };

  const body = {
    overview: (
      <OverviewView
        {...shared}
        phase={phase}
        progress={progress}
        onOpenNode={openNode}
        onOpenFlags={() => {
          setNodeFilter(null);
          setView("flags");
        }}
      />
    ),
    flags: (
      <FlagsView
        {...shared}
        nodeFilter={nodeFilter}
        setNodeFilter={setNodeFilter}
      />
    ),
    transcript: <TranscriptView activeCase={activeCase} />,
    note: <NoteView activeCase={activeCase} />,
    cases: (
      <CasesView
        cases={filteredCases}
        activeId={activeCase.id}
        onSelect={selectCase}
        query={query.trim()}
      />
    ),
    benchmark: <BenchmarkView />,
    settings: (
      <SettingsView
        settings={settings}
        setSettings={setSettings}
        onReset={resetDecisions}
        reviewed={activeCase.flags.length - unreviewed}
        total={activeCase.flags.length}
      />
    ),
  }[view];

  const stopDrag = (event) => event.stopPropagation();

  return (
    <div
      className={`flex flex-col rounded-xl bg-background text-[11px] ${
        expanded
          ? "guard-zoom h-full overflow-hidden"
          : "min-w-[900px] overflow-hidden"
      }`}
    >
      {/* Top bar — also the drag handle when docked */}
      <div
        data-drag-handle
        className={`relative flex shrink-0 items-center justify-between gap-3 border-b border-border px-3 py-2 ${
          expanded ? "" : "cursor-grab active:cursor-grabbing"
        }`}
      >
        <div className="relative flex items-center gap-1.5" data-menu-root>
          <div className="flex h-5 w-5 items-center justify-center rounded-md bg-primary text-[10px] font-semibold text-primary-foreground">
            N
          </div>
          <span className="font-medium text-foreground">NoteGuard</span>
          <button
            type="button"
            onPointerDown={stopDrag}
            onClick={() => setMenu(menu === "brand" ? null : "brand")}
            aria-label="Project menu"
            aria-expanded={menu === "brand"}
            className="rounded p-0.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <ChevronDown className="h-3 w-3" />
          </button>
          {menu === "brand" && (
            <Popover align="left">
              <MenuItem to="/about/pipeline" sub="All nine nodes, on a timeline">
                How it works
              </MenuItem>
              <MenuItem to="/evidence" sub="What the committed run showed">
                Evidence
              </MenuItem>
              <MenuItem to="/about" sub="Who built this, and why">
                Founder
              </MenuItem>
            </Popover>
          )}
        </div>

        <div
          className="flex flex-1 max-w-xs items-center gap-2 rounded-md border border-border px-2 py-1"
          onPointerDown={stopDrag}
        >
          <Search className="h-3 w-3 shrink-0 text-muted-foreground" />
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setView("cases");
            }}
            placeholder="Search cases, claims…"
            className="w-full bg-transparent text-[11px] text-foreground outline-none placeholder:text-muted-foreground"
          />
          <span className="shrink-0 rounded border border-border px-1 text-[9px] text-muted-foreground">
            ⌘K
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onPointerDown={stopDrag}
            onClick={run}
            className="flex items-center gap-1 rounded-full bg-primary px-2.5 py-1 text-[10px] font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Play className="h-2.5 w-2.5 fill-primary-foreground" />
            {phase === "running" ? "Running…" : "Run Guard"}
          </button>

          <div className="relative" data-menu-root>
            <button
              type="button"
              onPointerDown={stopDrag}
              onClick={() => setMenu(menu === "bell" ? null : "bell")}
              aria-label={`Notifications${unreviewed ? ` (${unreviewed} unreviewed)` : ""}`}
              aria-expanded={menu === "bell"}
              className="relative flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <Bell className="h-3.5 w-3.5" />
              {unreviewed > 0 && (
                <span className="absolute right-0 top-0 h-1.5 w-1.5 rounded-full bg-accent" />
              )}
            </button>
            {menu === "bell" && (
              <Popover>
                <div className="px-2.5 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                  Notifications
                </div>
                {notifications.map((note) =>
                  note.to ? (
                    <MenuItem key={note.id} to={note.to}>
                      {note.text}
                    </MenuItem>
                  ) : (
                    <MenuItem key={note.id} onClick={note.action}>
                      {note.text}
                    </MenuItem>
                  )
                )}
              </Popover>
            )}
          </div>

          <div className="relative" data-menu-root>
            <button
              type="button"
              onPointerDown={stopDrag}
              onClick={() => setMenu(menu === "user" ? null : "user")}
              aria-label="Reviewer menu"
              aria-expanded={menu === "user"}
              className="flex h-5 w-5 items-center justify-center rounded-full bg-secondary text-[9px] font-medium text-secondary-foreground hover:bg-border"
            >
              DR
            </button>
            {menu === "user" && (
              <Popover>
                <div className="px-2.5 py-1.5">
                  <div className="text-foreground">Dr. Reyes</div>
                  <div className="mt-0.5 text-[10px] leading-relaxed text-muted-foreground">
                    Reviewer — placeholder identity, not a real account
                  </div>
                </div>
                <MenuItem
                  onClick={resetDecisions}
                  sub={`${activeCase.flags.length - unreviewed} of ${
                    activeCase.flags.length
                  } reviewed on this case`}
                >
                  Reset review decisions
                </MenuItem>
                <MenuItem
                  onClick={() => {
                    setMenu(null);
                    setView("settings");
                  }}
                >
                  Console settings
                </MenuItem>
              </Popover>
            )}
          </div>

          <button
            type="button"
            onPointerDown={stopDrag}
            onClick={onToggleExpand}
            title={expanded ? "Exit full screen (Esc)" : "Open full screen"}
            aria-label={expanded ? "Exit full screen" : "Open full screen"}
            className="ml-1 flex h-6 w-6 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            {expanded ? (
              <Minimize2 className="h-3 w-3" />
            ) : (
              <Maximize2 className="h-3 w-3" />
            )}
          </button>
        </div>
      </div>

      <div className={`flex min-h-0 flex-1 ${expanded ? "overflow-hidden" : ""}`}>
        {/* Below sm the sidebar would eat half the screen; the action pills
            in the main column cover the same navigation. */}
        <aside
          className={`hidden w-40 shrink-0 border-r border-border px-2 py-3 sm:block ${
            expanded ? "overflow-y-auto" : ""
          }`}
        >
          <div className="space-y-0.5">
            {SIDEBAR.map((item) => (
              <button
                key={item.view}
                type="button"
                onClick={() => setView(item.view)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left ${
                  view === item.view
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/60"
                }`}
              >
                <item.icon className="h-3 w-3 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {item.badge && activeCase.flags.length > 0 && (
                  <span className="rounded-full bg-secondary px-1.5 text-[9px] text-muted-foreground">
                    {activeCase.flags.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="mt-4 px-2 text-[9px] uppercase tracking-wide text-muted-foreground">
            Pipeline
          </div>
          <div className="mt-1 space-y-0.5">
            {PIPELINE.map((item) => {
              const active =
                (item.view && view === item.view) ||
                (item.node && view === "flags" && nodeFilter === item.node);
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() =>
                    item.node ? openNode(item.node) : setView(item.view)
                  }
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left ${
                    active
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/60"
                  }`}
                >
                  {item.label === "Settings" ? (
                    <Settings className="h-3 w-3" />
                  ) : (
                    <span className="h-1 w-1 rounded-full bg-muted-foreground" />
                  )}
                  <span className="flex-1">{item.label}</span>
                  {item.node && (
                    <span className="text-[9px] text-muted-foreground">
                      {activeCase.counts[item.node]}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>

        <main
          className={`min-w-0 flex-1 bg-secondary/30 p-3 ${
            expanded ? "overflow-y-auto" : ""
          }`}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div className="text-sm font-semibold text-foreground">
              Welcome, Dr. Reyes
            </div>
            <div className="text-[10px] text-muted-foreground">
              {activeCase.shortId} · replay of committed run
              {activeCase.model ? ` · ${activeCase.model}` : ""}
            </div>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {visibleActions.map((action) => {
              const isRun = action.key === "run";
              const active = !isRun && view === action.key;
              return (
                <button
                  key={action.key}
                  type="button"
                  onClick={() => (isRun ? run() : setView(action.key))}
                  className={`rounded-full px-2.5 py-1 text-[10px] ${
                    isRun
                      ? "bg-accent text-accent-foreground hover:bg-accent/90"
                      : active
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-background text-foreground hover:bg-secondary"
                  }`}
                >
                  {action.label}
                </button>
              );
            })}

            <div className="relative ml-1" data-menu-root>
              <button
                type="button"
                onClick={() => setMenu(menu === "customize" ? null : "customize")}
                aria-expanded={menu === "customize"}
                className="text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                Customize
              </button>
              {menu === "customize" && (
                <Popover align="left">
                  <div className="px-2.5 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    Quick actions
                  </div>
                  {ACTIONS.map((action) => (
                    <label
                      key={action.key}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 hover:bg-secondary/70"
                    >
                      <input
                        type="checkbox"
                        className="accent-accent"
                        checked={pills.includes(action.key)}
                        onChange={(event) =>
                          setPills((prev) =>
                            event.target.checked
                              ? [...new Set([...prev, action.key])]
                              : prev.filter((k) => k !== action.key)
                          )
                        }
                      />
                      <span className="text-foreground">{action.label}</span>
                    </label>
                  ))}
                  <button
                    type="button"
                    onClick={() => setPills(DEFAULT_PILLS)}
                    className="mt-1 w-full rounded-lg px-2.5 py-1.5 text-left text-muted-foreground hover:bg-secondary/70"
                  >
                    Reset to defaults
                  </button>
                </Popover>
              )}
            </div>
          </div>

          {body}

          <p className="mt-3 text-[9px] leading-relaxed text-muted-foreground">
            Synthetic transcripts and notes only — no real patient data. Flags
            are the pipeline's committed output; a flag is a prompt for human
            review, never a decision.
          </p>
        </main>
      </div>
    </div>
  );
});

export default GuardConsole;
