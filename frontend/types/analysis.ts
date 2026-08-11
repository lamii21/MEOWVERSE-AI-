import type { GamificationEvent } from "@/types/gamification";

export interface BreedPrediction {
  label: string;
  confidence: number;
}

export interface ColorSwatch {
  name: string;
  hex: string;
  percentage: number;
}

export type PredictionMode = "demo" | "trained";

export type Season = "Spring" | "Summer" | "Autumn" | "Winter";
export type Rarity = "Common" | "Uncommon" | "Rare" | "Epic" | "Legendary" | "Mythical";

/** AI-generated creative content — never a scientific or veterinary claim. */
export interface CatProfile {
  name: string;
  title: string;
  personality: string;
  magic_power: string;
  kingdom: string;
  favorite_activity: string;
  favorite_food: string;
  favorite_season: Season;
  rarity: Rarity;
  description: string;
}

/**
 * Deliberately a different vocabulary than PredictionMode ("demo" |
 * "trained") — the profile is never a "prediction," real or otherwise,
 * so it must never be labeled with words that imply it is one.
 */
export type ProfileMode = "demo" | "generated";

export interface AnalysisResult {
  /** Set only if the backend could persist the analysis (Phase 7) —
   * story generation needs this. `null` if the database was
   * unreachable; the rest of the analysis is still fully usable. */
  id: string | null;
  detected: boolean;
  breed: BreedPrediction | null;
  breed_mode: PredictionMode;
  colors: ColorSwatch[];
  colors_mode: PredictionMode;
  embedding_available: boolean;
  profile: CatProfile;
  profile_mode: ProfileMode;
  /** Whether the Cat Card has been explicitly shared (Phase 8) — see
   * POST /api/v1/analyses/{id}/share. Always false for a fresh analysis. */
  is_public: boolean;
  /** Phase 9: true if this analysis belongs to the *caller* — either
   * auto-owned (created while signed in) or claimed via POST .../save.
   * Always false on a public (someone-else's-shared-cat) view, even if
   * that cat has an owner — see analysis_row_to_result's docstring on
   * the backend for why this is never leaked to other viewers. */
  owned: boolean;
  is_favorite: boolean;
  image_url: string | null;
  /** Phase 10: only set on responses from an action that itself
   * triggers a gamification event — a plain GET never carries one. */
  gamification: GamificationEvent | null;
  created_at: string | null;
  has_story: boolean;
}
