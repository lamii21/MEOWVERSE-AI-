import type { CatPersonality } from "@/types/personality";

export type PersonalityApiErrorKind = "not_found" | "unauthorized" | "server" | "network";

export class PersonalityApiError extends Error {
  kind: PersonalityApiErrorKind;

  constructor(message: string, kind: PersonalityApiErrorKind) {
    super(message);
    this.name = "PersonalityApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  } catch {
    throw new PersonalityApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
  if (response.status === 404) {
    throw new PersonalityApiError("This cat couldn't be found.", "not_found");
  }
  if (response.status === 401) {
    throw new PersonalityApiError("Please sign in to do that.", "unauthorized");
  }
  if (!response.ok) {
    throw new PersonalityApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response;
}

export async function fetchPersonality(analysisId: string): Promise<CatPersonality> {
  const response = await request(`/api/v1/analyses/${analysisId}/personality`);
  return response.json();
}

export async function regeneratePersonality(analysisId: string): Promise<CatPersonality> {
  const response = await request(`/api/v1/analyses/${analysisId}/personality/regenerate`, {
    method: "POST",
  });
  return response.json();
}
