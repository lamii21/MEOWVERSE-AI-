import type { ColorSwatch } from "@/types/analysis";

/**
 * Presents the raw OpenCV/K-means swatch output (Phase 5) as a
 * designer-style palette: a proportional stacked strip up top for an
 * at-a-glance read, then each swatch's name/hex/share spelled out
 * below (spec §14).
 */
export function ColorPalette({ colors }: { colors: ColorSwatch[] }) {
  if (colors.length === 0) return null;

  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {colors.map((c, i) => (
          <span
            key={`${c.hex}-${i}`}
            style={{ backgroundColor: c.hex, width: `${Math.max(c.percentage, 2)}%` }}
            title={`${c.name} — ${Math.round(c.percentage)}%`}
          />
        ))}
      </div>
      <ul className="mt-3 flex flex-col gap-1.5">
        {colors.map((c, i) => (
          <li key={`${c.hex}-${i}`} className="flex items-center gap-2 text-sm">
            <span
              className="size-4 shrink-0 rounded-full border border-black/10"
              style={{ backgroundColor: c.hex }}
              aria-hidden="true"
            />
            <span className="capitalize">{c.name}</span>
            <span className="font-mono text-xs text-muted-foreground">{c.hex}</span>
            <span className="ml-auto tabular-nums text-muted-foreground">
              {Math.round(c.percentage)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
