"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchFeaturedCats } from "@/services/explore";

import { DiscoveryCatCard } from "./DiscoveryCatCard";

export function FeaturedCats() {
  const query = useQuery({ queryKey: ["explore", "featured"], queryFn: fetchFeaturedCats });

  if (query.isLoading) {
    return (
      <div
        className="grid grid-cols-2 gap-4 sm:grid-cols-4"
        aria-busy="true"
        aria-label="Loading featured cats"
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="aspect-[3/4] animate-pulse rounded-2xl bg-muted" aria-hidden="true" />
        ))}
      </div>
    );
  }

  if (query.isError || !query.data || query.data.cats.length === 0) return null;

  return (
    <section aria-labelledby="featured-heading">
      <h2 id="featured-heading" className="font-heading text-xl font-bold">
        Featured Cats
      </h2>
      <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {query.data.cats.map((cat) => (
          <DiscoveryCatCard key={cat.analysis_id} cat={cat} />
        ))}
      </div>
    </section>
  );
}
