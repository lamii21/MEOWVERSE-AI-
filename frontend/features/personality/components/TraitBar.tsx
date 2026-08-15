import type { PersonalityTraitScore } from "@/types/personality";

/** One trait row — an accessible progress bar (`role="progressbar"`,
 * matching `ProgressCard`'s established pattern), always labeled
 * "AI-inspired" rather than shown as a bare percentage that could
 * read as a measured claim (Phase 13 spec §5). The `level` word
 * ("High", "Balanced", ...) carries the same information as color
 * alone would, for anyone who can't perceive the bar's fill color. */
export function TraitBar({ name, trait }: { name: string; trait: PersonalityTraitScore }) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="capitalize text-foreground">{name}</span>
        <span className="text-xs text-muted-foreground">
          {trait.level} · AI-inspired {trait.score}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={trait.score}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${name}: ${trait.level}, AI-inspired score ${trait.score} out of 100`}
        className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-magic-400 to-peach-400 transition-[width] duration-500"
          style={{ width: `${trait.score}%` }}
        />
      </div>
    </div>
  );
}
