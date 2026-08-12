import type { SimilarityQuery, SimilarityResponse } from "@/types/similarity";

export type SimilarityApiErrorKind = "not_found" | "unauthorized" | "server" | "network";

export class SimilarityApiError extends Error {
  kind: SimilarityApiErrorKind;

  constructor(message: string, kind: SimilarityApiErrorKind) {
    super(message);
    this.name = "SimilarityApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchSimilarCats(
  analysisId: string,
  query: SimilarityQuery = {},
): Promise<SimilarityResponse> {
  const params = new URLSearchParams();
  if (query.k) params.set("k", String(query.k));
  if (query.breed) params.set("breed", query.breed);
  if (query.rarity) params.set("rarity", query.rarity);
  if (query.favoritesOnly) params.set("favorites_only", "true");

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/analyses/${analysisId}/similar?${params}`, {
      credentials: "include",
    });
  } catch {
    throw new SimilarityApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }

  if (response.status === 404) {
    throw new SimilarityApiError("This cat couldn't be found.", "not_found");
  }
  if (response.status === 401) {
    throw new SimilarityApiError("Please sign in to do that.", "unauthorized");
  }
  if (!response.ok) {
    throw new SimilarityApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}
