import { Link } from "react-router-dom";

/** Shared furniture for the non-landing pages, so they read as one site. */

export function PageShell({ kicker, title, lede, children }) {
  return (
    <main className="mx-auto w-full max-w-4xl px-6 pb-24 pt-12 md:px-10">
      <p className="font-body text-sm text-muted-foreground">{kicker}</p>
      <h1 className="mt-2 font-display text-4xl leading-[1.05] tracking-tight text-foreground md:text-5xl">
        {title}
      </h1>
      {lede && (
        <p className="mt-4 max-w-[60ch] font-body text-base leading-relaxed text-muted-foreground md:text-lg">
          {lede}
        </p>
      )}
      <div className="mt-10 space-y-10">{children}</div>
    </main>
  );
}

export function Section({ title, children }) {
  return (
    <section>
      {title && (
        <h2 className="font-display text-2xl tracking-tight text-foreground">
          {title}
        </h2>
      )}
      <div className="mt-3 space-y-4 font-body text-sm leading-relaxed text-muted-foreground">
        {children}
      </div>
    </section>
  );
}

export function Stats({ items }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-lg border border-border bg-background p-4"
        >
          <div className="font-body text-xs text-muted-foreground">
            {item.label}
          </div>
          <div className="mt-1 font-display text-3xl tracking-tight text-foreground">
            {item.value}
          </div>
          {item.note && (
            <div className="mt-1 font-body text-xs text-muted-foreground">
              {item.note}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function Table({ columns, rows, caption }) {
  return (
    <figure>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[520px] border-collapse text-left font-body text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/40">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2.5 font-medium text-muted-foreground"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-border last:border-0">
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className={`px-4 py-2.5 ${
                      j === 0 ? "text-foreground" : "text-muted-foreground"
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {caption && (
        <figcaption className="mt-2 font-body text-xs text-muted-foreground">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

/** For the caveats this project insists on keeping next to its numbers. */
export function Callout({ tone = "muted", title, children }) {
  const tones = {
    muted: "border-border bg-secondary/40",
    warn: "border-amber-200 bg-amber-50",
    accent: "border-accent/30 bg-accent/5",
  };
  return (
    <div className={`rounded-lg border p-4 ${tones[tone]}`}>
      {title && (
        <div className="font-body text-sm font-medium text-foreground">
          {title}
        </div>
      )}
      <div className="mt-1 font-body text-sm leading-relaxed text-muted-foreground">
        {children}
      </div>
    </div>
  );
}

/** Where a number on the page actually came from in the repo. */
export function Source({ children }) {
  return (
    <p className="font-body text-xs text-muted-foreground">
      Source: <code className="text-foreground">{children}</code>
    </p>
  );
}

export function NextLinks({ items }) {
  return (
    <nav className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <Link
          key={item.to}
          to={item.to}
          className="rounded-lg border border-border bg-background p-4 transition-shadow hover:shadow-[0_2px_14px_rgba(0,0,0,0.07)]"
        >
          <div className="font-body text-sm font-medium text-foreground">
            {item.title}
          </div>
          <div className="mt-1 font-body text-xs leading-relaxed text-muted-foreground">
            {item.blurb}
          </div>
        </Link>
      ))}
    </nav>
  );
}
