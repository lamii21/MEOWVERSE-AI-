import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DiscoveryCatCard } from "./DiscoveryCatCard";

import type { DiscoveryCat } from "@/types/explore";

function makeCat(overrides: Partial<DiscoveryCat> = {}): DiscoveryCat {
  return {
    analysis_id: "11111111-1111-1111-1111-111111111111",
    cat_name: "Sable",
    breed: { label: "Bombay", confidence: 0.91 },
    rarity: "Legendary",
    colors: [{ name: "black", hex: "#050608", percentage: 100 }],
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

describe("DiscoveryCatCard", () => {
  it("renders name, breed, rarity, and archetype", () => {
    render(<DiscoveryCatCard cat={makeCat()} />);
    expect(screen.getByText("Sable")).toBeInTheDocument();
    expect(screen.getByText("Bombay")).toBeInTheDocument();
    expect(screen.getByText("Legendary")).toBeInTheDocument();
    expect(screen.getByText("Mystic Whisker")).toBeInTheDocument();
  });

  it("links to the public cat page, never a collection/owner path", () => {
    render(<DiscoveryCatCard cat={makeCat()} />);
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/cat/11111111-1111-1111-1111-111111111111",
    );
  });

  it("never renders owner-only fields", () => {
    const { container } = render(<DiscoveryCatCard cat={makeCat()} />);
    expect(container.innerHTML).not.toMatch(/owned|is_favorite|email/i);
  });

  it("shows a portrait indicator only when a public portrait exists", () => {
    const { rerender } = render(
      <DiscoveryCatCard cat={makeCat({ has_public_portrait: false })} />,
    );
    expect(screen.queryByLabelText("Has an AI portrait")).not.toBeInTheDocument();

    rerender(<DiscoveryCatCard cat={makeCat({ has_public_portrait: true })} />);
    expect(screen.getByLabelText("Has an AI portrait")).toBeInTheDocument();
  });

  it("shows a story indicator only when a public story exists", () => {
    const { rerender } = render(<DiscoveryCatCard cat={makeCat({ has_public_story: false })} />);
    expect(screen.queryByLabelText("Has a story")).not.toBeInTheDocument();

    rerender(<DiscoveryCatCard cat={makeCat({ has_public_story: true })} />);
    expect(screen.getByLabelText("Has a story")).toBeInTheDocument();
  });

  it("falls back to a placeholder emoji when there's no image", () => {
    render(<DiscoveryCatCard cat={makeCat({ image_url: null })} />);
    expect(screen.getByText("🐱")).toBeInTheDocument();
  });

  it("handles a missing breed prediction gracefully", () => {
    render(<DiscoveryCatCard cat={makeCat({ breed: null })} />);
    expect(screen.getByText("Sable")).toBeInTheDocument();
  });
});
