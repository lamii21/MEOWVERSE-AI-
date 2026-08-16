"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchColorExplorer } from "@/services/explore";
import { cn } from "@/lib/utils";

/** Color Explorer (Phase 15 spec §14) — groups public cats by their
 * real analyzed dominant fur color (Phase 5), never a second/invented
 * color classification. */
export function DiscoveryColorExplorer({
  selected,
  onSelect,
}: {
  selected: string | null;
  onSelect: (color: string | null) => void;
}) {
  const query = useQuery({ queryKey: ["explore", "colors"], queryFn: fetchColorExplorer });

  if (query.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading colors...</p>;
  }
  if (query.isError || !query.data || query.data.length === 0) return null;

  return (
    <section aria-labelledby="color-explorer-heading">
      <h2 id="color-explorer-heading" className="font-heading text-xl font-bold">
        Discover by Color
      </h2>
      <div role="radiogroup" aria-label="Filter by fur color" className="mt-3 flex flex-wrap gap-2">
        {query.data.map((entry) => (
          <button
            key={entry.color_name}
            type="button"
            role="radio"
            aria-checked={selected === entry.color_name}
            onClick={() => onSelect(selected === entry.color_name ? null : entry.color_name)}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              selected === entry.color_name
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            <span
              className="size-3 rounded-full border border-border"
              style={{ backgroundColor: entry.hex }}
              aria-hidden="true"
            />
            {entry.color_name}
            <span className="text-muted-foreground">({entry.public_count})</span>
          </button>
        ))}
      </div>
    </section>
  );
}
