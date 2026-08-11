import type { Rarity } from "@/types/analysis";

export type RarityTreatment = "plain" | "tint" | "shimmer" | "glow" | "aura" | "particles";

export interface RarityVisual {
  /** 1 = most common, 6 = rarest — drives ordering, not just display. */
  tier: number;
  treatment: RarityTreatment;
  /** Card surface + ring classes. */
  cardClassName: string;
  /** Small rarity pill classes. */
  badgeClassName: string;
}

/**
 * Rarity is a playful game mechanic (spec §5), never a scientific
 * measurement — the visual difference is deliberately subtle and
 * premium, not flashy. Each tier is a strict superset of the previous
 * one's polish: Common is a plain matte card, Mythical adds the most
 * (but still restrained) visual interest.
 */
export const RARITY_VISUALS: Record<Rarity, RarityVisual> = {
  Common: {
    tier: 1,
    treatment: "plain",
    cardClassName: "bg-card ring-1 ring-border",
    badgeClassName: "bg-muted text-muted-foreground",
  },
  Uncommon: {
    tier: 2,
    treatment: "tint",
    cardClassName:
      "bg-gradient-to-b from-sky-50 to-card ring-1 ring-sky-300/70 dark:from-sky-950/40 dark:ring-sky-400/30",
    badgeClassName: "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-200",
  },
  Rare: {
    tier: 3,
    treatment: "shimmer",
    cardClassName:
      "bg-gradient-to-b from-magic-50 to-card ring-1 ring-magic-300/70 dark:from-magic-950/40 dark:ring-magic-400/30",
    badgeClassName: "bg-magic-100 text-magic-700 dark:bg-magic-900/50 dark:text-magic-200",
  },
  Epic: {
    tier: 4,
    treatment: "glow",
    cardClassName:
      "bg-gradient-to-br from-magic-100 via-peach-50 to-magic-50 ring-2 ring-magic-400/60 shadow-[0_0_45px_-12px_var(--color-magic-400)] dark:from-magic-900/50 dark:via-peach-950/30 dark:to-magic-950/40",
    badgeClassName:
      "bg-gradient-to-r from-magic-500 to-peach-500 text-white dark:from-magic-400 dark:to-peach-400",
  },
  Legendary: {
    tier: 5,
    treatment: "aura",
    cardClassName:
      "bg-gradient-to-br from-peach-100 via-magic-50 to-peach-50 ring-2 ring-peach-400/70 dark:from-peach-900/40 dark:via-magic-950/30 dark:to-peach-950/30",
    badgeClassName:
      "bg-gradient-to-r from-peach-500 via-magic-500 to-peach-500 text-white bg-[length:200%_auto]",
  },
  Mythical: {
    tier: 6,
    treatment: "particles",
    cardClassName:
      "bg-gradient-to-br from-magic-100 via-peach-100 to-sky-50 ring-2 ring-magic-400/70 shadow-[0_0_55px_-10px_var(--color-magic-400)] dark:from-magic-900/50 dark:via-peach-950/30 dark:to-sky-950/30",
    badgeClassName:
      "bg-gradient-to-r from-magic-500 via-peach-500 to-magic-500 text-white bg-[length:200%_auto]",
  },
};

export function getRarityVisual(rarity: Rarity): RarityVisual {
  return RARITY_VISUALS[rarity] ?? RARITY_VISUALS.Common;
}
