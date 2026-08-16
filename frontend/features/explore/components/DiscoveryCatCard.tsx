import { BookOpen, Sparkles } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { getRarityVisual } from "@/features/results/rarity";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";

import type { DiscoveryCat } from "@/types/explore";

/**
 * A public discovery tile (Phase 15 spec §5) — the same compact-gallery
 * shape as `CollectionCard`, reusing the exact rarity visual language,
 * but built from `DiscoveryCat` (never `AnalysisResult`) so there is no
 * field to accidentally render that shouldn't be public (no owner
 * identity, no internal ids beyond the analysis id already used in the
 * public `/cat/[id]` URL).
 */
export function DiscoveryCatCard({ cat }: { cat: DiscoveryCat }) {
  const rarity = getRarityVisual(cat.rarity);

  return (
    <Link
      href={`/cat/${cat.analysis_id}`}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-2xl p-4 text-left transition-transform hover:-translate-y-0.5",
        rarity.cardClassName,
      )}
    >
      <div className="absolute right-3 top-3 flex items-center gap-1">
        {cat.has_public_portrait && (
          <Sparkles className="size-3.5 text-muted-foreground" aria-label="Has an AI portrait" />
        )}
        {cat.has_public_story && (
          <BookOpen className="size-3.5 text-muted-foreground" aria-label="Has a story" />
        )}
      </div>
      <div className="mx-auto flex aspect-square w-full max-w-28 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-magic-200 to-peach-200 text-3xl dark:from-magic-900/60 dark:to-peach-900/40">
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
      <p className="mt-3 truncate text-center font-heading text-sm font-semibold">
        {cat.cat_name}
      </p>
      {cat.breed && (
        <p className="truncate text-center text-xs text-muted-foreground">{cat.breed.label}</p>
      )}
      <p className="mt-1 truncate text-center text-xs text-muted-foreground">
        <span aria-hidden="true">{cat.archetype_emoji}</span> {cat.archetype_name}
      </p>
      <Badge className={cn("mx-auto mt-2 gap-1", rarity.badgeClassName)}>{cat.rarity}</Badge>
    </Link>
  );
}
