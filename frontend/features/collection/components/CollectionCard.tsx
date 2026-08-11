"use client";

import { BookOpen, Heart } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { getRarityVisual } from "@/features/results/rarity";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";

import type { AnalysisResult } from "@/types/analysis";

function formatDiscoveryDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/**
 * A compact gallery tile — the full CatCard (stats, palette, action
 * row) is the right amount of detail for *one* cat's own page, but far
 * too heavy repeated dozens of times in a grid. Reuses the same rarity
 * visual config as CatCard so a Legendary cat still reads as
 * Legendary at a glance in the collection view.
 */
export function CollectionCard({ result }: { result: AnalysisResult }) {
  const rarity = getRarityVisual(result.profile.rarity);

  return (
    <Link
      href={`/collection/${result.id}`}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-2xl p-4 text-left transition-transform hover:-translate-y-0.5",
        rarity.cardClassName,
      )}
    >
      <div className="absolute right-3 top-3 flex items-center gap-1">
        {result.has_story && (
          <BookOpen className="size-3.5 text-muted-foreground" aria-label="Has a story" />
        )}
        {result.is_favorite && (
          <Heart className="size-4 fill-destructive text-destructive" aria-label="Favorited" />
        )}
      </div>
      <div className="mx-auto flex aspect-square w-full max-w-28 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-magic-200 to-peach-200 text-3xl dark:from-magic-900/60 dark:to-peach-900/40">
        {result.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={resolveMediaUrl(result.image_url) ?? undefined}
            alt=""
            className="size-full object-cover"
          />
        ) : (
          <span aria-hidden="true">🐱</span>
        )}
      </div>
      <p className="mt-3 truncate text-center font-heading text-sm font-semibold">
        {result.profile.name}
      </p>
      {result.breed && (
        <p className="truncate text-center text-xs text-muted-foreground">{result.breed.label}</p>
      )}
      <Badge className={cn("mx-auto mt-2 gap-1", rarity.badgeClassName)}>
        {result.profile.rarity}
      </Badge>
      {result.created_at && (
        <p className="mt-1 text-center text-[10px] text-muted-foreground">
          Discovered {formatDiscoveryDate(result.created_at)}
        </p>
      )}
    </Link>
  );
}
