"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, Cat, Crown, Gem, Heart, Map as MapIcon, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CollectionCard } from "@/features/collection/components/CollectionCard";
import { BreedExplorer } from "@/features/collection/components/BreedExplorer";
import { CollectionMap } from "@/features/collection/components/CollectionMap";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { ProgressCard } from "@/features/gamification/components/ProgressCard";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { fetchBreeds, fetchCollection, fetchProgress, fetchStats } from "@/services/collection";
import { cn } from "@/lib/utils";

import type { Rarity } from "@/types/analysis";
import type { CollectionSort } from "@/types/collection";

const RARITIES: Rarity[] = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"];
const PAGE_SIZE = 24;

type QuickFilter = "all" | "favorites" | "stories" | "recent" | Rarity;

const QUICK_FILTERS: { value: QuickFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "favorites", label: "Favorites" },
  ...RARITIES.map((r) => ({ value: r as QuickFilter, label: r })),
  { value: "stories", label: "Stories" },
  { value: "recent", label: "Recently Discovered" },
];

const SORT_OPTIONS: { value: CollectionSort; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "name_asc", label: "Name A-Z" },
  { value: "name_desc", label: "Name Z-A" },
  { value: "rarity", label: "Rarity" },
  { value: "breed", label: "Breed" },
  { value: "favorite", label: "Favorite" },
];

function StatChip({ icon: Icon, label, value }: { icon: typeof Cat; label: string; value: string | number }) {
  return (
    <div className="glass flex flex-col items-center rounded-2xl p-3 text-center">
      <Icon className="size-4 text-magic-500" aria-hidden="true" />
      <p className="mt-1 font-heading text-lg font-bold">{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}

function CollectionContent() {
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput, 350);
  const [sort, setSort] = useState<CollectionSort>("newest");
  const [page, setPage] = useState(1);
  const [showMap, setShowMap] = useState(false);
  const [showBreeds, setShowBreeds] = useState(false);

  const rarity = (RARITIES as string[]).includes(quickFilter) ? (quickFilter as Rarity) : null;
  const favoritesOnly = quickFilter === "favorites";
  const hasStory = quickFilter === "stories";
  // "Recently Discovered" is a real chip but not a fabricated
  // time-window filter (e.g. "last 7 days" would be an invented
  // threshold) — it simply forces the honest, already-real "newest
  // first" ordering, same as the spec's own reluctance to invent
  // definitions it doesn't need (§9).
  const effectiveSort: CollectionSort = quickFilter === "recent" ? "newest" : sort;

  const collectionQuery = useQuery({
    queryKey: ["collection", { rarity, favoritesOnly, hasStory, search, sort: effectiveSort, page }],
    queryFn: () =>
      fetchCollection({
        rarity,
        favoritesOnly,
        hasStory,
        search,
        sort: effectiveSort,
        page,
        pageSize: PAGE_SIZE,
      }),
  });
  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: fetchProgress });
  const breedsQuery = useQuery({ queryKey: ["breeds"], queryFn: fetchBreeds, enabled: showBreeds });

  const totalPages = collectionQuery.data
    ? Math.max(1, Math.ceil(collectionQuery.data.total / PAGE_SIZE))
    : 1;

  function selectFilter(value: QuickFilter) {
    setQuickFilter(value);
    setPage(1);
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-12 sm:px-6">
      <div className="text-center">
        <h1 className="font-heading text-3xl font-bold tracking-tight">My Cat Universe</h1>
        <p className="mt-2 text-muted-foreground">
          Every little friend you&apos;ve discovered lives here.
        </p>
      </div>

      {statsQuery.data && (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
          <StatChip icon={Cat} label="Cats" value={statsQuery.data.total_cats} />
          <StatChip icon={Heart} label="Favorites" value={statsQuery.data.favorites_count} />
          <StatChip icon={BookOpen} label="Stories" value={statsQuery.data.stories_created} />
          <StatChip icon={Gem} label="Rare+" value={statsQuery.data.rare_count} />
          <StatChip icon={Crown} label="Legendary+" value={statsQuery.data.legendary_count} />
          <StatChip
            icon={Sparkles}
            label="Explored"
            value={`${statsQuery.data.completion_percentage}%`}
          />
        </div>
      )}

      {progressQuery.data && <ProgressCard progress={progressQuery.data} />}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name, breed, or color..."
            className="pl-8"
            aria-label="Search your cats"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="collection-sort">
            Sort by
          </label>
          <select
            id="collection-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as CollectionSort)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                Sort: {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div role="radiogroup" aria-label="Filter your collection" className="flex flex-wrap gap-2">
        {QUICK_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            role="radio"
            aria-checked={quickFilter === f.value}
            onClick={() => selectFilter(f.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              quickFilter === f.value
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {collectionQuery.isLoading && (
        <p className="py-16 text-center text-sm text-muted-foreground">Loading your cats...</p>
      )}

      {collectionQuery.isError && (
        <p className="py-16 text-center text-sm text-destructive" role="alert">
          The Cat Universe is taking a nap. Try again soon.
        </p>
      )}

      {collectionQuery.data && collectionQuery.data.items.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-16 text-center">
          <Sparkles className="size-8 text-muted-foreground" aria-hidden="true" />
          <p className="font-heading text-lg font-semibold">
            You haven&apos;t discovered your first cat yet.
          </p>
          <Button className="rounded-full" nativeButton={false} render={<Link href="/discover" />}>
            Discover a Cat
          </Button>
        </div>
      )}

      {collectionQuery.data && collectionQuery.data.items.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {collectionQuery.data.items.map((item) => (
              <CollectionCard key={item.id} result={item} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          )}

          <div className="mt-2 flex flex-col gap-3">
            <button
              type="button"
              onClick={() => setShowMap((v) => !v)}
              className="flex items-center gap-2 self-start rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              aria-expanded={showMap}
            >
              <MapIcon className="size-4" aria-hidden="true" />
              {showMap ? "Hide MeowVerse Map" : "Show MeowVerse Map"}
            </button>
            {showMap && <CollectionMap cats={collectionQuery.data.items} />}
          </div>
        </>
      )}

      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={() => setShowBreeds((v) => !v)}
          className="flex items-center gap-2 self-start rounded-full border border-border px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          aria-expanded={showBreeds}
        >
          <Cat className="size-4" aria-hidden="true" />
          {showBreeds ? "Hide Breed Explorer" : "Show Breed Explorer"}
        </button>
        {showBreeds && breedsQuery.data && <BreedExplorer breeds={breedsQuery.data} />}
      </div>
    </div>
  );
}

export default function CollectionPage() {
  return (
    <RequireAuth>
      <CollectionContent />
    </RequireAuth>
  );
}
