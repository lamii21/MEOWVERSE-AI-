"use client";

import { Lock } from "lucide-react";

import { cn } from "@/lib/utils";

import type { BreedDiscovery } from "@/types/collection";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/** Every canonical breed the classifier recognizes, undiscovered ones
 * shown locked — never implying the user has analyzed a breed they
 * haven't (Phase 10 spec §10). */
export function BreedExplorer({ breeds }: { breeds: BreedDiscovery[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
      {breeds.map((breed) => (
        <div
          key={breed.breed}
          className={cn(
            "flex flex-col items-center gap-1 rounded-2xl border p-3 text-center",
            breed.discovered
              ? "border-magic-300 bg-magic-50 dark:bg-magic-900/20"
              : "border-border bg-muted/40 opacity-70",
          )}
        >
          {breed.discovered ? (
            <span className="text-2xl" aria-hidden="true">
              🐱
            </span>
          ) : (
            <Lock className="size-5 text-muted-foreground" aria-hidden="true" />
          )}
          <p className="text-sm font-medium">{breed.breed}</p>
          {breed.discovered ? (
            <div className="text-xs text-muted-foreground">
              <p>
                {breed.count} {breed.count === 1 ? "cat" : "cats"}
              </p>
              {breed.best_confidence !== null && (
                <p>Best match: {Math.round(breed.best_confidence * 100)}%</p>
              )}
              {breed.latest_discovery && <p>Last found {formatDate(breed.latest_discovery)}</p>}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Undiscovered</p>
          )}
        </div>
      ))}
    </div>
  );
}
