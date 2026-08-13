import { useEffect, useState } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Types `segments` out one character at a time, across style boundaries, so
 * an italic run inside the line types like the rest of the sentence.
 *
 * The finished line is also rendered invisibly in the same grid cell, which
 * reserves the final height and stops the page reflowing as the text grows.
 */
export default function Typewriter({
  segments,
  speed = 45,
  startDelay = 350,
  className = "",
}) {
  const total = segments.reduce((n, s) => n + s.text.length, 0);
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setCount(total);
      return undefined;
    }
    let interval;
    const start = setTimeout(() => {
      interval = setInterval(() => {
        setCount((c) => {
          if (c >= total) {
            clearInterval(interval);
            return total;
          }
          return c + 1;
        });
      }, speed);
    }, startDelay);
    return () => {
      clearTimeout(start);
      clearInterval(interval);
    };
  }, [total, speed, startDelay]);

  const done = count >= total;
  let remaining = count;

  return (
    <span className={`grid ${className}`}>
      <span className="invisible col-start-1 row-start-1" aria-hidden="true">
        {segments.map((seg, i) =>
          seg.italic ? <em key={i}>{seg.text}</em> : <span key={i}>{seg.text}</span>
        )}
      </span>

      <span className="col-start-1 row-start-1">
        {segments.map((seg, i) => {
          const take = Math.max(0, Math.min(seg.text.length, remaining));
          remaining -= seg.text.length;
          const text = seg.text.slice(0, take);
          if (!text) return null;
          return seg.italic ? (
            <em key={i} className="italic">
              {text}
            </em>
          ) : (
            <span key={i}>{text}</span>
          );
        })}
        <span
          aria-hidden="true"
          className={`ml-0.5 inline-block h-[0.75em] w-[0.055em] translate-y-[0.02em] bg-foreground align-baseline ${
            done ? "opacity-0" : "animate-pulse"
          }`}
        />
      </span>
    </span>
  );
}
