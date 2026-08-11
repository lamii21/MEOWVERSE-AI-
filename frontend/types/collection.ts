import type { AnalysisResult, Rarity } from "@/types/analysis";

export type CollectionSort = "newest" | "oldest" | "rarity" | "name";

export interface CollectionQuery {
  rarity?: Rarity | null;
  favoritesOnly?: boolean;
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
  favorites_count: number;
  stories_created: number;
}

export interface Achievement {
  key: string;
  emoji: string;
  label: string;
  description: string;
  unlocked: boolean;
  unlocked_at: string | null;
}
