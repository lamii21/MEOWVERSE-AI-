"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";

import { getRarityVisual } from "@/features/results/rarity";

import type { AnalysisResult } from "@/types/analysis";

const VIEWBOX = 100;
const MAX_NODES = 60;

/** A small, fast, deterministic hash — the same cat always lands on
 * the same spot on the map (no stored coordinates needed, and it
 * can't drift between renders/refreshes). */
function hashToUnit(seed: string, salt: number): number {
  let h = salt;
  for (let i = 0; i < seed.length; i++) {
    h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return (h % 1000) / 1000;
}

function starPosition(id: string): { x: number; y: number } {
  // Keep nodes away from the very edge (8-92%) so labels/glow don't clip.
  const margin = 8;
  const span = VIEWBOX - margin * 2;
  return {
    x: margin + hashToUnit(id, 17) * span,
    y: margin + hashToUnit(id, 91) * span,
  };
}

/**
 * "My Cat Universe" as a constellation — each discovered cat is a
 * star, positioned deterministically, sized/colored by rarity tier.
 * Pure SVG + CSS + Framer Motion (no WebGL) so it stays cheap even
 * with a few dozen nodes on screen. Capped at MAX_NODES for the same
 * reason — this is a "feel of the collection" view, not a replacement
 * for the paginated grid, which remains the actual browsing surface.
 *
 * Below `sm`, small touch targets scattered across an SVG canvas stop
 * being usable, so a simple list takes over instead (spec §11).
 */
export function CollectionMap({ cats }: { cats: AnalysisResult[] }) {
  const reduceMotion = useReducedMotion();
  const nodes = cats.slice(0, MAX_NODES).filter((cat) => cat.id !== null);

  if (nodes.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        Your map is still dark — discover a cat to light up the first star.
      </p>
    );
  }

  return (
    <>
      <div className="hidden overflow-hidden rounded-2xl bg-gradient-to-b from-slate-950 via-magic-950 to-slate-950 p-2 sm:block">
        <svg
          viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
          className="aspect-[16/9] w-full"
          role="img"
          aria-label={`A star map of ${nodes.length} discovered cats`}
        >
          {/* Faint decorative background stars — purely atmospheric. */}
          {Array.from({ length: 40 }).map((_, i) => {
            const x = hashToUnit(`bg-${i}`, 3) * VIEWBOX;
            const y = hashToUnit(`bg-${i}`, 7) * VIEWBOX;
            return (
              <circle key={i} cx={x} cy={y} r={0.25} fill="white" opacity={0.25} aria-hidden="true" />
            );
          })}

          {nodes.map((cat, index) => {
            const { x, y } = starPosition(cat.id as string);
            const rarity = getRarityVisual(cat.profile.rarity);
            const radius = 1.2 + rarity.tier * 0.35;
            return (
              <motion.g
                key={cat.id}
                initial={reduceMotion ? undefined : { opacity: 0, scale: 0.3 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: reduceMotion ? 0 : Math.min(index * 0.02, 0.6), duration: 0.4 }}
              >
                <Link href={`/collection/${cat.id}`} aria-label={`View ${cat.profile.name}, ${cat.profile.rarity}`}>
                  <circle
                    cx={x}
                    cy={y}
                    r={radius + 2}
                    fill="transparent"
                    className="cursor-pointer"
                  />
                  <circle
                    cx={x}
                    cy={y}
                    r={radius}
                    className="fill-magic-300"
                    style={{ filter: `drop-shadow(0 0 ${radius}px var(--color-magic-400))` }}
                  />
                  <text
                    x={x}
                    y={y + radius + 3}
                    textAnchor="middle"
                    className="fill-white/70"
                    style={{ fontSize: "2.2px" }}
                  >
                    {cat.profile.name}
                  </text>
                </Link>
              </motion.g>
            );
          })}
        </svg>
      </div>

      <ul className="grid grid-cols-2 gap-2 sm:hidden">
        {nodes.map((cat) => {
          const rarity = getRarityVisual(cat.profile.rarity);
          return (
            <li key={cat.id}>
              <Link
                href={`/collection/${cat.id}`}
                className={`flex items-center gap-2 rounded-xl p-2 text-sm ${rarity.cardClassName}`}
              >
                <span aria-hidden="true">🐱</span>
                <span className="truncate">{cat.profile.name}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
