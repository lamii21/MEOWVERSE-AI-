import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CollectionCard } from "./CollectionCard";

import type { AnalysisResult } from "@/types/analysis";

function makeResult(overrides: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    detected: true,
    breed: { label: "Bombay", confidence: 0.91 },
    breed_mode: "trained",
    colors: [{ name: "cream", hex: "#F3E5D8", percentage: 100 }],
    colors_mode: "trained",
    embedding_available: false,
    profile: {
      name: "Sable",
      title: "Whisperer of the Air Vents",
      personality: "Mysterious.",
      magic_power: "Vanishing.",
      kingdom: "Shadows",
      favorite_activity: "Patrolling",
      favorite_food: "Whatever",
      favorite_season: "Autumn",
      rarity: "Legendary",
      description: "Independent.",
    },
    profile_mode: "generated",
    is_public: false,
    owned: true,
    is_favorite: false,
    image_url: null,
    ...overrides,
  };
}

describe("CollectionCard", () => {
  it("renders name, breed, and rarity", () => {
    render(<CollectionCard result={makeResult()} />);
    expect(screen.getByText("Sable")).toBeInTheDocument();
    expect(screen.getByText("Bombay")).toBeInTheDocument();
    expect(screen.getByText("Legendary")).toBeInTheDocument();
  });

  it("links to the cat's own collection detail page", () => {
    render(<CollectionCard result={makeResult()} />);
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/collection/11111111-1111-1111-1111-111111111111",
    );
  });

  it("shows a favorite indicator only when favorited", () => {
    const { rerender } = render(<CollectionCard result={makeResult({ is_favorite: false })} />);
    expect(screen.queryByLabelText("Favorited")).not.toBeInTheDocument();

    rerender(<CollectionCard result={makeResult({ is_favorite: true })} />);
    expect(screen.getByLabelText("Favorited")).toBeInTheDocument();
  });

  it("falls back to a placeholder emoji when there's no image", () => {
    render(<CollectionCard result={makeResult({ image_url: null })} />);
    expect(screen.getByText("🐱")).toBeInTheDocument();
  });
});
