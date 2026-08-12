import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { CatsLikeThis } from "./CatsLikeThis";

vi.mock("@/services/similarity", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/similarity")>("@/services/similarity");
  return { ...actual, fetchSimilarCats: vi.fn() };
});

import { fetchSimilarCats, SimilarityApiError } from "@/services/similarity";

import type { SimilarityResponse } from "@/types/similarity";

function makeResponse(overrides: Partial<SimilarityResponse> = {}): SimilarityResponse {
  return {
    source_cat: { analysis_id: "src-1", cat_name: "Sable", image_url: null },
    similar_cats: [],
    search_mode: "embedding",
    embedding_model: "mobilenet_v3_small_imagenet:v1",
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(fetchSimilarCats).mockReset();
});

describe("CatsLikeThis", () => {
  it("renders nothing when there is no analysis id", () => {
    const { container } = renderWithQueryClient(<CatsLikeThis analysisId={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a loading message while searching", () => {
    vi.mocked(fetchSimilarCats).mockReturnValue(new Promise(() => {}));
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    expect(
      screen.getByText(/Searching the Cat Universe|Finding your cat|Sniffing out/),
    ).toBeInTheDocument();
  });

  it("shows the honest one-of-a-kind empty state when search ran but found nothing", async () => {
    vi.mocked(fetchSimilarCats).mockResolvedValue(makeResponse({ similar_cats: [] }));
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    await waitFor(() =>
      expect(screen.getByText(/Your cat might be one of a kind/)).toBeInTheDocument(),
    );
  });

  it("shows an unavailable message distinct from the empty state", async () => {
    vi.mocked(fetchSimilarCats).mockResolvedValue(
      makeResponse({ search_mode: "unavailable", embedding_model: null }),
    );
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    await waitFor(() =>
      expect(screen.getByText(/isn't available for this cat right now/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/one of a kind/)).not.toBeInTheDocument();
  });

  it("shows an error message on failure, never a stack trace", async () => {
    vi.mocked(fetchSimilarCats).mockRejectedValue(
      new SimilarityApiError("This cat couldn't be found.", "not_found"),
    );
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("This cat couldn't be found."));
  });

  it("renders real similar cats with their real similarity values", async () => {
    vi.mocked(fetchSimilarCats).mockResolvedValue(
      makeResponse({
        similar_cats: [
          {
            analysis_id: "cat-2",
            cat_name: "Luna",
            image_url: null,
            breed: { label: "Siamese", confidence: 0.9 },
            rarity: "Rare",
            visual_similarity: 0.94,
            shared_colors: [],
            is_favorite: false,
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
      }),
    );
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    await waitFor(() => expect(screen.getByText("Luna")).toBeInTheDocument());
    expect(screen.getByText("94% visually similar")).toBeInTheDocument();
  });

  it("never shows a fabricated similarity value — only what the API returned", async () => {
    vi.mocked(fetchSimilarCats).mockResolvedValue(
      makeResponse({
        similar_cats: [
          {
            analysis_id: "cat-3",
            cat_name: "Mochi",
            image_url: null,
            breed: null,
            rarity: "Common",
            visual_similarity: 0.5123,
            shared_colors: [],
            is_favorite: false,
            created_at: null,
          },
        ],
      }),
    );
    renderWithQueryClient(<CatsLikeThis analysisId="src-1" />);
    await waitFor(() => expect(screen.getByText("51% visually similar")).toBeInTheDocument());
  });
});
