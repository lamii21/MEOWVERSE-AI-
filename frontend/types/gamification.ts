import type { Achievement } from "@/types/achievement";

/**
 * Attached to any mutation response that itself triggers a
 * gamification event (analysis create/save/favorite/share, story
 * generate) — never present on a plain GET. Drives the
 * DiscoveryToast queue (app/services/gamification.py's
 * GamificationEvent is the source of truth this mirrors).
 */
export interface GamificationEvent {
  xp_awarded: number;
  total_xp: number;
  level: number;
  leveled_up: boolean;
  is_new_breed: boolean;
  is_new_rarity: boolean;
  newly_unlocked: Achievement[];
}
