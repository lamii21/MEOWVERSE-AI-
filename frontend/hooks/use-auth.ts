"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as authService from "@/services/auth";

import type { User } from "@/types/user";

/**
 * Centralizes auth state in TanStack Query's cache (already wired up
 * app-wide in app/providers.tsx) rather than a hand-rolled Context —
 * `useCurrentUser`'s query result *is* the shared client state, so
 * every component reading it automatically stays in sync, and
 * login/register/logout just update that one cache entry. Keeps auth
 * logic in this one file instead of scattered across components.
 */
const ME_QUERY_KEY = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: authService.fetchCurrentUser,
    staleTime: 60_000,
    retry: false,
  });
}

/** Convenience wrapper — most components just want "who's signed in,
 * and do we know yet." */
export function useAuth() {
  const { data, isLoading } = useCurrentUser();
  const user = data ?? null;
  return {
    user,
    status: isLoading ? ("loading" as const) : user ? ("authenticated" as const) : ("guest" as const),
  };
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      email,
      password,
      displayName,
    }: {
      email: string;
      password: string;
      displayName: string;
    }) => authService.register(email, password, displayName),
    onSuccess: (user: User) => {
      queryClient.setQueryData(ME_QUERY_KEY, user);
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authService.login(email, password),
    onSuccess: (user: User) => {
      queryClient.setQueryData(ME_QUERY_KEY, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.logout,
    onSuccess: () => {
      queryClient.setQueryData(ME_QUERY_KEY, null);
      // Collection/stats/achievements are all per-user — dropping every
      // cached query on logout is simpler and safer than trying to
      // enumerate which ones might leak the previous user's data.
      queryClient.removeQueries();
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.updateCurrentUser,
    onSuccess: (user: User) => {
      queryClient.setQueryData(ME_QUERY_KEY, user);
    },
  });
}
