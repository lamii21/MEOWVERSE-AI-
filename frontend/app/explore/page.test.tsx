import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

vi.mock("@/services/explore", async () => {
  const actual = await vi.importActual<typeof import("@/services/explore")>("@/services/explore");
  return {
    ...actual,
    fetchExploreCats: vi.fn(),
    fetchFeaturedCats: vi.fn(),
    fetchBreedExplorer: vi.fn(),
    fetchPersonalityExplorer: vi.fn(),
    fetchColorExplorer: vi.fn(),
  };
});

import {
  fetchBreedExplorer,
  fetchColorExplorer,
  fetchExploreCats,
  fetchFeaturedCats,
  fetchPersonalityExplorer,
} from "@/services/explore";

import ExplorePage from "./page";

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
  vi.mocked(fetchExploreCats).mockReset();
  vi.mocked(fetchFeaturedCats).mockReset().mockResolvedValue({ cats: [] });
  vi.mocked(fetchBreedExplorer).mockReset().mockResolvedValue([]);
  vi.mocked(fetchPersonalityExplorer).mockReset().mockResolvedValue([]);
  vi.mocked(fetchColorExplorer).mockReset().mockResolvedValue([]);
});

describe("ExplorePage", () => {
  it("renders the hero and heading", async () => {
    vi.mocked(fetchExploreCats).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 24 });
    renderWithQueryClient(<ExplorePage />);
    expect(screen.getByText("Cat Universe")).toBeInTheDocument();
    await waitFor(() => expect(fetchExploreCats).toHaveBeenCalled());
  });

  it("shows the empty state when there are no public cats yet", async () => {
    vi.mocked(fetchExploreCats).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 24 });
    renderWithQueryClient(<ExplorePage />);
    await waitFor(() => expect(screen.getByText(/no cats found/i)).toBeInTheDocument());
  });

  it("renders real results once loaded", async () => {
    vi.mocked(fetchExploreCats).mockResolvedValue({
      items: [makeCat()],
      total: 1,
      page: 1,
      page_size: 24,
    });
    renderWithQueryClient(<ExplorePage />);
    await waitFor(() => expect(screen.getByText("Sable")).toBeInTheDocument());
  });

  it("shows an honest error message on failure", async () => {
    vi.mocked(fetchExploreCats).mockRejectedValue(new Error("network down"));
    renderWithQueryClient(<ExplorePage />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("re-queries with the selected rarity filter", async () => {
    vi.mocked(fetchExploreCats).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 24 });
    const user = userEvent.setup();
    renderWithQueryClient(<ExplorePage />);
    await waitFor(() => expect(fetchExploreCats).toHaveBeenCalled());

    await user.click(screen.getByRole("radio", { name: "Legendary" }));

    await waitFor(() =>
      expect(fetchExploreCats).toHaveBeenLastCalledWith(
        expect.objectContaining({ rarity: "Legendary" }),
        1,
        24,
      ),
    );
  });
});
