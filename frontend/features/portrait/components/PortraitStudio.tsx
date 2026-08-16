"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { resolveMediaUrl } from "@/lib/media";
import { PortraitApiError, fetchPortraits, generatePortrait } from "@/services/portrait";

import { PortraitCard } from "./PortraitCard";
import { PortraitReveal } from "./PortraitReveal";
import { StyleSelector } from "./StyleSelector";

import type { AnalysisResult } from "@/types/analysis";
import type { CatPortrait, PortraitStyleId } from "@/types/portrait";

const MAX_CUSTOMIZATION = 120;

const UNAVAILABLE_MESSAGES: Record<string, string> = {
  provider_unavailable:
    "Portrait generation is currently unavailable — no image-generation provider is configured in this environment.",
  rate_limited: "Too many portraits requested — please wait a moment and try again.",
  content_rejected:
    "This portrait couldn't be generated (it may have been flagged by content safety filters). Try a different style or idea.",
  timeout: "The portrait studio took too long to respond. Please try again.",
  network_error: "Couldn't reach the portrait studio. Please check your connection and try again.",
  source_image_unavailable: "The original photo isn't available for this cat right now.",
  storage_failed: "The portrait was generated but couldn't be saved. Please try again.",
  invalid_output: "The generated image didn't come back looking right. Please try again.",
  provider_error: "The portrait studio ran into a problem. Please try again.",
};

/**
 * "AI Cat Portrait Studio" (Phase 14) — auto-loads existing portraits
 * for this cat (like "Cats Like This"), but generation itself is
 * always an explicit, manually-triggered action (like Grad-CAM's "Why
 * this breed?" and Story's "Write My Cat's Story") — a real image
 * generation call is expensive and must never run automatically.
 */
export function PortraitStudio({
  result,
  catImageUrl,
}: {
  result: AnalysisResult;
  catImageUrl?: string | null;
}) {
  const [style, setStyle] = useState<PortraitStyleId>("royal");
  const [customization, setCustomization] = useState("");
  const [regeneratingStyle, setRegeneratingStyle] = useState<PortraitStyleId | null>(null);
  const queryClient = useQueryClient();

  const analysisId = result.id as string;
  const query = useQuery({
    queryKey: ["portraits", analysisId],
    queryFn: () => fetchPortraits(analysisId),
    enabled: result.id !== null,
  });

  const mutation = useMutation({
    mutationFn: ({ style: s, forceNew }: { style: PortraitStyleId; forceNew: boolean }) =>
      generatePortrait(analysisId, s, customization, forceNew),
    onSuccess: (portrait) => {
      queryClient.setQueryData(["portraits", analysisId], (prev: { portraits: CatPortrait[] } | undefined) => {
        const existing = prev?.portraits ?? [];
        const withoutThisOne = existing.filter((p) => p.id !== portrait.id);
        return { portraits: [portrait, ...withoutThisOne] };
      });
      setRegeneratingStyle(null);
    },
    onError: () => setRegeneratingStyle(null),
  });

  if (result.id === null || !result.breed) return null;

  const displayImageUrl = catImageUrl ?? resolveMediaUrl(result.image_url);
  const portraits = query.data?.portraits ?? [];
  const succeeded = portraits.filter((p) => p.status === "succeeded");
  const failedResult = mutation.data?.status === "failed" ? mutation.data : null;

  function handleGenerate() {
    mutation.mutate({ style, forceNew: false });
  }

  function handleGenerateAgain(portraitStyle: PortraitStyleId) {
    setRegeneratingStyle(portraitStyle);
    mutation.mutate({ style: portraitStyle, forceNew: true });
  }

  return (
    <section className="mx-auto mt-10 w-full max-w-md px-4 text-center sm:px-6">
      <h2 className="font-heading text-xl font-bold">Portrait Studio ✨</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Turn {result.profile.name} into a beautiful artistic portrait, styled from their real
        reference photo.
      </p>

      {result.owned && (
        <div className="mt-5 flex flex-col gap-3">
          <StyleSelector value={style} onChange={setStyle} disabled={mutation.isPending} />

          <div className="text-left">
            <Label htmlFor="portrait-customization">Add something special (optional)</Label>
            <Input
              id="portrait-customization"
              value={customization}
              onChange={(e) => setCustomization(e.target.value.slice(0, MAX_CUSTOMIZATION))}
              maxLength={MAX_CUSTOMIZATION}
              placeholder={`Put ${result.profile.name} in a moonlit library...`}
              disabled={mutation.isPending}
              className="mt-1"
            />
            <p className="mt-1 text-right text-xs text-muted-foreground">
              {customization.length}/{MAX_CUSTOMIZATION}
            </p>
          </div>

          <Button
            className="gap-1.5 self-center rounded-full"
            onClick={handleGenerate}
            disabled={mutation.isPending}
          >
            <Sparkles className="size-4" aria-hidden="true" />
            {mutation.isPending && !regeneratingStyle ? "Generating..." : "✨ Generate ✨"}
          </Button>
        </div>
      )}

      {mutation.isPending && <PortraitReveal />}

      {mutation.isError && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {mutation.error instanceof PortraitApiError
            ? mutation.error.message
            : "The Cat Universe is taking a nap. Try again soon."}
        </p>
      )}

      {failedResult && (
        <div
          className="mt-4 rounded-2xl border border-border p-4 text-sm text-muted-foreground"
          role="alert"
        >
          <p className="font-medium text-foreground">Couldn&apos;t create this portrait</p>
          <p className="mt-1">
            {(failedResult.error_code && UNAVAILABLE_MESSAGES[failedResult.error_code]) ||
              failedResult.error_message ||
              "Something went wrong."}
          </p>
        </div>
      )}

      {query.isLoading && result.owned === false && (
        <p className="mt-4 text-sm text-muted-foreground">Loading portraits...</p>
      )}

      {succeeded.length > 0 && (
        <div className="mt-6 flex flex-col gap-6">
          {succeeded.map((portrait) => (
            <PortraitCard
              key={portrait.id}
              portrait={portrait}
              catName={result.profile.name}
              originalImageUrl={displayImageUrl ?? null}
              onGenerateAgain={() => handleGenerateAgain(portrait.style)}
              isGeneratingAgain={mutation.isPending && regeneratingStyle === portrait.style}
            />
          ))}
        </div>
      )}

      {!result.owned && succeeded.length === 0 && !query.isLoading && (
        <p className="mt-4 text-sm text-muted-foreground">No portraits shared for this cat yet.</p>
      )}
    </section>
  );
}
