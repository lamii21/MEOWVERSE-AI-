import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DiscoveryCatGrid } from "./DiscoveryCatGrid";

import type { DiscoveryCat } from "@/types/explore";

function makeCat(overrides: Partial<DiscoveryCat> = {}): DiscoveryCat {
  return {
    analysis_id: "11111111-1111-1111-1111-111111111111",
    cat_name: "Sable",
    breed: { label: "Bombay", confidence: 0.91 },
    rarity: "Legendary",
    colors: [],
    image_url: null,
    archetype_id: "mystic_whisker",
    archetype_name: "Mystic Whisker",
    archetype_emoji: "🔮",
    has_public_story: false,
    has_public_portrait: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const NOOP_PROPS = {
  items: [] as DiscoveryCat[],
  total: 0,
  isLoading: false,
  isError: false,
  hasMore: false,
  onLoadMore: vi.fn(),
  isLoadingMore: false,
};

describe("DiscoveryCatGrid", () => {
  it("shows a busy skeleton state while loading", () => {
    render(<DiscoveryCatGrid {...NOOP_PROPS} isLoading />);
    expect(screen.getByLabelText("Loading public cats")).toBeInTheDocument();
  });

  it("shows an honest error message on failure, never a stack trace", () => {
    render(<DiscoveryCatGrid {...NOOP_PROPS} isError />);
    expect(screen.getByRole("alert")).toHaveTextContent(/taking a nap/i);
  });

  it("shows an empty state with a real call to action, never a fake discovery", () => {
    render(<DiscoveryCatGrid {...NOOP_PROPS} items={[]} />);
    expect(screen.getByText(/no cats found/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze your cat/i })).toHaveAttribute(
      "href",
      "/discover",
    );
  });

  it("renders every cat card when results exist", () => {
    render(
      <DiscoveryCatGrid
        {...NOOP_PROPS}
        items={[makeCat(), makeCat({ analysis_id: "2", cat_name: "Luna" })]}
        total={2}
      />,
    );
    expect(screen.getByText("Sable")).toBeInTheDocument();
    expect(screen.getByText("Luna")).toBeInTheDocument();
  });

  it("shows Load More only when hasMore is true", () => {
    const { rerender } = render(
      <DiscoveryCatGrid {...NOOP_PROPS} items={[makeCat()]} total={1} hasMore={false} />,
    );
    expect(screen.queryByRole("button", { name: /load more/i })).not.toBeInTheDocument();

    rerender(<DiscoveryCatGrid {...NOOP_PROPS} items={[makeCat()]} total={5} hasMore={true} />);
    expect(screen.getByRole("button", { name: /load more/i })).toBeInTheDocument();
  });

  it("calls onLoadMore when clicked", async () => {
    const onLoadMore = vi.fn();
    const user = userEvent.setup();
    render(
      <DiscoveryCatGrid
        {...NOOP_PROPS}
        items={[makeCat()]}
        total={5}
        hasMore={true}
        onLoadMore={onLoadMore}
      />,
    );
    await user.click(screen.getByRole("button", { name: /load more/i }));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("disables Load More while a page is already loading", () => {
    render(
      <DiscoveryCatGrid
        {...NOOP_PROPS}
        items={[makeCat()]}
        total={5}
        hasMore={true}
        isLoadingMore={true}
      />,
    );
    expect(screen.getByRole("button", { name: /loading/i })).toBeDisabled();
  });
});
