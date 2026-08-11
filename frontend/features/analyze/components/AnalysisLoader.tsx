"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import { Progress } from "@/components/ui/progress";
import { Sparkle } from "@/components/Sparkle";

const STAGES = [
  "Finding whiskers...",
  "Counting fluff...",
  "Reading tiny paws...",
  "Searching the Cat Universe...",
  "Learning your cat's personality...",
  "Choosing a magical destiny...",
  "Discovering hidden magic...",
];

const STAGE_DURATION_MS = 1400;

export function AnalysisLoader() {
  const [stageIndex, setStageIndex] = useState(0);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, STAGE_DURATION_MS);
    return () => clearInterval(interval);
  }, []);

  const progress = Math.round(((stageIndex + 1) / STAGES.length) * 100);

  return (
    <div className="flex flex-col items-center gap-8 text-center">
      <div className="relative flex size-32 items-center justify-center">
        <motion.div
          className="absolute inset-0 rounded-full bg-gradient-to-br from-magic-300 to-peach-300 opacity-40 blur-xl"
          animate={reduceMotion ? undefined : { scale: [1, 1.15, 1] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.span
          className="text-6xl"
          animate={reduceMotion ? undefined : { rotate: [-4, 4, -4] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        >
          🐱
        </motion.span>
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute"
            style={{ left: `${10 + i * 35}%`, top: `${5 + i * 8}%` }}
            animate={reduceMotion ? undefined : { opacity: [0.2, 1, 0.2], scale: [0.7, 1.1, 0.7] }}
            transition={{ duration: 1.8, repeat: Infinity, delay: i * 0.4, ease: "easeInOut" }}
          >
            <Sparkle size={10 + i * 2} />
          </motion.div>
        ))}
      </div>

      <div className="h-8">
        <AnimatePresence mode="wait">
          <motion.p
            key={stageIndex}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="font-heading text-lg font-medium"
            role="status"
            aria-live="polite"
          >
            {STAGES[stageIndex]}
          </motion.p>
        </AnimatePresence>
      </div>

      <Progress value={progress} className="w-full max-w-xs" />
    </div>
  );
}
