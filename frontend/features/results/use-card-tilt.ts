"use client";

import { useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";

import type { RefObject } from "react";

const MAX_TILT_DEG = 8;

/**
 * A performant CSS-transform tilt (spec §6: "prefer performant CSS
 * transforms / Framer Motion" over WebGL) — pointer position within
 * the card drives rotateX/rotateY via springs, no external library.
 * Disabled entirely under `prefers-reduced-motion` and while `enabled`
 * is false (used to hold off tilt until the reveal sequence finishes).
 *
 * Takes the target ref rather than creating and returning one — a ref
 * bundled inside a returned object isn't statically recognizable as a
 * ref by the react-hooks/refs (React Compiler) lint rule, which then
 * flags every read of it as an unsafe render-time ref access.
 *
 * `reduceMotion` is deliberately checked only *inside*
 * `handlePointerMove` (a runtime behavior decision), never used to
 * decide whether `style`/`handlers` are structurally present in the
 * returned object — the latter changes what Framer Motion actually
 * renders (it adds `tabIndex="0"` to a `motion.div` that has pointer
 * handlers attached), so gating it on `useReducedMotion()` caused a
 * real SSR/client hydration mismatch on `/cat/[id]` (found via
 * Playwright's `reducedMotion: "reduce"` context option — same root
 * cause as `AuthCard`'s fix, see its docstring). Gating on `enabled`
 * alone is SSR-safe since it's a plain prop, never a client-only read.
 */
export function useCardTilt(ref: RefObject<HTMLDivElement | null>, enabled: boolean) {
  const reduceMotion = useReducedMotion();

  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const springX = useSpring(x, { stiffness: 300, damping: 30 });
  const springY = useSpring(y, { stiffness: 300, damping: 30 });

  const rotateX = useTransform(springY, [0, 1], [MAX_TILT_DEG, -MAX_TILT_DEG]);
  const rotateY = useTransform(springX, [0, 1], [-MAX_TILT_DEG, MAX_TILT_DEG]);

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!enabled || reduceMotion || e.pointerType === "touch") return;
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    x.set((e.clientX - rect.left) / rect.width);
    y.set((e.clientY - rect.top) / rect.height);
  }

  function handlePointerLeave() {
    x.set(0.5);
    y.set(0.5);
  }

  return {
    style: enabled ? { rotateX, rotateY, transformPerspective: 800 } : {},
    handlers: enabled
      ? { onPointerMove: handlePointerMove, onPointerLeave: handlePointerLeave }
      : {},
  };
}
