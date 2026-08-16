import { cn } from "@/lib/utils";

import type { Rarity } from "@/types/analysis";

const RARITIES: Rarity[] = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"];

export interface DiscoveryQuickFilter {
  rarity: Rarity | null;
  hasStory: boolean;
  hasPortrait: boolean;
}

const RARITY_CHIPS: { value: Rarity | null; label: string }[] = [
  { value: null, label: "All" },
  ...RARITIES.map((r) => ({ value: r, label: r })),
];

/** The quick filter bar (Phase 15 spec §6/§8) — a small, cute set of
 * chips, not a dropdown-heavy filter panel. Breed/personality/color
 * filtering happens by clicking an entry in the dedicated Breed/
 * Personality/Color Explorer sections below, which feels like
 * *discovering* a category rather than configuring a form. */
export function DiscoveryFilters({
  value,
  onChange,
}: {
  value: DiscoveryQuickFilter;
  onChange: (next: DiscoveryQuickFilter) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div role="radiogroup" aria-label="Filter by rarity" className="flex flex-wrap gap-2">
        {RARITY_CHIPS.map((chip) => (
          <button
            key={chip.label}
            type="button"
            role="radio"
            aria-checked={value.rarity === chip.value}
            onClick={() => onChange({ ...value, rarity: chip.value })}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              value.rarity === chip.value
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {chip.label}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          aria-pressed={value.hasStory}
          onClick={() => onChange({ ...value, hasStory: !value.hasStory })}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
            value.hasStory
              ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          📖 Has story
        </button>
        <button
          type="button"
          aria-pressed={value.hasPortrait}
          onClick={() => onChange({ ...value, hasPortrait: !value.hasPortrait })}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
            value.hasPortrait
              ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          🎨 Has AI portrait
        </button>
      </div>
    </div>
  );
}
