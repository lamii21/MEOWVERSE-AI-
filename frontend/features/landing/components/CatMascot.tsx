"use client";

import { motion, useReducedMotion } from "framer-motion";

import { Sparkle } from "@/components/Sparkle";

const sparkles = [
  { x: "8%", y: "12%", size: 14, delay: 0 },
  { x: "88%", y: "8%", size: 10, delay: 0.6 },
  { x: "92%", y: "62%", size: 16, delay: 1.1 },
  { x: "4%", y: "68%", size: 12, delay: 1.6 },
  { x: "50%", y: "2%", size: 9, delay: 2.1 },
];

export function CatMascot() {
  const reduceMotion = useReducedMotion();

  return (
    <div
      className="relative mx-auto aspect-square w-full max-w-md"
      role="img"
      aria-label="An illustrated magical cat surrounded by sparkles"
    >
      {sparkles.map((s, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{ left: s.x, top: s.y }}
          animate={
            reduceMotion
              ? undefined
              : { opacity: [0.2, 1, 0.2], scale: [0.8, 1.15, 0.8] }
          }
          transition={{
            duration: 2.8,
            repeat: Infinity,
            delay: s.delay,
            ease: "easeInOut",
          }}
        >
          <Sparkle size={s.size} />
        </motion.div>
      ))}

      <motion.div
        animate={reduceMotion ? undefined : { y: [0, -14, 0] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg viewBox="0 0 220 220" className="w-full drop-shadow-xl">
          <defs>
            <linearGradient id="catBody" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-magic-400)" />
              <stop offset="100%" stopColor="var(--color-magic-600)" />
            </linearGradient>
          </defs>

          <ellipse cx="110" cy="200" rx="55" ry="8" className="fill-foreground/10" />

          <path
            d="M158 150 C 190 150, 200 110, 178 90 C 195 100, 198 135, 172 158 Z"
            fill="url(#catBody)"
          />

          <path
            d="M60 190 C 40 150, 45 95, 110 90 C 175 95, 180 150, 160 190 C 130 205, 90 205, 60 190 Z"
            fill="url(#catBody)"
          />

          <ellipse cx="110" cy="185" rx="34" ry="20" className="fill-peach-50 dark:fill-peach-100" />

          <circle cx="110" cy="85" r="48" fill="url(#catBody)" />

          <path d="M70 55 L 60 20 L 95 48 Z" fill="url(#catBody)" />
          <path d="M150 55 L 160 20 L 125 48 Z" fill="url(#catBody)" />
          <path d="M75 48 L 70 30 L 90 46 Z" className="fill-peach-200" />
          <path d="M145 48 L 150 30 L 130 46 Z" className="fill-peach-200" />

          <path
            d="M85 90 Q92 98 99 90"
            stroke="var(--color-magic-900)"
            strokeWidth="3.5"
            strokeLinecap="round"
            fill="none"
          />
          <path
            d="M121 90 Q128 98 135 90"
            stroke="var(--color-magic-900)"
            strokeWidth="3.5"
            strokeLinecap="round"
            fill="none"
          />

          <path d="M108 100 L 112 100 L 110 105 Z" className="fill-peach-300" />
          <path
            d="M110 105 Q104 112 96 108"
            stroke="var(--color-magic-900)"
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />
          <path
            d="M110 105 Q116 112 124 108"
            stroke="var(--color-magic-900)"
            strokeWidth="2.5"
            strokeLinecap="round"
            fill="none"
          />

          <g stroke="var(--color-magic-900)" strokeWidth="1.5" strokeLinecap="round" opacity="0.5">
            <path d="M55 92 L30 88" />
            <path d="M55 100 L28 100" />
            <path d="M165 92 L190 88" />
            <path d="M165 100 L192 100" />
          </g>

          <circle cx="110" cy="180" r="4" className="fill-peach-300" />
          <path
            d="M100 178 Q110 172 120 178"
            stroke="var(--color-peach-400)"
            strokeWidth="2.5"
            fill="none"
          />
        </svg>
      </motion.div>
    </div>
  );
}
