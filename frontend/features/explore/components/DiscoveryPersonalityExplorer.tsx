"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchPersonalityExplorer } from "@/services/explore";
import { cn } from "@/lib/utils";

/** Personality Explorer (Phase 15 spec §13) — the 10 Phase 13
 * archetypes with real public-cat counts. Never presented as a
 * scientific classification (each entry's own disclaimer is shown). */
export function DiscoveryPersonalityExplorer({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (archetypeId: string | null) => void;
}) {
  const query = useQuery({
    queryKey: ["explore", "personalities"],
    queryFn: fetchPersonalityExplorer,
  });

  if (query.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading personalities...</p>;
  }
  if (query.isError || !query.data) return null;

  return (
    <section aria-labelledby="personality-explorer-heading">
      <h2 id="personality-explorer-heading" className="font-heading text-xl font-bold">
        Discover by Personality
      </h2>
      <div
        role="radiogroup"
        aria-label="Filter by personality archetype"
        className="mt-3 flex flex-wrap gap-2"
      >
        {query.data.map((archetype) => (
          <button
            key={archetype.id}
            type="button"
            role="radio"
            aria-checked={selected === archetype.id}
            disabled={archetype.public_count === 0}
            onClick={() => onSelect(selected === archetype.id ? null : archetype.id)}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
              selected === archetype.id
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <span aria-hidden="true">{archetype.emoji}</span>
            {archetype.name}
            <span className="text-muted-foreground">({archetype.public_count})</span>
          </button>
        ))}
      </div>
      {query.data[0] && (
        <p className="mt-2 text-xs text-muted-foreground">{query.data[0].disclaimer}</p>
      )}
    </section>
  );
}
