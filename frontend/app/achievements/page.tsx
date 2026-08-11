"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { fetchAchievements } from "@/services/collection";
import { cn } from "@/lib/utils";

function formatUnlockedDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

function AchievementsContent() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["achievements"],
    queryFn: fetchAchievements,
  });

  const unlocked = data?.filter((a) => a.unlocked) ?? [];
  const locked = data?.filter((a) => !a.unlocked) ?? [];

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12 sm:px-6">
      <div className="text-center">
        <h1 className="font-heading text-3xl font-bold tracking-tight">Achievements</h1>
        <p className="mt-2 text-muted-foreground">
          Milestones you&apos;ve earned exploring the Cat Universe.
        </p>
      </div>

      {isLoading && (
        <p className="py-16 text-center text-sm text-muted-foreground">Loading achievements...</p>
      )}
      {isError && (
        <p className="py-16 text-center text-sm text-destructive" role="alert">
          The Cat Universe is taking a nap. Try again soon.
        </p>
      )}

      {data && (
        <>
          <section>
            <h2 className="font-heading text-lg font-semibold">
              Unlocked ({unlocked.length}/{data.length})
            </h2>
            {unlocked.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">
                Nothing unlocked yet — discover your first cat to get started.
              </p>
            ) : (
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                {unlocked.map((a) => (
                  <div
                    key={a.key}
                    className="flex items-center gap-3 rounded-2xl border border-magic-300 bg-magic-50 p-3 dark:bg-magic-900/20"
                  >
                    <span className="text-2xl" aria-hidden="true">
                      {a.emoji}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{a.label}</p>
                      <p className="text-xs text-muted-foreground">{a.description}</p>
                      {a.unlocked_at && (
                        <p className="text-[11px] text-muted-foreground">
                          Unlocked {formatUnlockedDate(a.unlocked_at)}
                        </p>
                      )}
                    </div>
                    <Badge variant="secondary" className="ml-auto shrink-0">
                      Unlocked
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="font-heading text-lg font-semibold">Locked</h2>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {locked.map((a) => {
                const percent = Math.min(
                  100,
                  Math.round((a.progress_current / Math.max(a.progress_target, 1)) * 100),
                );
                return (
                  <div
                    key={a.key}
                    className="flex flex-col gap-2 rounded-2xl border border-border p-3 opacity-80"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl grayscale" aria-hidden="true">
                        {a.emoji}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{a.label}</p>
                        <p className="text-xs text-muted-foreground">{a.description}</p>
                      </div>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuenow={percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`Progress toward ${a.label}`}
                      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted")}
                    >
                      <div
                        className="h-full rounded-full bg-magic-400 transition-[width] duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      {a.progress_current} / {a.progress_target}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default function AchievementsPage() {
  return (
    <RequireAuth>
      <AchievementsContent />
    </RequireAuth>
  );
}
