import { act, render, screen } from "@testing-library/react";
import { useReducedMotion } from "framer-motion";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ResultReveal } from "./ResultReveal";

// See features/results/use-card-tilt.test.ts for why useReducedMotion
// is mocked directly rather than via window.matchMedia.
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: vi.fn(() => false) };
});

describe("ResultReveal", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(useReducedMotion).mockReturnValue(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the intro beat before revealing content", () => {
    render(
      <ResultReveal catImageUrl={null}>
        {(interactive) => <div data-testid="content">interactive:{String(interactive)}</div>}
      </ResultReveal>,
    );

    expect(screen.getByText("A new cat has appeared...")).toBeInTheDocument();
    expect(screen.queryByTestId("content")).not.toBeInTheDocument();
  });

  it("reveals content (not yet interactive) after the intro, then becomes interactive once settled", () => {
    render(
      <ResultReveal catImageUrl={null}>
        {(interactive) => <div data-testid="content">interactive:{String(interactive)}</div>}
      </ResultReveal>,
    );

    act(() => vi.advanceTimersByTime(1400));
    expect(screen.getByTestId("content")).toHaveTextContent("interactive:false");

    act(() => vi.advanceTimersByTime(1300));
    expect(screen.getByTestId("content")).toHaveTextContent("interactive:true");
  });

  it("skips straight to the finished, interactive state under prefers-reduced-motion", () => {
    // Doesn't assert the intro node is gone from the DOM: AnimatePresence's
    // exit transition is RAF-driven and doesn't resolve under fake timers/
    // jsdom, so the outgoing node can visually linger (opacity: 0) in this
    // test environment even though `stage` is correctly "done" immediately
    // — confirmed for real in the Playwright pass with reduced-motion
    // emulation, where the intro beat is skipped visually too.
    vi.mocked(useReducedMotion).mockReturnValue(true);
    render(
      <ResultReveal catImageUrl={null}>
        {(interactive) => <div data-testid="content">interactive:{String(interactive)}</div>}
      </ResultReveal>,
    );
    act(() => vi.advanceTimersByTime(0));

    expect(screen.getByTestId("content")).toHaveTextContent("interactive:true");
  });
});
