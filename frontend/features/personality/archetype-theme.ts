/** Maps each archetype's `theme_token` (from the backend's
 * `PersonalityArchetype.theme_token`) to a visual treatment — built
 * entirely from the existing `magic`/`peach` design-system scale plus
 * standard Tailwind colors already used elsewhere in this codebase
 * (`sky`/`slate`, e.g. `rarity.ts`'s Uncommon tier and
 * `CollectionMap`'s starfield) — never a new, arbitrary color (Phase
 * 13 spec §41). Falls back to a plain, safe default for any
 * unrecognized token so a future archetype never renders unstyled. */
export interface ArchetypeTheme {
  cardClassName: string;
  badgeClassName: string;
}

const DEFAULT_THEME: ArchetypeTheme = {
  cardClassName: "bg-card ring-1 ring-border",
  badgeClassName: "bg-muted text-muted-foreground",
};

export const ARCHETYPE_THEMES: Record<string, ArchetypeTheme> = {
  dreamy: {
    cardClassName:
      "bg-gradient-to-br from-magic-50 to-sky-50 ring-1 ring-magic-300/60 dark:from-magic-950/40 dark:to-sky-950/30",
    badgeClassName: "bg-magic-100 text-magic-700 dark:bg-magic-900/50 dark:text-magic-200",
  },
  cozy: {
    cardClassName:
      "bg-gradient-to-br from-peach-50 to-magic-50 ring-1 ring-peach-300/60 dark:from-peach-950/40 dark:to-magic-950/30",
    badgeClassName: "bg-peach-100 text-peach-700 dark:bg-peach-900/50 dark:text-peach-200",
  },
  mischief: {
    cardClassName:
      "bg-gradient-to-br from-magic-100 via-peach-50 to-magic-50 ring-2 ring-magic-400/60 dark:from-magic-900/50 dark:via-peach-950/30",
    badgeClassName: "bg-gradient-to-r from-magic-500 to-peach-500 text-white",
  },
  royal: {
    cardClassName:
      "bg-gradient-to-br from-peach-100 via-magic-50 to-peach-50 ring-2 ring-peach-400/70 dark:from-peach-900/40 dark:via-magic-950/30",
    badgeClassName: "bg-gradient-to-r from-peach-500 via-magic-500 to-peach-500 text-white",
  },
  gentle: {
    cardClassName: "bg-gradient-to-b from-peach-50 to-card ring-1 ring-peach-200/70 dark:from-peach-950/30",
    badgeClassName: "bg-peach-100 text-peach-600 dark:bg-peach-900/40 dark:text-peach-200",
  },
  chaos: {
    cardClassName:
      "bg-gradient-to-br from-magic-100 to-peach-100 ring-2 ring-magic-400/70 dark:from-magic-900/50 dark:to-peach-900/30",
    badgeClassName: "bg-gradient-to-r from-magic-500 to-peach-500 text-white bg-[length:200%_auto]",
  },
  mystic: {
    cardClassName:
      "bg-gradient-to-b from-slate-50 to-magic-50 ring-1 ring-slate-300/60 dark:from-slate-900/40 dark:to-magic-950/30",
    badgeClassName: "bg-slate-100 text-slate-700 dark:bg-slate-800/50 dark:text-slate-200",
  },
  calm: {
    cardClassName: "bg-gradient-to-b from-sky-50 to-card ring-1 ring-sky-300/60 dark:from-sky-950/40",
    badgeClassName: "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-200",
  },
  bold: {
    cardClassName:
      "bg-gradient-to-br from-peach-100 to-magic-100 ring-2 ring-peach-400/60 dark:from-peach-900/40 dark:to-magic-900/30",
    badgeClassName: "bg-gradient-to-r from-peach-500 to-magic-500 text-white",
  },
  velvet: {
    cardClassName:
      "bg-gradient-to-br from-magic-100 to-peach-50 ring-1 ring-magic-300/70 dark:from-magic-900/40 dark:to-peach-950/20",
    badgeClassName: "bg-magic-100 text-magic-700 dark:bg-magic-900/50 dark:text-magic-200",
  },
};

export function getArchetypeTheme(themeToken: string): ArchetypeTheme {
  return ARCHETYPE_THEMES[themeToken] ?? DEFAULT_THEME;
}
