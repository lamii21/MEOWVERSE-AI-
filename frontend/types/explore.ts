import type { BreedPrediction, ColorSwatch, Rarity } from "@/types/analysis";

export type ExploreSort = "newest" | "oldest" | "rarity" | "most_discovered" | "name_asc" | "name_desc";

/** A public cat's discovery-card shape — deliberately distinct from
 * `AnalysisResult` (no `owned`, no `is_favorite`, no owner identity):
 * every field here is safe to show a stranger by construction. */
export interface DiscoveryCat {
  analysis_id: string;
  cat_name: string;
  breed: BreedPrediction | null;
  rarity: Rarity;
  colors: ColorSwatch[];
  image_url: string | null;
  archetype_id: string;
  archetype_name: string;
  archetype_emoji: string;
  has_public_story: boolean;
  has_public_portrait: boolean;
  created_at: string;
}

export interface ExploreCatsPage {
  items: DiscoveryCat[];
  total: number;
  page: number;
  page_size: number;
}

export interface FeaturedCatsResponse {
  cats: DiscoveryCat[];
}

export interface BreedExplorerEntry {
  breed: string;
  public_count: number;
  examples: DiscoveryCat[];
}

export interface PersonalityArchetypeExplorerEntry {
  id: string;
  name: string;
  emoji: string;
  short_description: string;
  long_description: string;
  theme_token: string;
  public_count: number;
  examples: DiscoveryCat[];
  disclaimer: string;
}

export interface ColorExplorerEntry {
  color_name: string;
  hex: string;
  public_count: number;
  examples: DiscoveryCat[];
}

export interface ExploreCatsFilters {
  breed?: string;
  rarity?: string;
  archetype?: string;
  color?: string;
  hasStory?: boolean;
  hasPortrait?: boolean;
  search?: string;
  sort?: ExploreSort;
}
