"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect } from "react";

import { dismissCurrent } from "@/lib/discovery-toast-store";
import { useDiscoveryToast } from "@/features/gamification/use-discovery-toast";

const DISPLAY_MS = 3200;

/**
 * One toast at a time, auto-advancing through the queue (see
 * lib/discovery-toast-store.ts) — mounted once in the root layout so
 * any mutation anywhere in the tree (Save, Favorite, Share, story
 * generation) can trigger it without prop-drilling. Soft glow + gentle
 * scale only, no flashing (spec §25); reduced motion drops the
 * animation but keeps the same show/auto-dismiss timing so the
 * information itself is never lost, just its motion.
 */
export function DiscoveryToastHost() {
  const toast = useDiscoveryToast();
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(dismissCurrent, DISPLAY_MS);
    return () => clearTimeout(timer);
  }, [toast]);

  return (
    <div
      className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4"
      aria-live="polite"
      role="status"
    >
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -16, scale: 0.92 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: reduceMotion ? 0.15 : 0.35, ease: "easeOut" }}
            className="glass pointer-events-auto flex items-center gap-3 rounded-2xl px-5 py-3 shadow-[0_0_30px_-8px_var(--color-magic-400)]"
          >
            <span className="text-2xl" aria-hidden="true">
              {toast.emoji}
            </span>
            <div className="text-left">
              <p className="font-heading text-sm font-semibold">{toast.title}</p>
              {toast.description && (
                <p className="text-xs text-muted-foreground">{toast.description}</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
