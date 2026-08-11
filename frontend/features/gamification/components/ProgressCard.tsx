"use client";

import { Sparkles } from "lucide-react";

import type { Progress } from "@/types/collection";

interface ProgressCardProps {
  progress: Progress;
}

/** The XP/level bar — shown on /profile and atop /collection. Every
 * number here is server-computed (app/services/progression.py); this
 * component only renders it. */
export function ProgressCard({ progress }: ProgressCardProps) {
  const percent = Math.round(progress.progress_ratio * 100);

  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-magic-500" aria-hidden="true" />
          <p className="font-heading text-sm font-semibold">
            {progress.level_title} — Level {progress.level}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          {progress.xp_for_next_level === null
            ? `${progress.xp} XP (max level)`
            : `${progress.xp_into_level} / ${progress.xp_needed_for_level} XP`}
        </p>
      </div>
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Level progress"
        className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-magic-400 to-peach-400 transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
