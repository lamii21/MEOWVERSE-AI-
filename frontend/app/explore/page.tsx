"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DiscoveryBreedExplorer } from "@/features/explore/components/DiscoveryBreedExplorer";
import { DiscoveryCatGrid } from "@/features/explore/components/DiscoveryCatGrid";
import { DiscoveryColorExplorer } from "@/features/explore/components/DiscoveryColorExplorer";
import { DiscoveryFilters } from "@/features/explore/components/DiscoveryFilters";
import type { DiscoveryQuickFilter } from "@/features/explore/components/DiscoveryFilters";
import { DiscoveryPersonalityExplorer } from "@/features/explore/components/DiscoveryPersonalityExplorer";
import { DiscoverySearch } from "@/features/explore/components/DiscoverySearch";
import { ExploreHero } from "@/features/explore/components/ExploreHero";
import { FeaturedCats } from "@/features/explore/components/FeaturedCats";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { fetchExploreCats } from "@/services/explore";

import type { ExploreSort } from "@/types/explore";

const PAGE_SIZE = 24;

export default function ExplorePage() {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput, 350);
  const [quickFilter, setQuickFilter] = useState<DiscoveryQuickFilter>({
    rarity: null,
    hasStory: false,
    hasPortrait: false,
  });
  const [breed, setBreed] = useState<string | null>(null);
  const [archetype, setArchetype] = useState<string | null>(null);
  const [color, setColor] = useState<string | null>(null);
  const [sort] = useState<ExploreSort>("newest");

  const filters = {
    breed: breed ?? undefined,
    rarity: quickFilter.rarity ?? undefined,
    archetype: archetype ?? undefined,
    color: color ?? undefined,
    hasStory: quickFilter.hasStory,
    hasPortrait: quickFilter.hasPortrait,
    search,
    sort,
  };

  // useInfiniteQuery keys each page cache entry off `filters` — any
  // filter change is a brand-new query key, so TanStack Query resets
  // to page 1 on its own; no manual "reset accumulated state" effect
  // needed (Phase 15's "Load more" — spec §4).
  const query = useInfiniteQuery({
    queryKey: ["explore", "cats", filters],
    queryFn: ({ pageParam }) => fetchExploreCats(filters, pageParam, PAGE_SIZE),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? allPages.length + 1 : undefined;
    },
  });

  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;
  const activeCategoryLabel = breed || archetype || color || quickFilter.rarity || search;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-4 py-12 sm:px-6">
      <ExploreHero />

      <div className="flex flex-col gap-3">
        <DiscoverySearch value={searchInput} onChange={setSearchInput} />
        <DiscoveryFilters value={quickFilter} onChange={setQuickFilter} />
      </div>

      <FeaturedCats />

      <DiscoveryBreedExplorer selected={breed} onSelect={setBreed} />

      <DiscoveryPersonalityExplorer selected={archetype} onSelect={setArchetype} />

      <DiscoveryColorExplorer selected={color} onSelect={setColor} />

      <section aria-labelledby="latest-heading">
        <h2 id="latest-heading" className="font-heading text-xl font-bold">
          {activeCategoryLabel ? "Discoveries" : "Latest Discoveries"}
        </h2>
        <div className="mt-3">
          <DiscoveryCatGrid
            items={items}
            total={total}
            isLoading={query.isLoading}
            isError={query.isError}
            hasMore={query.hasNextPage ?? false}
            onLoadMore={() => query.fetchNextPage()}
            isLoadingMore={query.isFetchingNextPage}
          />
        </div>
      </section>
    </div>
  );
}
