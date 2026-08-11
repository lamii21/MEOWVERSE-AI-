import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authService from "@/services/auth";

import { useAuth, useLogin, useLogout, useRegister } from "./use-auth";

import type { ReactNode } from "react";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return {
    ...actual,
    fetchCurrentUser: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  };
});

const FAKE_USER = {
  id: "u1",
  email: "cat@example.com",
  display_name: "Cat Fan",
  avatar_url: null,
  created_at: "2026-01-01T00:00:00Z",
};

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return { Wrapper, queryClient };
}

beforeEach(() => {
  vi.mocked(authService.fetchCurrentUser).mockReset();
  vi.mocked(authService.login).mockReset();
  vi.mocked(authService.register).mockReset();
  vi.mocked(authService.logout).mockReset();
});

describe("useAuth", () => {
  it("reports guest status when there is no session", async () => {
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(null);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.status).toBe("guest"));
    expect(result.current.user).toBeNull();
  });

  it("reports authenticated status with the current user", async () => {
    vi.mocked(authService.fetchCurrentUser).mockResolvedValue(FAKE_USER);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useAuth(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.status).toBe("authenticated"));
    expect(result.current.user).toEqual(FAKE_USER);
  });
});

describe("useLogin / useRegister / useLogout", () => {
  it("useLogin populates the current-user cache on success", async () => {
    vi.mocked(authService.login).mockResolvedValue(FAKE_USER);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    await act(async () => {
      await result.current.mutateAsync({ email: "cat@example.com", password: "hunter2000" });
    });

    expect(authService.login).toHaveBeenCalledWith("cat@example.com", "hunter2000");
  });

  it("useRegister populates the current-user cache on success", async () => {
    vi.mocked(authService.register).mockResolvedValue(FAKE_USER);
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(() => useRegister(), { wrapper: Wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        email: "cat@example.com",
        password: "hunter2000",
        displayName: "Cat Fan",
      });
    });

    expect(authService.register).toHaveBeenCalledWith("cat@example.com", "hunter2000", "Cat Fan");
  });

  it("useLogout clears cached queries", async () => {
    vi.mocked(authService.logout).mockResolvedValue(undefined);
    const { Wrapper, queryClient } = makeWrapper();
    const removeSpy = vi.spyOn(queryClient, "removeQueries");
    const { result } = renderHook(() => useLogout(), { wrapper: Wrapper });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(removeSpy).toHaveBeenCalled();
  });
});
