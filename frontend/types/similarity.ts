import type { BreedPrediction } from "@/types/analysis";

export type SearchMode = "embedding" | "unavailable";

export interface SourceCatSummary {
  analysis_id: string;
  cat_name: string;
  image_url: string | null;
}

export interface SimilarCat {
  analysis_id: string;
  cat_name: string;
  image_url: string | null;
  breed: BreedPrediction | null;
  rarity: string;
  /** 0-1 ratio (cosine similarity, clamped at 0), NOT a percentage —
   * the UI multiplies by 100 and rounds for display. See
   * ARCHITECTURE.md §19 for the exact definition. */
  visual_similarity: number;
  shared_colors: string[];
  is_favorite: boolean;
  created_at: string | null;
}

export interface SimilarityResponse {
  source_cat: SourceCatSummary;
  similar_cats: SimilarCat[];
  search_mode: SearchMode;
  embedding_model: string | null;
}

export interface SimilarityQuery {
  k?: number;
  breed?: string;
  rarity?: string;
  favoritesOnly?: boolean;
}
