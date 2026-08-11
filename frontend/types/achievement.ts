/**
 * Its own leaf module, imported by both types/collection.ts and
 * types/gamification.ts — mirrors the backend's app/schemas/achievement.py
 * split, which exists to avoid a real circular import there. Not
 * strictly required on the TypeScript side (type-only circular imports
 * are erased at compile time), but kept parallel for consistency and
 * because achievement shape genuinely is a leaf concept.
 */
export interface Achievement {
  key: string;
  emoji: string;
  label: string;
  description: string;
  unlocked: boolean;
  unlocked_at: string | null;
  progress_current: number;
  progress_target: number;
}
