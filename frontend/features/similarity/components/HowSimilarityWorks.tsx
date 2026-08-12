"use client";

import { useState } from "react";
import { ChevronDown, ScanEye } from "lucide-react";

const STEPS = [
  "Your cat image is converted into a numerical embedding.",
  "Similar visual patterns are close together in vector space.",
  "FAISS searches the vector space.",
  "MeowVerse returns the closest eligible cats.",
];

/** A small, optional, collapsed-by-default technical explainer — Phase
 * 11 spec §36: portfolio-quality detail for anyone curious, never
 * forced on a normal user just trying to look at their cat. */
export function HowSimilarityWorks() {
  const [open, setOpen] = useState(false);

  return (
    <div className="mx-auto mt-4 max-w-md text-left">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mx-auto flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ScanEye className="size-3.5" aria-hidden="true" />
        How Similarity Works
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
