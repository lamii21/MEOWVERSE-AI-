"use client";

import { useReducedMotion } from "framer-motion";
import { useState } from "react";

import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";

/** A simple Original/AI Portrait toggle (Phase 14 spec §31 — "do not
 * make the UI overly complicated," a two-way switcher rather than a
 * drag slider), same accessible radiogroup pattern as
 * GradCamExplanation's Original/AI Focus/Overlay switcher. */
export function BeforeAfterViewer({
  originalUrl,
  portraitUrl,
  catName,
  styleName,
}: {
  originalUrl: string | null;
  portraitUrl: string;
  catName: string;
  styleName: string;
}) {
  const [view, setView] = useState<"original" | "portrait">("portrait");
  const reduceMotion = useReducedMotion();
  const activeUrl = view === "original" ? originalUrl : resolveMediaUrl(portraitUrl);

  return (
    <div>
      {originalUrl && (
        <div
          role="radiogroup"
          aria-label="Portrait comparison"
          className="mx-auto inline-flex gap-1 rounded-full border border-border p-1"
        >
          <button
            type="button"
            role="radio"
            aria-checked={view === "original"}
            onClick={() => setView("original")}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              view === "original"
                ? "bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            Original
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={view === "portrait"}
            onClick={() => setView("portrait")}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              view === "portrait"
                ? "bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            AI Portrait
          </button>
        </div>
      )}

      <div className="mx-auto mt-3 max-w-xs overflow-hidden rounded-2xl bg-muted">
        {activeUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={activeUrl}
            alt={
              view === "original"
                ? `The original photo of ${catName}.`
                : `AI-generated ${styleName.toLowerCase()} artwork of ${catName} — an artistic interpretation, not a photograph.`
            }
            className={cn(
              "aspect-square w-full object-cover",
              !reduceMotion && "transition-opacity duration-300",
            )}
          />
        ) : (
          <div className="flex aspect-square w-full items-center justify-center text-sm text-muted-foreground">
            Image unavailable
          </div>
        )}
      </div>
    </div>
  );
}
