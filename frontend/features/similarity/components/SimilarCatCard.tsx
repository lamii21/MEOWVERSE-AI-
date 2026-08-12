"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { getRarityVisual } from "@/features/results/rarity";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";

import type { SimilarCat } from "@/types/similarity";
import type { Rarity } from "@/types/analysis";

/** A compact result tile for "Cats Like This" — same rarity visual
 * language as `CollectionCard`, plus the one thing that's unique to a
 * similarity result: the visual-similarity percentage itself. */
export function SimilarCatCard({ cat }: { cat: SimilarCat }) {
  const rarity = getRarityVisual(cat.rarity as Rarity);
  const percent = Math.round(cat.visual_similarity * 100);

  return (
    <Link
      href={`/cat/${cat.analysis_id}`}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-2xl p-4 text-left transition-transform hover:-translate-y-0.5",
        rarity.cardClassName,
      )}
    >
      <div className="mx-auto flex aspect-square w-full max-w-24 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-magic-200 to-peach-200 text-2xl dark:from-magic-900/60 dark:to-peach-900/40">
        {cat.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={resolveMediaUrl(cat.image_url) ?? undefined}
            alt=""
            className="size-full object-cover"
          />
        ) : (
          <span aria-hidden="true">🐱</span>
        )}
      </div>
      <p className="mt-2 truncate text-center font-heading text-sm font-semibold">
        {cat.cat_name}
      </p>
      {cat.breed && (
        <p className="truncate text-center text-xs text-muted-foreground">{cat.breed.label}</p>
      )}
      <Badge className={cn("mx-auto mt-2 gap-1", rarity.badgeClassName)}>{cat.rarity}</Badge>
      <p className="mt-1.5 text-center text-xs font-medium text-magic-600 dark:text-magic-300">
        {percent}% visually similar
      </p>
    </Link>
  );
}
