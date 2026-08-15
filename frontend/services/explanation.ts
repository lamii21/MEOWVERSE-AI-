import type { CatExplanation, ExplanationRequest } from "@/types/explanation";

export type ExplanationApiErrorKind =
  | "not_found"
  | "unauthorized"
  | "invalid_target"
  | "server"
  | "network";

export class ExplanationApiError extends Error {
  kind: ExplanationApiErrorKind;

  constructor(message: string, kind: ExplanationApiErrorKind) {
    super(message);
    this.name = "ExplanationApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchExplanation(
  analysisId: string,
  body: ExplanationRequest = {},
): Promise<CatExplanation> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/analyses/${analysisId}/explanation`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ExplanationApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }

  if (response.status === 404) {
    throw new ExplanationApiError("This cat couldn't be found.", "not_found");
  }
  if (response.status === 401) {
    throw new ExplanationApiError("Please sign in to do that.", "unauthorized");
  }
  if (response.status === 422) {
    throw new ExplanationApiError("That breed isn't recognized.", "invalid_target");
  }
  if (!response.ok) {
    throw new ExplanationApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}
