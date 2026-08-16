import type { GamificationEvent } from "@/types/gamification";

export type PortraitStyleId =
  | "royal"
  | "magical_guardian"
  | "fantasy_wizard"
  | "cosmic"
  | "cozy_cafe"
  | "storybook"
  | "watercolor"
  | "sticker"
  | "anime"
  | "medieval";

export interface PortraitStyleOption {
  value: PortraitStyleId;
  emoji: string;
  title: string;
  description: string;
}

/** UI-facing metadata only, mirroring the backend's
 * PORTRAIT_STYLE_LABELS (app/schemas/portrait.py) — the frontend never
 * constructs prompt text itself (Phase 14 spec §11); this is purely
 * what the style picker displays. */
export const PORTRAIT_STYLE_OPTIONS: PortraitStyleOption[] = [
  { value: "royal", emoji: "👑", title: "Royal Portrait", description: "Regal robes, a gilded frame, quiet dignity." },
  { value: "magical_guardian", emoji: "🌙", title: "Magical Guardian", description: "Moonlit and mystical, wrapped in soft protective light." },
  { value: "fantasy_wizard", emoji: "🧙", title: "Fantasy Wizard", description: "A pointed hat, a glowing staff, a hint of spellcraft." },
  { value: "cosmic", emoji: "🪐", title: "Cosmic Cat", description: "Adrift among stars, nebulae, and stardust." },
  { value: "cozy_cafe", emoji: "☕", title: "Cozy Café", description: "A warm window seat, a cup of something hot, soft afternoon light." },
  { value: "storybook", emoji: "📚", title: "Storybook Illustration", description: "Hand-drawn and whimsical, like a page from a children's book." },
  { value: "watercolor", emoji: "🌸", title: "Watercolor", description: "Soft washes of color and loose, painterly edges." },
  { value: "sticker", emoji: "🎀", title: "Cute Sticker", description: "Bold outline, flat colors, a die-cut sticker look." },
  { value: "anime", emoji: "✨", title: "Anime-Inspired", description: "Clean linework and expressive anime shading." },
  { value: "medieval", emoji: "🏰", title: "Medieval Portrait", description: "Oil-painted and formal, like an old castle's gallery." },
];

export type PortraitStatus = "pending" | "succeeded" | "failed";

export type PortraitErrorCode =
  | "provider_unavailable"
  | "timeout"
  | "rate_limited"
  | "content_rejected"
  | "invalid_output"
  | "storage_failed"
  | "network_error"
  | "source_image_unavailable"
  | "provider_error";

export interface CatPortrait {
  id: string;
  analysis_id: string;
  style: PortraitStyleId;
  style_name: string;
  style_emoji: string;
  status: PortraitStatus;
  image_url: string | null;
  provider: string;
  model: string | null;
  prompt_version: string;
  error_code: PortraitErrorCode | null;
  error_message: string | null;
  is_public: boolean;
  owned: boolean;
  reused: boolean;
  created_at: string;
  completed_at: string | null;
  gamification: GamificationEvent | null;
}

export interface PortraitListResponse {
  portraits: CatPortrait[];
}
