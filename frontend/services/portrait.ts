import type { CatPortrait, PortraitListResponse, PortraitStyleId } from "@/types/portrait";

export type PortraitApiErrorKind =
  | "validation"
  | "not_found"
  | "unauthorized"
  | "rate_limited"
  | "server"
  | "network";

export class PortraitApiError extends Error {
  kind: PortraitApiErrorKind;

  constructor(message: string, kind: PortraitApiErrorKind) {
    super(message);
    this.name = "PortraitApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  } catch {
    throw new PortraitApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
}

function throwForStatus(response: Response, notFoundMessage: string): void {
  if (response.status === 401) {
    throw new PortraitApiError("Please sign in to do that.", "unauthorized");
  }
  if (response.status === 404) {
    throw new PortraitApiError(notFoundMessage, "not_found");
  }
  if (response.status === 429) {
    throw new PortraitApiError(
      "Too many portraits requested right now — give the Cat Universe a moment to rest.",
      "rate_limited",
    );
  }
  if (!response.ok) {
    throw new PortraitApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
}

export async function fetchPortraits(analysisId: string): Promise<PortraitListResponse> {
  const response = await request(`/api/v1/analyses/${analysisId}/portraits`);
  throwForStatus(response, "We couldn't find that cat's analysis anymore.");
  return response.json();
}

export async function generatePortrait(
  analysisId: string,
  style: PortraitStyleId,
  customization?: string,
  forceNew = false,
): Promise<CatPortrait> {
  const response = await request(`/api/v1/analyses/${analysisId}/portraits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      style,
      customization: customization && customization.length > 0 ? customization : null,
      force_new: forceNew,
    }),
  });

  if (response.status === 422) {
    const body = await response.json().catch(() => null);
    throw new PortraitApiError(
      body?.detail ?? "That portrait request wasn't valid.",
      "validation",
    );
  }
  throwForStatus(response, "We couldn't find that cat's analysis anymore.");
  return response.json();
}

export async function fetchPortrait(portraitId: string): Promise<CatPortrait> {
  const response = await request(`/api/v1/portraits/${portraitId}`);
  throwForStatus(
    response,
    "This portrait couldn't be found — it may be private or no longer exists.",
  );
  return response.json();
}

export async function sharePortrait(portraitId: string): Promise<CatPortrait> {
  const response = await request(`/api/v1/portraits/${portraitId}/share`, { method: "POST" });
  throwForStatus(response, "This portrait couldn't be found.");
  return response.json();
}

export async function unsharePortrait(portraitId: string): Promise<CatPortrait> {
  const response = await request(`/api/v1/portraits/${portraitId}/unshare`, { method: "POST" });
  throwForStatus(response, "This portrait couldn't be found.");
  return response.json();
}
