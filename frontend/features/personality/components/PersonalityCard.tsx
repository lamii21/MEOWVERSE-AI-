"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, RefreshCw, Sparkles } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PersonalityApiError, fetchPersonality, regeneratePersonality } from "@/services/personality";

import { getArchetypeTheme } from "../archetype-theme";
import { HowPersonalityWorks } from "./HowPersonalityWorks";
import { PersonalityReveal } from "./PersonalityReveal";
import { TraitBar } from "./TraitBar";

import type { AnalysisResult } from "@/types/analysis";

interface PersonalityCardProps {
  result: AnalysisResult;
}

/**
 * The Phase 13 Cat Personality Engine's frontend home — auto-loads
 * (like "Cats Like This", unlike Grad-CAM's manual "Why this breed?"
 * trigger, since a personality read is cheap and central to the
 * product's identity) via `useQuery`, shows the reveal sequence while
 * waiting, then a collectible card. "Regenerate" only ever replaces
 * `interpretation` — the query cache is updated with the *server's*
 * full response (traits/archetype included), and the backend itself
 * guarantees those never change on a regenerate call, so there's
 * nothing for the frontend to accidentally diverge on.
 */
export function PersonalityCard({ result }: PersonalityCardProps) {
  const exportRef = useRef<HTMLDivElement>(null);
  const [downloadState, setDownloadState] = useState<"idle" | "exporting" | "error">("idle");
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["personality", result.id],
    queryFn: () => fetchPersonality(result.id as string),
    enabled: result.id !== null,
  });

  const regenerateMutation = useMutation({
    mutationFn: () => regeneratePersonality(result.id as string),
    onSuccess: (data) => {
      queryClient.setQueryData(["personality", result.id], data);
    },
  });

  if (result.id === null || !result.breed) return null;

  async function handleDownload() {
    if (!exportRef.current) return;
    setDownloadState("exporting");
    try {
      // Same one-shot export technique as CatCard.tsx — no `cacheBust`
      // (breaks blob: URLs), reused rather than a second export pipeline.
      const dataUrl = await toPng(exportRef.current, { pixelRatio: 2, backgroundColor: undefined });
      if (!dataUrl || dataUrl === "data:,") throw new Error("Empty export");
      const a = document.createElement("a");
      const archetypeName = query.data?.archetype.name ?? "cat-personality";
      a.href = dataUrl;
      a.download = `${archetypeName.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setDownloadState("idle");
    } catch {
      setDownloadState("error");
      setTimeout(() => setDownloadState("idle"), 3000);
    }
  }

  const personality = query.data;
  const theme = personality ? getArchetypeTheme(personality.archetype.theme_token) : null;

  return (
    <section className="mx-auto mt-10 w-full max-w-md px-4 text-center sm:px-6">
      <h2 className="font-heading text-xl font-bold">Cat Personality</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        An AI-inspired personality built from this cat&apos;s real visual signals.
      </p>

      {query.isLoading && <PersonalityReveal />}

      {query.isError && (
        <p className="mt-6 text-sm text-destructive" role="alert">
          {query.error instanceof PersonalityApiError
            ? query.error.message
            : "The Cat Universe is taking a nap. Try again soon."}
        </p>
      )}

      {personality && theme && (
        <>
          <div
            ref={exportRef}
            className={cn("mt-6 rounded-3xl p-6 text-center", theme.cardClassName)}
          >
            <Badge className={cn("mx-auto gap-1", theme.badgeClassName)}>
              <Sparkles className="size-3" aria-hidden="true" />
              {personality.interpretation_mode === "generated"
                ? "AI-generated"
                : "Offline demo content"}
            </Badge>

            <p className="mt-3 text-4xl" aria-hidden="true">
              {personality.archetype.emoji}
            </p>
            <h3 className="mt-1 font-heading text-2xl font-bold uppercase tracking-wide">
              {personality.archetype.name}
            </h3>
            <p className="mt-1 text-sm italic text-muted-foreground">
              &ldquo;{personality.interpretation.catchphrase}&rdquo;
            </p>

            <p className="mt-4 text-sm font-medium">{personality.interpretation.headline}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {personality.interpretation.description}
            </p>

            <div className="mt-5 flex flex-col gap-3 text-left">
              {Object.entries(personality.traits).map(([name, trait]) => (
                <TraitBar key={name} name={name} trait={trait} />
              ))}
            </div>

            <dl className="mt-5 flex flex-col gap-3 text-left text-sm">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Secret talent
                </dt>
                <dd className="mt-0.5">{personality.interpretation.secret_talent}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Fictional job
                </dt>
                <dd className="mt-0.5">{personality.interpretation.fictional_job}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Fun fact
                </dt>
                <dd className="mt-0.5">{personality.interpretation.fun_fact}</dd>
              </div>
            </dl>

            <p className="mt-5 text-xs text-muted-foreground">{personality.disclaimer}</p>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            {result.owned && (
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5"
                onClick={() => regenerateMutation.mutate()}
                disabled={regenerateMutation.isPending}
              >
                <RefreshCw
                  className={cn("size-4", regenerateMutation.isPending && "animate-spin")}
                  aria-hidden="true"
                />
                {regenerateMutation.isPending ? "Regenerating..." : "Regenerate"}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5"
              onClick={handleDownload}
              disabled={downloadState === "exporting"}
            >
              <Download className="size-4" aria-hidden="true" />
              {downloadState === "error" ? "Download failed" : "Download PNG"}
            </Button>
          </div>

          <HowPersonalityWorks />
        </>
      )}
    </section>
  );
}
