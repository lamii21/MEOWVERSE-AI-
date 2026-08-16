"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchBreedExplorer } from "@/services/explore";
import { cn } from "@/lib/utils";

/** Breed Explorer (Phase 15 spec §12) — reuses the Phase 10 canonical
 * breed catalog, merged with real *public*-cat counts only (never the
 * owner-scoped counts Phase 10's own Breed Explorer shows). Clicking a
 * breed filters the main discovery grid rather than navigating away —
 * browsing should feel exploratory, not like filling out a form. */
export function DiscoveryBreedExplorer({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (breed: string | null) => void;
}) {
  const query = useQuery({ queryKey: ["explore", "breeds"], queryFn: fetchBreedExplorer });

  if (query.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading breeds...</p>;
  }
  if (query.isError || !query.data) return null;

  return (
    <section aria-labelledby="breed-explorer-heading">
      <h2 id="breed-explorer-heading" className="font-heading text-xl font-bold">
        Discover by Breed
      </h2>
      <div role="radiogroup" aria-label="Filter by breed" className="mt-3 flex flex-wrap gap-2">
        {query.data.map((entry) => (
          <button
            key={entry.breed}
            type="button"
            role="radio"
            aria-checked={selected === entry.breed}
            disabled={entry.public_count === 0}
            onClick={() => onSelect(selected === entry.breed ? null : entry.breed)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40",
              selected === entry.breed
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {entry.breed} <span className="text-muted-foreground">({entry.public_count})</span>
          </button>
        ))}
      </div>
    </section>
  );
}
