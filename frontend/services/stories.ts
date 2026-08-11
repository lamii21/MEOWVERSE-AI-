import type { StoryResponse, StoryStyle } from "@/types/story";

export type StoryApiErrorKind = "validation" | "not_found" | "rate_limited" | "server" | "network";

export class StoryApiError extends Error {
  kind: StoryApiErrorKind;

  constructor(message: string, kind: StoryApiErrorKind) {
    super(message);
    this.name = "StoryApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new StoryApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
}

function throwForStatus(response: Response, notFoundMessage: string): never | void {
  if (response.status === 404) {
    throw new StoryApiError(notFoundMessage, "not_found");
  }
  if (response.status === 429) {
    throw new StoryApiError(
      "Too many requests right now — give the Cat Universe a moment to rest.",
      "rate_limited",
    );
  }
  if (!response.ok) {
    throw new StoryApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
}

export async function generateStory(
  analysisId: string,
  style: StoryStyle,
  regenerate = false,
): Promise<StoryResponse> {
  const response = await request(`/api/v1/analyses/${analysisId}/story`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ style, regenerate }),
  });

  if (response.status === 422) {
    const body = await response.json().catch(() => null);
    throw new StoryApiError(
      body?.detail ?? "That story style isn't recognized.",
      "validation",
    );
  }
  throwForStatus(response, "We couldn't find that cat's analysis anymore.");

  return response.json();
}

export async function fetchPublicStory(storyId: string): Promise<StoryResponse> {
  const response = await request(`/api/v1/stories/${storyId}`);
  throwForStatus(response, "This story couldn't be found — it may be private or no longer exists.");
  return response.json();
}

export async function shareStory(storyId: string): Promise<StoryResponse> {
  const response = await request(`/api/v1/stories/${storyId}/share`, { method: "POST" });
  throwForStatus(response, "This story couldn't be found.");
  return response.json();
}
