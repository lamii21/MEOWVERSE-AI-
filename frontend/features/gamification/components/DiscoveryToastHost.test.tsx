import { act, render, screen } from "@testing-library/react";
import { useReducedMotion } from "framer-motion";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { _resetForTests, pushGamificationEvent } from "@/lib/discovery-toast-store";

import { DiscoveryToastHost } from "./DiscoveryToastHost";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: vi.fn(() => false) };
});

describe("DiscoveryToastHost", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(useReducedMotion).mockReturnValue(false);
    _resetForTests();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when there is no discovery to show", () => {
    render(<DiscoveryToastHost />);
    expect(screen.queryByRole("status")).toBeEmptyDOMElement();
  });

  it("shows a toast for a new breed discovery", () => {
    render(<DiscoveryToastHost />);
    act(() => {
      pushGamificationEvent({
        xp_awarded: 100,
        total_xp: 100,
        level: 1,
        leveled_up: false,
        is_new_breed: true,
        is_new_rarity: false,
        newly_unlocked: [],
      });
    });
    expect(screen.getByText("New breed discovered!")).toBeInTheDocument();
  });

  it("shows an achievement toast with the achievement's label", () => {
    render(<DiscoveryToastHost />);
    act(() => {
      pushGamificationEvent({
        xp_awarded: 150,
        total_xp: 150,
        level: 2,
        leveled_up: true,
        is_new_breed: false,
        is_new_rarity: false,
        newly_unlocked: [
          {
            key: "first_meow",
            emoji: "🐾",
            label: "First Paw",
            description: "Discover your first cat.",
            unlocked: true,
            unlocked_at: "2026-01-01T00:00:00Z",
            progress_current: 1,
            progress_target: 1,
          },
        ],
      });
    });
    expect(screen.getByText("Achievement unlocked!")).toBeInTheDocument();
    expect(screen.getByText("First Paw")).toBeInTheDocument();
  });

  it("auto-dismisses and advances to the next queued toast", () => {
    render(<DiscoveryToastHost />);
    act(() => {
      pushGamificationEvent({
        xp_awarded: 100,
        total_xp: 100,
        level: 1,
        leveled_up: false,
        is_new_breed: true,
        is_new_rarity: true,
        newly_unlocked: [],
      });
    });
    expect(screen.getByText("New breed discovered!")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(3300));
    expect(screen.getByText("New rarity discovered!")).toBeInTheDocument();
  });
});
