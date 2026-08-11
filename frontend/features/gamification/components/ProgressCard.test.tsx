import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressCard } from "./ProgressCard";

import type { Progress } from "@/types/collection";

function makeProgress(overrides: Partial<Progress> = {}): Progress {
  return {
    xp: 150,
    level: 2,
    level_title: "Meow Explorer",
    xp_into_level: 50,
    xp_needed_for_level: 300,
    xp_for_next_level: 400,
    progress_ratio: 50 / 300,
    ...overrides,
  };
}

describe("ProgressCard", () => {
  it("shows the level title and level number", () => {
    render(<ProgressCard progress={makeProgress()} />);
    expect(screen.getByText(/Meow Explorer — Level 2/)).toBeInTheDocument();
  });

  it("shows xp progress within the current level", () => {
    render(<ProgressCard progress={makeProgress()} />);
    expect(screen.getByText("50 / 300 XP")).toBeInTheDocument();
  });

  it("shows a max-level message once there is no next level", () => {
    render(
      <ProgressCard
        progress={makeProgress({ xp: 5000, level: 20, xp_for_next_level: null, progress_ratio: 1 })}
      />,
    );
    expect(screen.getByText("5000 XP (max level)")).toBeInTheDocument();
  });

  it("exposes progress via an accessible progressbar", () => {
    render(<ProgressCard progress={makeProgress()} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", String(Math.round((50 / 300) * 100)));
  });
});
