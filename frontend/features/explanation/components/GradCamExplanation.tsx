"use client";

import { useMutation } from "@tanstack/react-query";
import { useReducedMotion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";
import { ExplanationApiError, fetchExplanation } from "@/services/explanation";

import type { AnalysisResult } from "@/types/analysis";

type ExplanationView = "original" | "focus" | "overlay";

const VIEWS: { value: ExplanationView; label: string }[] = [
  { value: "original", label: "Original" },
  { value: "focus", label: "AI Focus" },
  { value: "overlay", label: "Overlay" },
];

interface GradCamExplanationProps {
  result: AnalysisResult;
  /** A fresh analysis's local blob: preview URL, same fallback pattern
   * as `CatCard`/`CollectionCard` — falls back to the persisted photo
   * when this isn't provided (public/collection views). */
  catImageUrl?: string | null;
}

/**
 * "Why MeowVerse thinks this is a [breed]" (Phase 12) — deliberately
 * *not* auto-loaded like "Cats Like This": Grad-CAM only runs when the
 * user explicitly clicks "Why this breed?" (spec §31 — a real forward
 * + backward pass through the classifier is too expensive to run
 * unconditionally on every page view). The button always exists and
 * always makes the real request — whether the result is a genuine
 * heatmap or an honest "unavailable" is decided server-side from the
 * analysis's real `breed_mode`, never guessed here first.
 */
export function GradCamExplanation({ result, catImageUrl }: GradCamExplanationProps) {
  const [view, setView] = useState<ExplanationView>("overlay");
  const reduceMotion = useReducedMotion();
  const displayImageUrl = catImageUrl ?? resolveMediaUrl(result.image_url);

  const mutation = useMutation({
    mutationFn: () => fetchExplanation(result.id as string),
  });

  if (result.id === null || !result.breed) return null;

  const explanation = mutation.data;
  const activeImageUrl =
    view === "original"
      ? displayImageUrl
      : view === "focus"
        ? resolveMediaUrl(explanation?.heatmap_url)
        : resolveMediaUrl(explanation?.overlay_url);

  return (
    <section className="mx-auto mt-10 w-full max-w-md px-4 text-center sm:px-6">
      <h2 className="font-heading text-xl font-bold">
        Why MeowVerse thinks this is a {result.breed.label}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Grad-CAM highlights the image regions that contributed most to the breed prediction.
      </p>

      {!explanation && (
        <Button
          className="mt-4 gap-1.5 rounded-full"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          <Sparkles className="size-4" aria-hidden="true" />
          {mutation.isPending ? "Tracing the model's attention..." : "Why this breed?"}
        </Button>
      )}

      {mutation.isError && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {mutation.error instanceof ExplanationApiError
            ? mutation.error.message
            : "The Cat Universe is taking a nap. Try again soon."}
        </p>
      )}

      {explanation && explanation.mode === "unavailable" && (
        <div className="mt-4 rounded-2xl border border-border p-4 text-sm text-muted-foreground">
          <p className="font-medium text-foreground">Visual explanation unavailable</p>
          <p className="mt-1">{explanation.reason}</p>
        </div>
      )}

      {explanation && explanation.mode === "trained" && (
        <div className="mt-4">
          <div
            role="radiogroup"
            aria-label="Explanation view"
            className="inline-flex gap-1 rounded-full border border-border p-1"
          >
            {VIEWS.map((v) => (
              <button
                key={v.value}
                type="button"
                role="radio"
                aria-checked={view === v.value}
                onClick={() => setView(v.value)}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                  view === v.value
                    ? "bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {v.label}
              </button>
            ))}
          </div>

          <div className="mx-auto mt-4 max-w-xs overflow-hidden rounded-2xl bg-muted">
            {activeImageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={activeImageUrl}
                alt={
                  view === "original"
                    ? "The original uploaded cat photo."
                    : view === "focus"
                      ? `Grad-CAM visualization for the predicted ${explanation.target_class} breed.`
                      : `Grad-CAM overlay highlighting the regions that contributed most to the ${explanation.target_class} prediction.`
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

          <p className="mt-4 text-sm">
            Prediction confidence:{" "}
            <strong>{Math.round((explanation.confidence ?? 0) * 100)}%</strong>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Grad-CAM highlights regions that contributed most strongly to the prediction — an
            interpretability visualization, not proof, certainty, or a causal explanation of your
            cat&apos;s actual breed.
          </p>
        </div>
      )}
    </section>
  );
}
