"use client";

import { AlertCircle, Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { generateStory, shareStory, StoryApiError } from "@/services/stories";

import { StoryCard } from "./StoryCard";
import { StoryLoader } from "./StoryLoader";
import { StoryStyleSelector } from "./StoryStyleSelector";

import type { StoryResponse, StoryStyle } from "@/types/story";

type StoryUiStatus = "idle" | "pending" | "success" | "error";

interface StorySectionProps {
  /** Null when the analysis couldn't be persisted (see AnalysisResult.id
   * docs) — story generation genuinely can't work without a saved
   * analysis to attach it to. */
  analysisId: string | null;
  catImageUrl?: string | null;
}

export function StorySection({ analysisId, catImageUrl }: StorySectionProps) {
  const [style, setStyle] = useState<StoryStyle>("magical_adventure");
  const [status, setStatus] = useState<StoryUiStatus>("idle");
  const [story, setStory] = useState<StoryResponse | null>(null);
  const [error, setError] = useState<StoryApiError | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const generate = (regenerate: boolean) => {
    if (!analysisId) return;
    if (regenerate) setIsRegenerating(true);
    else setStatus("pending");
    setError(null);

    generateStory(analysisId, style, regenerate)
      .then((result) => {
        setStory(result);
        setStatus("success");
      })
      .catch((err: unknown) => {
        setError(
          err instanceof StoryApiError
            ? err
            : new StoryApiError("The Cat Universe is taking a nap. Try again soon.", "network"),
        );
        if (!regenerate) setStatus("error");
      })
      .finally(() => setIsRegenerating(false));
  };

  const handleShare = async () => {
    if (!story) return;
    const updated = await shareStory(story.id);
    setStory(updated);
  };

  if (!analysisId) {
    return (
      <div className="mt-6 w-full text-center">
        <Separator className="mb-6" />
        <p className="text-xs text-muted-foreground">
          Story generation needs this analysis to be saved, and we couldn&apos;t reach the
          database just now — everything else above is still fully real.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-6 w-full">
      <Separator className="mb-6" />

      {status !== "success" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <h3 className="font-heading text-lg font-semibold">
            {status === "pending" ? "Writing your cat's story..." : "Your cat's story is waiting..."}
          </h3>

          {status === "pending" ? (
            <StoryLoader />
          ) : (
            <>
              <p className="text-sm text-muted-foreground">Pick a style, then write the story.</p>
              <StoryStyleSelector value={style} onChange={setStyle} />
              {status === "error" && error && (
                <div
                  role="alert"
                  className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
                >
                  <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
                  {error.message}
                </div>
              )}
              <Button onClick={() => generate(false)} className="gap-1.5 rounded-full">
                <Sparkles className="size-4" aria-hidden="true" />
                Write My Cat&apos;s Story
              </Button>
            </>
          )}
        </div>
      )}

      {status === "success" && story && (
        <div className="flex flex-col items-center gap-4">
          <StoryCard
            story={story}
            catImageUrl={catImageUrl}
            onRegenerate={() => generate(true)}
            isRegenerating={isRegenerating}
            onShare={handleShare}
          />
          {error && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
            >
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              {error.message}
            </div>
          )}
          <Button variant="outline" size="sm" className="rounded-full" onClick={() => setStatus("idle")}>
            Try a different style
          </Button>
        </div>
      )}
    </div>
  );
}
