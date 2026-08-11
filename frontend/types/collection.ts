import type { Achievement } from "@/types/achievement";
import type { AnalysisResult, Rarity } from "@/types/analysis";

export type { Achievement };

export type CollectionSort =
  | "newest"
  | "oldest"
  | "name_asc"
  | "name_desc"
  | "rarity"
  | "breed"
  | "favorite";

export interface CollectionQuery {
  rarity?: Rarity | null;
  favoritesOnly?: boolean;
  hasStory?: boolean;
  search?: string;
  sort?: CollectionSort;
  page?: number;
  pageSize?: number;
}

export interface CollectionPage {
  items: AnalysisResult[];
  total: number;
  page: number;
  page_size: number;
}

export interface CollectionStats {
  total_cats: number;
  favorite_breed: string | null;
  most_common_color: string | null;
  legendary_count: number;
  rare_count: number;
  favorites_count: number;
  stories_created: number;
  unique_breeds_discovered: number;
  total_supported_breeds: number;
  completion_percentage: number;
  unique_colors_discovered: number;
  rarity_distribution: Record<Rarity, number>;
}

export interface BreedDiscovery {
  breed: string;
  discovered: boolean;
  count: number;
  best_confidence: number | null;
  latest_discovery: string | null;
}

export interface Progress {
  xp: number;
  level: number;
  level_title: string;
  xp_into_level: number;
  xp_needed_for_level: number;
  xp_for_next_level: number | null;
  progress_ratio: number;
}
