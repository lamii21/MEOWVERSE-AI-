import { renderHook } from "@testing-library/react";
import { useReducedMotion } from "framer-motion";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCardTilt } from "./use-card-tilt";

import type { RefObject } from "react";

// framer-motion's useReducedMotion resolves from a module-level
// matchMedia subscription created once at import time — reassigning
// window.matchMedia per-test doesn't reach it. Mocking the hook's
// return value directly is the reliable way to drive both branches.
vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: vi.fn(() => false) };
});

const fakeRef = { current: null } as RefObject<HTMLDivElement | null>;

describe("useCardTilt", () => {
  beforeEach(() => {
    vi.mocked(useReducedMotion).mockReturnValue(false);
  });

  it("provides no tilt style or pointer handlers when disabled", () => {
    const { result } = renderHook(() => useCardTilt(fakeRef, false));

    expect(result.current.style).toEqual({});
    expect(result.current.handlers).toEqual({});
  });

  it("provides tilt style and handlers when enabled and motion is not reduced", () => {
    const { result } = renderHook(() => useCardTilt(fakeRef, true));

    expect(result.current.style).toHaveProperty("rotateX");
    expect(result.current.style).toHaveProperty("rotateY");
    expect(result.current.handlers).toHaveProperty("onPointerMove");
    expect(result.current.handlers).toHaveProperty("onPointerLeave");
  });

  it("disables tilt even when enabled, if prefers-reduced-motion is set", () => {
    vi.mocked(useReducedMotion).mockReturnValue(true);
    const { result } = renderHook(() => useCardTilt(fakeRef, true));

    expect(result.current.style).toEqual({});
    expect(result.current.handlers).toEqual({});
  });
});
