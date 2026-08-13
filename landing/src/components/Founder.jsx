import { useState } from "react";
import { Link } from "react-router-dom";

/**
 * PLACEHOLDER COPY — the anecdote below was written to fit the page, not by
 * Gurneil and not from life. Swap it for something that actually happened
 * before this goes anywhere public.
 *
 * The photo is expected at `public/founder.jpg`. Until that file exists the
 * frame falls back to a labelled placeholder rather than a broken image.
 */

const STORY =
  "A model wrote me a paragraph about a paper I'd never read, with a page number and a direct quote. I went to check it. The paper was real. The author was real. The page didn't exist. Everything in that sentence was right except the one part that was supposed to be true — and nothing in the writing told me which part that was.";

const CODA =
  "That's the whole problem in a clinical note, except a person signs it. So I built something that reads a note one claim at a time, checks each against what was actually said, and hands a human everything that doesn't line up. It never signs anything. It just makes sure nobody signs without looking.";

export default function Founder() {
  const [photoOk, setPhotoOk] = useState(true);

  return (
    <section className="grid items-center gap-10 md:grid-cols-[1.15fr_0.85fr]">
      <div>
        <p className="font-body text-sm text-muted-foreground">Founder</p>
        <h1 className="mt-2 font-display text-4xl leading-[1.05] tracking-tight text-foreground md:text-5xl">
          Hey, I'm Gurneil.
        </h1>
        <p className="mt-5 font-body text-lg leading-relaxed text-muted-foreground">
          {STORY}
        </p>
        <p className="mt-4 font-body text-base leading-relaxed text-muted-foreground">
          {CODA}
        </p>
        <Link
          to="/about/pipeline"
          className="mt-6 inline-block font-body text-sm text-foreground underline-offset-4 hover:underline"
        >
          See how it works →
        </Link>
      </div>

      {/* Print-style mat: a cream border around the photo, very slightly
          off-square so it reads as a physical print on the page. */}
      <figure className="mx-auto w-full max-w-xs rotate-[-1.2deg] rounded-sm bg-[#f6f1e7] p-3 shadow-[0_18px_50px_-18px_rgba(0,0,0,0.35)]">
        <div className="aspect-[3/4] overflow-hidden rounded-sm border border-black/5 bg-secondary">
          {photoOk ? (
            <img
              src={`${import.meta.env.BASE_URL}founder.jpg`}
              alt="Gurneil"
              className="h-full w-full object-cover"
              onError={() => setPhotoOk(false)}
              loading="lazy"
            />
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-center">
              <span className="font-display text-3xl text-muted-foreground">
                G
              </span>
              <span className="font-body text-[11px] leading-relaxed text-muted-foreground">
                Drop the photo at
                <br />
                <code className="text-foreground">public/founder.jpg</code>
              </span>
            </div>
          )}
        </div>
      </figure>
    </section>
  );
}
