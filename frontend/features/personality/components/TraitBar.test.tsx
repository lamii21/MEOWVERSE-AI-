import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TraitBar } from "./TraitBar";

import type { PersonalityTraitScore } from "@/types/personality";

function makeTrait(overrides: Partial<PersonalityTraitScore> = {}): PersonalityTraitScore {
  return {
    score: 69,
    level: "High",
    label: "High curiosity",
    description: "Investigates everything.",
    ...overrides,
  };
}

describe("TraitBar", () => {
  it("renders an accessible progressbar with the real score", () => {
    render(<TraitBar name="curiosity" trait={makeTrait({ score: 69 })} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "69");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("never shows a bare percentage — always labels the score AI-inspired", () => {
    render(<TraitBar name="curiosity" trait={makeTrait({ score: 69, level: "High" })} />);
    expect(screen.getByText(/AI-inspired 69/)).toBeInTheDocument();
    expect(screen.queryByText("69%")).not.toBeInTheDocument();
  });

  it("carries the level word in the accessible label, not color alone", () => {
    render(<TraitBar name="calmness" trait={makeTrait({ score: 51, level: "Balanced" })} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-label",
      "calmness: Balanced, AI-inspired score 51 out of 100",
    );
    expect(screen.getByText(/Balanced/)).toBeInTheDocument();
  });

  it("renders the trait name", () => {
    render(<TraitBar name="mischief" trait={makeTrait()} />);
    expect(screen.getByText("mischief")).toBeInTheDocument();
  });
});
