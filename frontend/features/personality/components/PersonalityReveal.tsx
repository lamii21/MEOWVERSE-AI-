"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

// Phase 13 spec §25's exact sequence — playful UI copy only, never
// implying the model is literally measuring behavioral characteristics
// (the actual computation is a deterministic scoring function plus, at
// most, one fast LLM call — these messages just make the short wait
// feel like part of the magic).
const STAGES = [
  "Reading the vibes...",
  "Measuring the whisker energy...",
  "Consulting the Cat Universe...",
];
const STAGE_DURATION_MS = 900;

/** Cycles through the reveal messages once, then holds on the last one
 * until real data arrives and this component unmounts — never repeats
 * or implies a specific elapsed-time guarantee. Framer's `animate`
 * prop here is always present (not conditioned on reduced motion),
 * only the *transition* is instant under reduced motion — same
 * SSR-hydration-safe shape established in Phase 12's `AuthCard`/
 * `CatCard` fixes (not that hydration risk applies here, since this
 * only ever mounts client-side after a query starts, but keeping the
 * same shape is simpler than re-deriving the reasoning per component).
 */
export function PersonalityReveal() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, STAGE_DURATION_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center gap-2 py-6" role="status" aria-live="polite">
      <span className="text-3xl" aria-hidden="true">
        🐾
      </span>
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
