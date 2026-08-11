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
 */
export function useCardTilt(ref: RefObject<HTMLDivElement | null>, enabled: boolean) {
  const reduceMotion = useReducedMotion();
  const active = enabled && !reduceMotion;

  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const springX = useSpring(x, { stiffness: 300, damping: 30 });
  const springY = useSpring(y, { stiffness: 300, damping: 30 });

  const rotateX = useTransform(springY, [0, 1], [MAX_TILT_DEG, -MAX_TILT_DEG]);
  const rotateY = useTransform(springX, [0, 1], [-MAX_TILT_DEG, MAX_TILT_DEG]);

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!active || e.pointerType === "touch") return;
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
    style: active ? { rotateX, rotateY, transformPerspective: 800 } : {},
    handlers: active
      ? { onPointerMove: handlePointerMove, onPointerLeave: handlePointerLeave }
      : {},
  };
}
