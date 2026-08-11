"use client";

import { motion, useReducedMotion } from "framer-motion";

import { Sparkle } from "@/components/Sparkle";

import type { RarityTreatment } from "../rarity";

/**
 * Renders the per-tier animated flourish behind/around a Cat Card.
 * Deliberately restrained (spec §5: "subtle and premium," "do not use
 * excessive flashing effects") — only Rare/Epic/Legendary/Mythical get
 * any motion at all, and every animated variant has a static
 * equivalent for `prefers-reduced-motion` rather than just turning
 * itself off (reduced motion should still feel finished, not broken).
 */
export function RarityAura({ treatment }: { treatment: RarityTreatment }) {
  const reduceMotion = useReducedMotion();

  if (treatment === "plain" || treatment === "tint") return null;

  if (treatment === "shimmer") {
    return (
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]"
      >
        <motion.div
          className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/40 to-transparent dark:via-white/15"
          style={{ width: "60%" }}
          animate={reduceMotion ? { x: "20%" } : { x: ["-60%", "160%"] }}
          transition={
            reduceMotion ? undefined : { duration: 3.2, repeat: Infinity, ease: "easeInOut", repeatDelay: 1.5 }
          }
        />
      </div>
    );
  }

  if (treatment === "glow") {
    return (
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-4 -z-10 rounded-[inherit] bg-gradient-to-br from-magic-400/30 to-peach-400/30 blur-2xl"
      />
    );
  }

  if (treatment === "aura") {
    return (
      <motion.div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-6 -z-10 rounded-[inherit] bg-gradient-to-br from-peach-400/30 via-magic-400/20 to-peach-400/30 blur-2xl"
        animate={reduceMotion ? { opacity: 0.7 } : { opacity: [0.5, 0.85, 0.5], scale: [1, 1.04, 1] }}
        transition={reduceMotion ? undefined : { duration: 3.6, repeat: Infinity, ease: "easeInOut" }}
      />
    );
  }

  // particles (Mythical) — a handful of static or gently twinkling sparkles.
  const positions = [
    { top: "-6%", left: "8%" },
    { top: "10%", left: "94%" },
    { top: "88%", left: "-4%" },
    { top: "96%", left: "80%" },
  ];

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10">
      <div className="pointer-events-none absolute -inset-6 rounded-[inherit] bg-gradient-to-br from-magic-400/20 via-peach-400/15 to-sky-300/20 blur-2xl" />
      {positions.map((pos, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={pos}
          animate={reduceMotion ? { opacity: 0.6 } : { opacity: [0.25, 0.9, 0.25], scale: [0.8, 1.1, 0.8] }}
          transition={
            reduceMotion ? undefined : { duration: 2.4, repeat: Infinity, delay: i * 0.5, ease: "easeInOut" }
          }
        >
          <Sparkle size={12} />
        </motion.div>
      ))}
    </div>
  );
}
