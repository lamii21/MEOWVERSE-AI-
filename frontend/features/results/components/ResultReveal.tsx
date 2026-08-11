"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

type Stage = "intro" | "card" | "done";

const INTRO_DURATION_MS = 1400;
const CARD_SETTLE_MS = 1300;

/**
 * The cinematic reveal (spec §2): cat image + glow + "A new cat has
 * appeared..." first, then the Cat Card itself (whose own internal
 * stagger — rarity → image → name → breed → magic power → confidence
 * → palette — covers reveal steps 4-8), then the rest of the page
 * (story availability, "how MeowVerse knows") fades in once the card
 * has visually settled, and finally the card becomes interactive
 * (tiltable) — "the Cat Card appears" as a finished, alive object, not
 * mid-animation.
 *
 * `prefers-reduced-motion` skips straight to the finished state
 * (spec §3: reduced motion still gets the *complete* experience, just
 * not gated behind timers) rather than instantly-but-invisibly
 * flashing through each stage.
 */
export function ResultReveal({
  catImageUrl,
  children,
}: {
  catImageUrl?: string | null;
  /** Render-prop so the caller can lay out the Cat Card and its
   * surrounding content (e.g. a two-column desktop grid) while still
   * being told whether the reveal has finished settling. */
  children: (interactive: boolean) => React.ReactNode;
}) {
  const reduceMotion = useReducedMotion();
  const [stage, setStage] = useState<Stage>("intro");

  // useReducedMotion resolves asynchronously (it defers to an effect
  // internally so it's SSR-safe), so it's never trustworthy read
  // directly in a useState initializer — this effect re-syncs `stage`
  // the moment the real value becomes known, rather than only reacting
  // to it inside the timer effects below (which would still run the
  // full animated sequence once before catching up). The update is
  // deferred a tick (not called synchronously in the effect body) per
  // the react-hooks/set-state-in-effect rule — this is genuinely
  // syncing with an external system (the OS motion preference), not
  // the "mirror a prop into state" antipattern that rule exists for.
  useEffect(() => {
    if (!reduceMotion) return;
    const id = setTimeout(() => setStage("done"), 0);
    return () => clearTimeout(id);
  }, [reduceMotion]);

  useEffect(() => {
    if (reduceMotion || stage !== "intro") return;
    const timer = setTimeout(() => setStage("card"), INTRO_DURATION_MS);
    return () => clearTimeout(timer);
  }, [reduceMotion, stage]);

  useEffect(() => {
    if (reduceMotion || stage !== "card") return;
    const timer = setTimeout(() => setStage("done"), CARD_SETTLE_MS);
    return () => clearTimeout(timer);
  }, [reduceMotion, stage]);

  return (
    <div className="flex w-full flex-col items-center">
      <AnimatePresence mode="wait">
        {stage === "intro" && (
          <motion.div
            key="intro"
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.35 }}
            className="flex flex-col items-center gap-5 py-16 text-center"
          >
            <div className="relative flex size-32 items-center justify-center">
              <motion.div
                aria-hidden="true"
                className="absolute inset-0 rounded-full bg-gradient-to-br from-magic-300 to-peach-300 opacity-50 blur-xl"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              />
              {catImageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={catImageUrl}
                  alt=""
                  className="relative size-28 rounded-full object-cover ring-4 ring-white/60 dark:ring-white/20"
                />
              ) : (
                <span className="relative text-6xl" aria-hidden="true">
                  🐱
                </span>
              )}
            </div>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4 }}
              className="font-heading text-lg font-semibold"
              role="status"
              aria-live="polite"
            >
              A new cat has appeared...
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      {stage !== "intro" && (
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full"
        >
          {children(stage === "done")}
        </motion.div>
      )}
    </div>
  );
}
