"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";

/**
 * Client-side route protection — this app has no server-rendered auth
 * gate (every existing page here is a Client Component, and the
 * session lives in an httpOnly cookie the server component tree isn't
 * currently wired to read), so this trades a brief loading flash for
 * consistency with how every other page in this codebase already
 * works, rather than introducing a second, server-side auth pattern
 * for just three pages.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "guest") {
      router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
    }
  }, [status, router]);

  if (status === "loading" || status === "guest") {
    return (
      <div className="flex flex-1 items-center justify-center py-24" role="status" aria-live="polite">
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    );
  }

  if (!user) return null;
  return <>{children}</>;
}
