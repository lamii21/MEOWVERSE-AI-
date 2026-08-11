import type {
  Achievement,
  BreedDiscovery,
  CollectionPage,
  CollectionQuery,
  CollectionStats,
  Progress,
} from "@/types/collection";

export type CollectionApiErrorKind = "unauthorized" | "server" | "network";

export class CollectionApiError extends Error {
  kind: CollectionApiErrorKind;

  constructor(message: string, kind: CollectionApiErrorKind) {
    super(message);
    this.name = "CollectionApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { credentials: "include" });
  } catch {
    throw new CollectionApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
  if (response.status === 401) {
    throw new CollectionApiError("Please sign in to view this.", "unauthorized");
  }
  if (!response.ok) {
    throw new CollectionApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response;
}

export async function fetchCollection(query: CollectionQuery = {}): Promise<CollectionPage> {
  const params = new URLSearchParams();
  if (query.rarity) params.set("rarity", query.rarity);
  if (query.favoritesOnly) params.set("favorites_only", "true");
  if (query.hasStory) params.set("has_story", "true");
  if (query.search) params.set("search", query.search);
  if (query.sort) params.set("sort", query.sort);
  if (query.page) params.set("page", String(query.page));
  if (query.pageSize) params.set("page_size", String(query.pageSize));

  const response = await request(`/api/v1/me/collection?${params.toString()}`);
  return response.json();
}

export async function fetchStats(): Promise<CollectionStats> {
  const response = await request("/api/v1/me/stats");
  return response.json();
}

export async function fetchAchievements(): Promise<Achievement[]> {
  const response = await request("/api/v1/me/achievements");
  return response.json();
}

export async function fetchBreeds(): Promise<BreedDiscovery[]> {
  const response = await request("/api/v1/me/breeds");
  return response.json();
}

export async function fetchProgress(): Promise<Progress> {
  const response = await request("/api/v1/me/progress");
  return response.json();
}
