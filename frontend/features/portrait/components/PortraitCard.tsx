"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, RefreshCw, Share2, Sparkles } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PortraitApiError, sharePortrait } from "@/services/portrait";

import { BeforeAfterViewer } from "./BeforeAfterViewer";

import type { CatPortrait } from "@/types/portrait";

/** One generated portrait, shown as a collectible card (Phase 14 spec
 * §32-33) — always carrying an explicit "AI-generated artwork" label,
 * never presented as an actual photograph. Reuses `CatCard`'s exact
 * PNG export technique (no second export pipeline, spec §34) and the
 * existing `/share` endpoint (spec §35) rather than inventing a new
 * mechanism for either. */
export function PortraitCard({
  portrait,
  catName,
  originalImageUrl,
  onGenerateAgain,
  isGeneratingAgain,
}: {
  portrait: CatPortrait;
  catName: string;
  originalImageUrl: string | null;
  onGenerateAgain: () => void;
  isGeneratingAgain: boolean;
}) {
  const exportRef = useRef<HTMLDivElement>(null);
  const [downloadState, setDownloadState] = useState<"idle" | "exporting" | "error">("idle");
  const [shareState, setShareState] = useState<"idle" | "copied" | "error">("idle");
  const queryClient = useQueryClient();

  const shareMutation = useMutation({
    mutationFn: () => sharePortrait(portrait.id),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["portrait", portrait.id], updated);
      const url = `${window.location.origin}/portrait/${updated.id}`;
      try {
        if (navigator.share) {
          await navigator.share({ title: `${catName}'s AI portrait`, url });
        } else {
          await navigator.clipboard.writeText(url);
          setShareState("copied");
          setTimeout(() => setShareState("idle"), 3000);
        }
      } catch {
        // A cancelled native share sheet isn't an error.
      }
    },
    onError: () => {
      setShareState("error");
      setTimeout(() => setShareState("idle"), 3000);
    },
  });

  async function handleDownload() {
    if (!exportRef.current) return;
    setDownloadState("exporting");
    try {
      const dataUrl = await toPng(exportRef.current, { pixelRatio: 2, backgroundColor: undefined });
      if (!dataUrl || dataUrl === "data:,") throw new Error("Empty export");
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `${catName.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-${portrait.style}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setDownloadState("idle");
    } catch {
      setDownloadState("error");
      setTimeout(() => setDownloadState("idle"), 3000);
    }
  }

  if (portrait.status !== "succeeded" || !portrait.image_url) return null;

  return (
    <div className="mx-auto w-full max-w-xs">
      <div ref={exportRef} className="glass rounded-3xl p-4 text-center">
        <Badge className="mx-auto gap-1 bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200">
          <Sparkles className="size-3" aria-hidden="true" />
          AI-generated artwork
        </Badge>

        <p className="mt-2 text-lg" aria-hidden="true">
          {portrait.style_emoji}
        </p>
        <h3 className="font-heading text-lg font-bold">{portrait.style_name}</h3>

        <div className="mt-3">
          <BeforeAfterViewer
            originalUrl={originalImageUrl}
            portraitUrl={portrait.image_url}
            catName={catName}
            styleName={portrait.style_name}
          />
        </div>

        <p className="mt-3 text-xs text-muted-foreground">
          An AI-generated artistic interpretation based on {catName}&apos;s reference photo — not
          an actual photograph, and not a claim of perfect likeness.
        </p>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
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
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5"
          onClick={() => shareMutation.mutate()}
          disabled={shareMutation.isPending}
        >
          <Share2 className="size-4" aria-hidden="true" />
          {shareState === "copied"
            ? "Link copied!"
            : shareState === "error"
              ? "Share failed"
              : "Share"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5"
          onClick={onGenerateAgain}
          disabled={isGeneratingAgain}
        >
          <RefreshCw
            className={cn("size-4", isGeneratingAgain && "animate-spin")}
            aria-hidden="true"
          />
          {isGeneratingAgain ? "Generating..." : "Generate Again"}
        </Button>
      </div>
      {shareMutation.isError && (
        <p className="mt-2 text-xs text-destructive" role="alert">
          {shareMutation.error instanceof PortraitApiError
            ? shareMutation.error.message
            : "Couldn't share this portrait right now."}
        </p>
      )}
    </div>
  );
}
