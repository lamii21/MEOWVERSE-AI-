"use client";

import { useState } from "react";
import { ChevronDown, Sparkles } from "lucide-react";

const STEPS = [
  "MeowVerse starts from existing visual analysis signals — real breed and fur-color results, never re-measured here.",
  "A deterministic rules engine turns those signals into playful personality traits — the same photo always produces the same result.",
  "An AI model may turn those already-decided traits into creative text — it can't change the scores or pick a different archetype.",
  "The personality is an AI-inspired interpretation, not a scientific behavioral assessment.",
];

/** Collapsed-by-default technical explainer, same pattern as
 * `HowSimilarityWorks` (Phase 11) and integrated into "How MeowVerse
 * Knows" (Phase 13 spec §32/20). */
export function HowPersonalityWorks() {
  const [open, setOpen] = useState(false);

  return (
    <div className="mx-auto mt-4 max-w-md text-left">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mx-auto flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <Sparkles className="size-3.5" aria-hidden="true" />
        How Personality Works
        <ChevronDown
          className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <ol className="mt-3 flex flex-col gap-2 rounded-2xl border border-border bg-muted/30 p-4 text-xs text-muted-foreground">
          {STEPS.map((step, i) => (
            <li key={step} className="flex gap-2">
              <span className="font-heading font-semibold text-magic-500">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
