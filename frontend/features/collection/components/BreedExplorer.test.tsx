import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BreedExplorer } from "./BreedExplorer";

import type { BreedDiscovery } from "@/types/collection";

const BREEDS: BreedDiscovery[] = [
  {
    breed: "Siamese",
    discovered: true,
    count: 3,
    best_confidence: 0.87,
    latest_discovery: "2026-01-05T00:00:00Z",
  },
  {
    breed: "Sphynx",
    discovered: false,
    count: 0,
    best_confidence: null,
    latest_discovery: null,
  },
];

describe("BreedExplorer", () => {
  it("shows discovered breeds with real stats", () => {
    render(<BreedExplorer breeds={BREEDS} />);
    expect(screen.getByText("Siamese")).toBeInTheDocument();
    expect(screen.getByText("3 cats")).toBeInTheDocument();
    expect(screen.getByText("Best match: 87%")).toBeInTheDocument();
  });

  it("shows undiscovered breeds as locked, never fabricating stats", () => {
    render(<BreedExplorer breeds={BREEDS} />);
    expect(screen.getByText("Sphynx")).toBeInTheDocument();
    expect(screen.getByText("Undiscovered")).toBeInTheDocument();
  });
});
