import type {
  BreedExplorerEntry,
  ColorExplorerEntry,
  ExploreCatsFilters,
  ExploreCatsPage,
  FeaturedCatsResponse,
  PersonalityArchetypeExplorerEntry,
} from "@/types/explore";

export type ExploreApiErrorKind = "validation" | "rate_limited" | "server" | "network";

export class ExploreApiError extends Error {
  kind: ExploreApiErrorKind;

  constructor(message: string, kind: ExploreApiErrorKind) {
    super(message);
    this.name = "ExploreApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { credentials: "include" });
  } catch {
    throw new ExploreApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
  if (response.status === 422) {
    throw new ExploreApiError("That search wasn't valid.", "validation");
  }
  if (response.status === 429) {
    throw new ExploreApiError(
      "Too many requests — give the Cat Universe a moment to rest.",
      "rate_limited",
    );
  }
  if (!response.ok) {
    throw new ExploreApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response;
}

function buildQuery(filters: ExploreCatsFilters, page: number, pageSize: number): string {
  const params = new URLSearchParams();
  if (filters.breed) params.set("breed", filters.breed);
  if (filters.rarity) params.set("rarity", filters.rarity);
  if (filters.archetype) params.set("archetype", filters.archetype);
  if (filters.color) params.set("color", filters.color);
  if (filters.hasStory) params.set("has_story", "true");
  if (filters.hasPortrait) params.set("has_portrait", "true");
  if (filters.search) params.set("search", filters.search);
  params.set("sort", filters.sort ?? "newest");
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return params.toString();
}

export async function fetchExploreCats(
  filters: ExploreCatsFilters,
  page = 1,
  pageSize = 24,
): Promise<ExploreCatsPage> {
  const response = await request(`/api/v1/explore/cats?${buildQuery(filters, page, pageSize)}`);
  return response.json();
}

export async function fetchFeaturedCats(): Promise<FeaturedCatsResponse> {
  const response = await request("/api/v1/explore/featured");
  return response.json();
}

export async function fetchBreedExplorer(): Promise<BreedExplorerEntry[]> {
  const response = await request("/api/v1/explore/breeds");
  return response.json();
}

export async function fetchPersonalityExplorer(): Promise<PersonalityArchetypeExplorerEntry[]> {
  const response = await request("/api/v1/explore/personalities");
  return response.json();
}

export async function fetchColorExplorer(): Promise<ColorExplorerEntry[]> {
  const response = await request("/api/v1/explore/colors");
  return response.json();
}
