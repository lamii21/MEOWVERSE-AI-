import type { User } from "@/types/user";

export type AuthErrorKind =
  | "validation"
  | "conflict"
  | "unauthorized"
  | "rate_limited"
  | "server"
  | "network";

export class AuthApiError extends Error {
  kind: AuthErrorKind;

  constructor(message: string, kind: AuthErrorKind) {
    super(message);
    this.name = "AuthApiError";
    this.kind = kind;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    // `credentials: "include"` is required on every auth call — the
    // session lives in an httpOnly cookie, and the frontend/backend run
    // on different ports even in local dev, so fetch would otherwise
    // drop it as a cross-origin request.
    return await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  } catch {
    throw new AuthApiError("The Cat Universe is taking a nap. Try again soon.", "network");
  }
}

async function detailOf(response: Response): Promise<string | undefined> {
  const body = await response.json().catch(() => null);
  return body?.detail;
}

export async function register(
  email: string,
  password: string,
  displayName: string,
): Promise<User> {
  const response = await request("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });

  if (response.status === 409) {
    throw new AuthApiError((await detailOf(response)) ?? "That email is already registered.", "conflict");
  }
  if (response.status === 422) {
    throw new AuthApiError(
      (await detailOf(response)) ?? "Please double-check your details and try again.",
      "validation",
    );
  }
  if (response.status === 429) {
    throw new AuthApiError("Too many attempts — please wait a moment and try again.", "rate_limited");
  }
  if (!response.ok) {
    throw new AuthApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}

export async function login(email: string, password: string): Promise<User> {
  const response = await request("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (response.status === 401) {
    throw new AuthApiError("Incorrect email or password.", "unauthorized");
  }
  if (response.status === 429) {
    throw new AuthApiError("Too many attempts — please wait a moment and try again.", "rate_limited");
  }
  if (!response.ok) {
    throw new AuthApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}

export async function logout(): Promise<void> {
  const response = await request("/api/v1/auth/logout", { method: "POST" });
  if (!response.ok && response.status !== 204) {
    throw new AuthApiError("Couldn't sign out — please try again.", "server");
  }
}

export async function fetchCurrentUser(): Promise<User | null> {
  const response = await request("/api/v1/auth/me");
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new AuthApiError("The Cat Universe is taking a nap. Try again soon.", "server");
  }
  return response.json();
}

export async function updateCurrentUser(data: {
  display_name?: string;
  avatar_url?: string;
}): Promise<User> {
  const response = await request("/api/v1/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new AuthApiError("Couldn't update your profile — please try again.", "server");
  }
  return response.json();
}
