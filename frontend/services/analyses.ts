import type { AnalysisResult } from "@/types/analysis";

export type AnalysisErrorKind = "validation" | "not_found" | "server" | "network";

export class AnalysisApiError extends Error {
  kind: AnalysisErrorKind;

  constructor(message: string, kind: AnalysisErrorKind) {
    super(message);
    this.name = "AnalysisApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function submitAnalysis(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/analyses`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new AnalysisApiError(
      "The Cat Universe is taking a nap. Try again soon.",
      "network",
    );
  }

  if (response.status === 422) {
    const body = await response.json().catch(() => null);
    throw new AnalysisApiError(
      body?.detail ?? "MeowVerse needs a valid image.",
      "validation",
    );
  }

  if (!response.ok) {
    throw new AnalysisApiError(
      "The Cat Universe is taking a nap. Try again soon.",
      "server",
    );
  }

  return response.json();
}

export async function shareAnalysis(analysisId: string): Promise<AnalysisResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/analyses/${analysisId}/share`, { method: "POST" });
  } catch {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }

  if (response.status === 404) {
    throw new AnalysisApiError("This cat couldn't be found.", "not_found");
  }
  if (!response.ok) {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}

export async function fetchPublicAnalysis(analysisId: string): Promise<AnalysisResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/analyses/${analysisId}`);
  } catch {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }

  if (response.status === 404) {
    throw new AnalysisApiError(
      "This cat couldn't be found — it may be private or no longer exists.",
      "not_found",
    );
  }
  if (!response.ok) {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}
