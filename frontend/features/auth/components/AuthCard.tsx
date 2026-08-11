"use client";

import { motion, useReducedMotion } from "framer-motion";

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col items-center justify-center px-4 py-16">
      {/* `initial` deliberately never depends on `reduceMotion`: framer's
       * `motion.div` renders `initial` as a real inline style during SSR,
       * so conditioning it on a client-only value (`useReducedMotion()`)
       * causes the client's very first render to disagree with the
       * server-rendered HTML — a genuine hydration mismatch, found via
       * Playwright with `reducedMotion: "reduce"`. Gating only the
       * transition duration keeps `initial`/`animate` identical between
       * server and client while still making the motion instant (no
       * visible animation) when reduced motion is preferred. */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reduceMotion ? 0 : 0.4 }}
        className="glass w-full rounded-3xl p-8"
      >
        <div className="mb-6 text-center">
          <span className="text-3xl" aria-hidden="true">
            🐾
          </span>
          <h1 className="mt-2 font-heading text-2xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </motion.div>
    </div>
  );
}
