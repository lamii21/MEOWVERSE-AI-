import type { GamificationEvent } from "@/types/gamification";

/**
 * A tiny external store (Phase 10) for the discovery-moment toast
 * queue — same `useSyncExternalStore` pattern this codebase already
 * uses for SSR-safe cross-component state (Phase 7's story-favorite
 * hook), chosen over a React Context because the producer (any Cat
 * Card's Save/Favorite/Share mutation, or story generation, anywhere
 * in the tree) and the consumer (one toast host mounted in the root
 * layout) have no natural parent/child relationship to thread a
 * context through.
 *
 * One event can contain several distinct discoveries (a new breed AND
 * a level-up AND an achievement, all from the same Save click) — these
 * are queued and shown one at a time, never stacked, so the user isn't
 * hit with several overlapping animations at once (spec §19/§25).
 */

export type DiscoveryToastKind = "breed" | "rarity" | "achievement" | "levelup";

export interface DiscoveryToastItem {
  id: string;
  kind: DiscoveryToastKind;
  emoji: string;
  title: string;
  description?: string;
}

let current: DiscoveryToastItem | null = null;
let queue: DiscoveryToastItem[] = [];
const listeners = new Set<() => void>();
let nextId = 0;
function uniqueId(prefix: string): string {
  nextId += 1;
  return `${prefix}-${nextId}`;
}

function emit(): void {
  for (const listener of listeners) listener();
}

function advance(): void {
  current = queue.shift() ?? null;
  emit();
}

export function pushGamificationEvent(event: GamificationEvent | null | undefined): void {
  if (!event) return;

  const items: DiscoveryToastItem[] = [];
  if (event.is_new_breed) {
    items.push({ id: uniqueId("breed"), kind: "breed", emoji: "✨", title: "New breed discovered!" });
  }
  if (event.is_new_rarity) {
    items.push({ id: uniqueId("rarity"), kind: "rarity", emoji: "💎", title: "New rarity discovered!" });
  }
  for (const achievement of event.newly_unlocked) {
    items.push({
      id: `achievement-${achievement.key}`,
      kind: "achievement",
      emoji: achievement.emoji,
      title: "Achievement unlocked!",
      description: achievement.label,
    });
  }
  if (event.leveled_up) {
    items.push({
      id: `level-${event.level}`,
      kind: "levelup",
      emoji: "🌟",
      title: "Level up!",
      description: `Level ${event.level}`,
    });
  }

  if (items.length === 0) return;
  queue.push(...items);
  if (!current) advance();
  else emit();
}

export function dismissCurrent(): void {
  advance();
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot(): DiscoveryToastItem | null {
  return current;
}

export function _resetForTests(): void {
  current = null;
  queue = [];
}
