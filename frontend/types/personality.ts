export type PersonalityLevel = "Very Low" | "Low" | "Balanced" | "High" | "Very High";
export type InterpretationMode = "generated" | "demo";

export interface PersonalityTraitScore {
  /** 0-100 — an "AI-inspired" deterministic score, never displayed as
   * a claimed behavioral percentage. See `disclaimer` on the response. */
  score: number;
  level: PersonalityLevel;
  label: string;
  description: string;
}

export interface PersonalityArchetype {
  id: string;
  name: string;
  emoji: string;
  short_description: string;
  long_description: string;
  /** A design-token identifier (e.g. `"dreamy"`) — maps to an existing
   * theme treatment, never an arbitrary invented color. */
  theme_token: string;
}

export interface PersonalityInterpretation {
  headline: string;
  description: string;
  catchphrase: string;
  secret_talent: string;
  fictional_job: string;
  fun_fact: string;
}

export interface CatPersonality {
  id: string;
  analysis_id: string;
  personality_engine_version: string;
  archetype: PersonalityArchetype;
  traits: Record<string, PersonalityTraitScore>;
  created_at: string;

  interpretation_mode: InterpretationMode;
  interpretation_model: string | null;
  interpretation_version: string;
  interpretation: PersonalityInterpretation;
  interpretation_created_at: string;
  interpretation_cached: boolean;

  disclaimer: string;
}
