"use client";

import { motion, useReducedMotion } from "framer-motion";
import { toPng } from "html-to-image";
import {
  Bookmark,
  Check,
  Download,
  Heart,
  ImagePlus,
  Link2,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { GuestSavePrompt } from "@/features/auth/components/GuestSavePrompt";
import { pushGamificationEvent } from "@/lib/discovery-toast-store";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";
import { shareAnalysis } from "@/services/analyses";

import { ColorPalette } from "./ColorPalette";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { RarityAura } from "./RarityAura";
import { getRarityVisual } from "../rarity";
import { useCardTilt } from "../use-card-tilt";
import { useCatActions } from "../use-cat-actions";

import type { AnalysisResult } from "@/types/analysis";

function meowverseId(id: string | null): string {
  if (!id) return "UNSAVED";
  return `#${id.replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

interface CatCardProps {
  result: AnalysisResult;
  catImageUrl?: string | null;
  /** True once the reveal sequence has finished — tilt/interaction is
   * held off until then so the card doesn't wobble mid-animation. */
  interactive?: boolean;
  storySectionId?: string;
}

export function CatCard({
  result: initialResult,
  catImageUrl,
  interactive = true,
  storySectionId = "story-section",
}: CatCardProps) {
  const {
    result,
    isGuest,
    showGuestPrompt,
    setShowGuestPrompt,
    handleSaveClick,
    handleToggleFavoriteClick,
    isSaving,
    isTogglingFavorite,
  } = useCatActions(initialResult);
  const { profile } = result;
  // A fresh analysis passes its local blob: preview URL explicitly;
  // any other view (collection, public /cat/[id]) has no such prop, so
  // fall back to the persisted photo from ImageStorageProvider (Phase 9).
  const displayImageUrl = catImageUrl ?? resolveMediaUrl(result.image_url);
  const rarity = getRarityVisual(profile.rarity);
  const reduceMotion = useReducedMotion();
  const tiltRef = useRef<HTMLDivElement>(null);
  const tilt = useCardTilt(tiltRef, interactive);
  const exportRef = useRef<HTMLDivElement>(null);

  const [shareState, setShareState] = useState<"idle" | "sharing" | "copied" | "error">("idle");
  const [downloadState, setDownloadState] = useState<"idle" | "exporting" | "error">("idle");

  async function handleShare() {
    if (isGuest) {
      setShowGuestPrompt(true);
      return;
    }
    if (!result.id || !result.owned) return;
    setShareState("sharing");
    try {
      const shared = await shareAnalysis(result.id);
      pushGamificationEvent(shared.gamification);
      const url = `${window.location.origin}/cat/${result.id}`;
      if (navigator.share) {
        try {
          await navigator.share({ title: `${profile.name} — MeowVerse AI`, url });
          setShareState("idle");
          return;
        } catch {
          // User cancelled the native share sheet, or it's unsupported
          // for this content — clipboard fallback below still runs.
        }
      }
      await navigator.clipboard.writeText(url);
      setShareState("copied");
      setTimeout(() => setShareState("idle"), 2500);
    } catch {
      setShareState("error");
      setTimeout(() => setShareState("idle"), 2500);
    }
  }

  async function handleDownload() {
    if (!exportRef.current) return;
    setDownloadState("exporting");
    try {
      // No `cacheBust` — it appends a `?timestamp` query string to every
      // <img> src to force a fresh fetch, but the cat photo's src is a
      // blob: URL, which doesn't support query strings at all (appending
      // one produces an unresolvable URL and the whole export throws).
      // Not needed anyway: this is a one-shot export of a freshly
      // rendered card, not a repeatedly-reused cached node.
      const dataUrl = await toPng(exportRef.current, {
        pixelRatio: 2,
        backgroundColor: undefined,
      });
      if (!dataUrl || dataUrl === "data:,") throw new Error("Empty export");
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `${profile.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "cat-card"}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setDownloadState("idle");
    } catch {
      setDownloadState("error");
      setTimeout(() => setDownloadState("idle"), 3000);
    }
  }

  function handleGenerateStoryClick() {
    document
      .getElementById(storySectionId)
      ?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  }

  return (
    <div className="relative w-full max-w-sm">
      <RarityAura treatment={rarity.treatment} />

      <motion.div
        ref={tiltRef}
        {...tilt.handlers}
        style={tilt.style}
        whileTap={reduceMotion ? undefined : { scale: 0.98 }}
        className="relative"
      >
        <div
          ref={exportRef}
          className={cn(
            "relative overflow-hidden rounded-3xl p-6 text-center",
            rarity.cardClassName,
          )}
        >
          <div className="flex items-center justify-between">
            <Badge className={cn("gap-1", rarity.badgeClassName)}>{profile.rarity}</Badge>
            <span
              className="font-mono text-[10px] tracking-wider text-muted-foreground"
              title="MeowVerse ID"
            >
              {meowverseId(result.id)}
            </span>
          </div>

          <div className="mx-auto mt-4 flex aspect-square w-40 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-magic-200 to-peach-200 text-5xl dark:from-magic-900/60 dark:to-peach-900/40">
            {displayImageUrl ? (
              // Card export needs a plain <img>, not next/image's
              // runtime-optimized one (which would break html-to-image's
              // DOM snapshot). The src is either a same-origin blob: URL
              // (fresh analysis) or the backend's /media/... URL (any
              // other view) — the latter relies on the backend's CORS
              // config allowing the frontend origin, same as every other
              // API call.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={displayImageUrl} alt="" className="size-full object-cover" />
            ) : (
              <span aria-hidden="true">🐱</span>
            )}
          </div>

          <div className="mt-4">
            <h2 className="font-heading text-2xl font-bold">{profile.name}</h2>
            <p className="text-sm italic text-muted-foreground">&ldquo;{profile.title}&rdquo;</p>
          </div>

          {result.breed && (
            <p className="mt-1 text-sm text-muted-foreground">{result.breed.label}</p>
          )}

          {/* Plain text, not a Badge — magic_power can be a full sentence
           * and Badge's whitespace-nowrap silently clipped long ones. */}
          <p className="mt-4 flex items-start justify-center gap-1.5 text-sm text-magic-700 dark:text-magic-300">
            <Sparkles className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span>{profile.magic_power}</span>
          </p>

          <p className="mt-3 text-sm">{profile.personality}</p>

          {result.breed && (
            <div className="mt-4 text-left">
              <ConfidenceMeter confidence={result.breed.confidence} />
            </div>
          )}

          {result.colors.length > 0 && (
            <>
              <Separator className="my-4" />
              <div className="text-left">
                <p className="mb-2 text-xs text-muted-foreground">Fur palette</p>
                <ColorPalette colors={result.colors} />
              </div>
            </>
          )}

          <Separator className="my-4" />
          <p className="text-sm text-muted-foreground">{profile.description}</p>
        </div>
      </motion.div>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSaveClick}
          disabled={result.owned || isSaving}
          aria-pressed={result.owned}
          className="gap-1.5"
        >
          <Bookmark
            className={cn("size-4", result.owned && "fill-magic-500 text-magic-500")}
            aria-hidden="true"
          />
          {result.owned ? "Saved" : isSaving ? "Saving..." : "Save"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleToggleFavoriteClick}
          disabled={(!isGuest && !result.owned) || isTogglingFavorite}
          aria-pressed={result.is_favorite}
          title={!isGuest && !result.owned ? "Save this cat first" : undefined}
          className="gap-1.5"
        >
          <Heart
            className={cn("size-4", result.is_favorite && "fill-destructive text-destructive")}
            aria-hidden="true"
          />
          {result.is_favorite ? "Favorited" : "Favorite"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleShare}
          disabled={!result.id || shareState === "sharing" || (!isGuest && !result.owned)}
          title={!isGuest && !result.owned ? "Save this cat first" : undefined}
          className="gap-1.5"
        >
          {shareState === "copied" ? (
            <Check className="size-4" aria-hidden="true" />
          ) : (
            <Link2 className="size-4" aria-hidden="true" />
          )}
          {shareState === "copied"
            ? "Link copied!"
            : shareState === "sharing"
              ? "Sharing..."
              : shareState === "error"
                ? "Couldn't share"
                : "Share"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDownload}
          disabled={downloadState === "exporting"}
          className="gap-1.5"
        >
          {downloadState === "exporting" ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="size-4" aria-hidden="true" />
          )}
          {downloadState === "error" ? "Download failed" : "Download PNG"}
        </Button>
        <Button variant="ghost" size="sm" onClick={handleGenerateStoryClick} className="gap-1.5">
          <Sparkles className="size-4" aria-hidden="true" />
          Story
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled
          title="Coming in a future update"
          className="gap-1.5"
        >
          <ImagePlus className="size-4" aria-hidden="true" />
          Wallpaper
        </Button>
      </div>

      <GuestSavePrompt open={showGuestPrompt} onOpenChange={setShowGuestPrompt} />
    </div>
  );
}
