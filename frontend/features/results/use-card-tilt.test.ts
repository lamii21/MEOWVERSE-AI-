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

  it("keeps style/handlers structurally present under reduced motion (SSR-safe), but pointer move is a no-op", () => {
    // `style`/`handlers` must NOT depend on `useReducedMotion()` (a
    // client-only read) — doing so previously caused a real SSR
    // hydration mismatch on the public /cat/[id] page (Framer Motion
    // adds `tabIndex="0"` to a motion.div with pointer handlers
    // attached, so the server and a reduced-motion client rendered
    // different markup). Reduced motion must only affect *runtime
    // behavior* inside the handler, never the shape of what's rendered.
    vi.mocked(useReducedMotion).mockReturnValue(true);
    const { result } = renderHook(() => useCardTilt(fakeRef, true));

    expect(result.current.style).toHaveProperty("rotateX");
    expect(result.current.style).toHaveProperty("rotateY");
    expect(result.current.handlers).toHaveProperty("onPointerMove");
    expect(result.current.handlers).toHaveProperty("onPointerLeave");

    // Calling it must be a safe no-op under reduced motion, not throw.
    expect(() =>
      result.current.handlers.onPointerMove?.({
        clientX: 10,
        clientY: 10,
        pointerType: "mouse",
      } as React.PointerEvent<HTMLDivElement>),
    ).not.toThrow();
  });
});
