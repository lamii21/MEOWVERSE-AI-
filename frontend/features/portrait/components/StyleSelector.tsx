import { cn } from "@/lib/utils";
import { PORTRAIT_STYLE_OPTIONS } from "@/types/portrait";

import type { PortraitStyleId } from "@/types/portrait";

/** A controlled set of 10 styles (Phase 14 spec §10) — the frontend
 * only ever picks a `style` id here; the actual prompt is entirely
 * backend-built (see app/ai/portrait_prompt.py), never assembled or
 * edited client-side (spec §11). Accessible radiogroup, same pattern
 * as GradCamExplanation's view switcher and the collection page's
 * rarity filter. */
export function StyleSelector({
  value,
  onChange,
  disabled,
}: {
  value: PortraitStyleId;
  onChange: (style: PortraitStyleId) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Portrait style"
      className="grid grid-cols-2 gap-2 sm:grid-cols-3"
    >
      {PORTRAIT_STYLE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          disabled={disabled}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition-colors disabled:pointer-events-none disabled:opacity-50",
            value === option.value
              ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40 dark:text-magic-200"
              : "border-border bg-card hover:bg-muted",
          )}
        >
          <span className="text-2xl" aria-hidden="true">
            {option.emoji}
          </span>
          <span className="text-xs font-medium">{option.title}</span>
        </button>
      ))}
    </div>
  );
}
