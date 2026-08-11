"use client";

import { useQuery } from "@tanstack/react-query";
import { Heart, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CollectionCard } from "@/features/collection/components/CollectionCard";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { fetchCollection } from "@/services/collection";
import { cn } from "@/lib/utils";

import type { Rarity } from "@/types/analysis";
import type { CollectionSort } from "@/types/collection";

const RARITIES: Rarity[] = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"];
const PAGE_SIZE = 24;

const SORT_OPTIONS: { value: CollectionSort; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "rarity", label: "Rarity" },
  { value: "name", label: "Name" },
];

function CollectionContent() {
  const [rarity, setRarity] = useState<Rarity | null>(null);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<CollectionSort>("newest");
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ["collection", { rarity, favoritesOnly, search, sort, page }],
    queryFn: () =>
      fetchCollection({ rarity, favoritesOnly, search, sort, page, pageSize: PAGE_SIZE }),
  });

  const totalPages = query.data ? Math.max(1, Math.ceil(query.data.total / PAGE_SIZE)) : 1;

  function resetToFirstPage() {
    setPage(1);
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-12 sm:px-6">
      <div className="text-center">
        <h1 className="font-heading text-3xl font-bold tracking-tight">My Cats</h1>
        <p className="mt-2 text-muted-foreground">Every cat you&apos;ve discovered and saved.</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              resetToFirstPage();
            }}
            placeholder="Search by name or breed..."
            className="pl-8"
            aria-label="Search your cats"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={favoritesOnly ? "secondary" : "outline"}
            size="sm"
            className="gap-1.5 rounded-full"
            aria-pressed={favoritesOnly}
            onClick={() => {
              setFavoritesOnly((v) => !v);
              resetToFirstPage();
            }}
          >
            <Heart
              className={cn("size-3.5", favoritesOnly && "fill-destructive text-destructive")}
              aria-hidden="true"
            />
            Favorites
          </Button>

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

      <div role="radiogroup" aria-label="Filter by rarity" className="flex flex-wrap gap-2">
        <button
          type="button"
          role="radio"
          aria-checked={rarity === null}
          onClick={() => {
            setRarity(null);
            resetToFirstPage();
          }}
          className={cn(
            "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
            rarity === null
              ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          All
        </button>
        {RARITIES.map((r) => (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={rarity === r}
            onClick={() => {
              setRarity(r);
              resetToFirstPage();
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              rarity === r
                ? "border-magic-400 bg-magic-100 text-magic-700 dark:bg-magic-900/40"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {r}
          </button>
        ))}
      </div>

      {query.isLoading && (
        <p className="py-16 text-center text-sm text-muted-foreground">Loading your cats...</p>
      )}

      {query.isError && (
        <p className="py-16 text-center text-sm text-destructive" role="alert">
          The Cat Universe is taking a nap. Try again soon.
        </p>
      )}

      {query.data && query.data.items.length === 0 && (
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

      {query.data && query.data.items.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {query.data.items.map((item) => (
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
        </>
      )}
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
