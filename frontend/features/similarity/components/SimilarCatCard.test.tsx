import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SimilarCatCard } from "./SimilarCatCard";

import type { SimilarCat } from "@/types/similarity";

function makeCat(overrides: Partial<SimilarCat> = {}): SimilarCat {
  return {
    analysis_id: "11111111-1111-1111-1111-111111111111",
    cat_name: "Luna",
    image_url: null,
    breed: { label: "Siamese", confidence: 0.88 },
    rarity: "Rare",
    visual_similarity: 0.94,
    shared_colors: ["cream"],
    is_favorite: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("SimilarCatCard", () => {
  it("renders name, breed, and rarity", () => {
    render(<SimilarCatCard cat={makeCat()} />);
    expect(screen.getByText("Luna")).toBeInTheDocument();
    expect(screen.getByText("Siamese")).toBeInTheDocument();
    expect(screen.getByText("Rare")).toBeInTheDocument();
  });

  it("shows visual similarity as a rounded percentage, never a raw ratio", () => {
    render(<SimilarCatCard cat={makeCat({ visual_similarity: 0.9375 })} />);
    expect(screen.getByText("94% visually similar")).toBeInTheDocument();
  });

  it("links to the cat's public detail page", () => {
    render(<SimilarCatCard cat={makeCat()} />);
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/cat/11111111-1111-1111-1111-111111111111",
    );
  });

  it("falls back to a placeholder emoji when there's no image", () => {
    render(<SimilarCatCard cat={makeCat({ image_url: null })} />);
    expect(screen.getByText("🐱")).toBeInTheDocument();
  });
});
