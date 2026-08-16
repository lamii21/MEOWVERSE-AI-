"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

// Phase 14 spec §18's exact playful sequence — an indeterminate
// loading experience (spec §19: no fake percentages, since a real
// image-generation call has no meaningful progress signal to report).
// Wording only ever implies real steps this pipeline actually performs
// (a real prompt build, a real provider call, a real store) — never a
// fabricated technical process.
const STAGES = [
  "Preparing the portrait studio...",
  "Preserving every whisker...",
  "Painting a new universe...",
  "Adding the final sparkle...",
];
const STAGE_DURATION_MS = 1400;

/** Cycles through the reveal messages once, then holds on the last one
 * until the real result arrives — same shape as Phase 13's
 * PersonalityReveal (`animate` always present, only the *transition*
 * becomes instant under reduced motion via Framer's global
 * `MotionConfig`, so this needs no reduced-motion branching of its own). */
export function PortraitReveal() {
  const [stageIndex, setStageIndex] = useState(0);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, STAGE_DURATION_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center gap-3 py-8" role="status" aria-live="polite">
      <span className="text-4xl" aria-hidden="true">
        🎨
      </span>
      {/* Indeterminate — no fake percentage (spec §19). */}
      <div className="h-1.5 w-40 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-magic-400 to-peach-400"
          animate={reduceMotion ? undefined : { x: ["-100%", "220%"] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <AnimatePresence mode="wait">
        <motion.p
          key={stageIndex}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
          className="font-heading text-sm font-medium text-muted-foreground"
        >
          {STAGES[stageIndex]}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
