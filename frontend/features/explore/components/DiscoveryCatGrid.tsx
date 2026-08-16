import { Sparkles } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

import { DiscoveryCatCard } from "./DiscoveryCatCard";

import type { DiscoveryCat } from "@/types/explore";

/** The main discovery grid (Phase 15 spec §4/§32) — "Load more" rather
 * than auto-triggered infinite scroll: simpler to make fully keyboard/
 * screen-reader accessible (a real, focusable button with a clear
 * label) than an IntersectionObserver-driven auto-load, and spec §4
 * explicitly allows either. */
export function DiscoveryCatGrid({
  items,
  total,
  isLoading,
  isError,
  hasMore,
  onLoadMore,
  isLoadingMore,
}: {
  items: DiscoveryCat[];
  total: number;
  isLoading: boolean;
  isError: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  isLoadingMore: boolean;
}) {
  if (isLoading) {
    return (
      <div
        className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
        aria-busy="true"
        aria-label="Loading public cats"
      >
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            className="aspect-[3/4] animate-pulse rounded-2xl bg-muted"
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <p className="py-16 text-center text-sm text-destructive" role="alert">
        The Cat Universe is taking a nap. Try again soon.
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 py-16 text-center">
        <Sparkles className="size-8 text-muted-foreground" aria-hidden="true" />
        <p className="font-heading text-lg font-semibold">No cats found here yet.</p>
        <p className="text-sm text-muted-foreground">
          Try a different search or filter, or be the first to share one.
        </p>
        <Button className="rounded-full" nativeButton={false} render={<Link href="/discover" />}>
          Analyze your cat
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="grid w-full grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {items.map((cat) => (
          <DiscoveryCatCard key={cat.analysis_id} cat={cat} />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Showing {items.length} of {total}
      </p>
      {hasMore && (
        <Button
          variant="outline"
          className="rounded-full"
          onClick={onLoadMore}
          disabled={isLoadingMore}
        >
          {isLoadingMore ? "Loading..." : "Load more"}
        </Button>
      )}
    </div>
  );
}
