import type { AnalysisResult } from "@/types/analysis";

export type AnalysisErrorKind =
  | "validation"
  | "not_found"
  | "unauthorized"
  | "conflict"
  | "server"
  | "network";

export class AnalysisApiError extends Error {
  kind: AnalysisErrorKind;

  constructor(message: string, kind: AnalysisErrorKind) {
    super(message);
    this.name = "AnalysisApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    // `credentials: "include"` on every call — an authenticated
    // request auto-owns its analysis (Phase 9), and the mutating
    // endpoints below (save/favorite/share/unshare) all require the
    // session cookie regardless.
    return await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  } catch {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
}

async function throwForStatus(response: Response, notFoundMessage: string): Promise<void> {
  if (response.status === 401) {
    throw new AnalysisApiError("Please sign in to do that.", "unauthorized");
  }
  if (response.status === 404) {
    throw new AnalysisApiError(notFoundMessage, "not_found");
  }
  if (response.status === 409) {
    const body = await response.json().catch(() => null);
    throw new AnalysisApiError(body?.detail ?? "That cat has already been saved.", "conflict");
  }
  if (!response.ok) {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
}

export async function submitAnalysis(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await request("/api/v1/analyses", { method: "POST", body: formData });

  if (response.status === 422) {
    const body = await response.json().catch(() => null);
    throw new AnalysisApiError(body?.detail ?? "MeowVerse needs a valid image.", "validation");
  }
  if (!response.ok) {
    throw new AnalysisApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}

export async function fetchPublicAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}`);
  await throwForStatus(response, "This cat couldn't be found — it may be private or no longer exists.");
  return response.json();
}

export async function saveAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}/save`, { method: "POST" });
  await throwForStatus(response, "This cat couldn't be found.");
  return response.json();
}

export async function favoriteAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}/favorite`, { method: "POST" });
  await throwForStatus(response, "This cat couldn't be found.");
  return response.json();
}

export async function unfavoriteAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}/unfavorite`, { method: "POST" });
  await throwForStatus(response, "This cat couldn't be found.");
  return response.json();
}

export async function shareAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}/share`, { method: "POST" });
  await throwForStatus(response, "This cat couldn't be found.");
  return response.json();
}

export async function unshareAnalysis(analysisId: string): Promise<AnalysisResult> {
  const response = await request(`/api/v1/analyses/${analysisId}/unshare`, { method: "POST" });
  await throwForStatus(response, "This cat couldn't be found.");
  return response.json();
}
