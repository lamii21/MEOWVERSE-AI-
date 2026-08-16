import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { FeaturedCats } from "./FeaturedCats";

vi.mock("@/services/explore", async () => {
  const actual = await vi.importActual<typeof import("@/services/explore")>("@/services/explore");
  return { ...actual, fetchFeaturedCats: vi.fn() };
});

import { fetchFeaturedCats } from "@/services/explore";

import type { DiscoveryCat } from "@/types/explore";

function makeCat(overrides: Partial<DiscoveryCat> = {}): DiscoveryCat {
  return {
    analysis_id: "1",
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

beforeEach(() => {
  vi.mocked(fetchFeaturedCats).mockReset();
});

describe("FeaturedCats", () => {
  it("renders the featured heading and cats once loaded", async () => {
    vi.mocked(fetchFeaturedCats).mockResolvedValue({ cats: [makeCat()] });
    renderWithQueryClient(<FeaturedCats />);
    await waitFor(() => expect(screen.getByText("Featured Cats")).toBeInTheDocument());
    expect(screen.getByText("Sable")).toBeInTheDocument();
  });

  it("renders nothing when there are no featured cats yet, never a fake one", async () => {
    vi.mocked(fetchFeaturedCats).mockResolvedValue({ cats: [] });
    const { container } = renderWithQueryClient(<FeaturedCats />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("renders nothing on error rather than crashing", async () => {
    vi.mocked(fetchFeaturedCats).mockRejectedValue(new Error("network down"));
    const { container } = renderWithQueryClient(<FeaturedCats />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
