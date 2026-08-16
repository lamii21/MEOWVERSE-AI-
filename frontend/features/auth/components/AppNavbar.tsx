"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth, useLogout } from "@/hooks/use-auth";

const GUEST_LINKS = [
  { href: "/", label: "Home" },
  { href: "/discover", label: "Discover" },
  { href: "/explore", label: "Explore" },
];

const AUTHED_LINKS = [
  { href: "/", label: "Home" },
  { href: "/discover", label: "Discover" },
  { href: "/explore", label: "Explore" },
  { href: "/collection", label: "My Cats" },
  { href: "/achievements", label: "Achievements" },
  { href: "/profile", label: "Profile" },
];

function initialsOf(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "?";
}

export function AppNavbar() {
  const { user, status } = useAuth();
  const logout = useLogout();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const links = user ? AUTHED_LINKS : GUEST_LINKS;

  async function handleLogout() {
    await logout.mutateAsync();
    // A hard navigation, not router.push: logging out from a protected
    // page (e.g. /settings) races a client-side push against
    // RequireAuth's own "guest on a protected route" redirect effect,
    // which fires the instant the auth query cache clears — that race
    // was observed landing on /login?next=/settings right after
    // logging out, which is a confusing thing to show someone who just
    // asked to sign out. A full navigation sidesteps the race and also
    // guarantees every last bit of client state is reset, not just
    // whatever queryClient.removeQueries() catches.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/";
  }

  return (
    <header className="sticky top-0 z-40 w-full">
      <nav className="glass mx-auto mt-4 flex max-w-6xl items-center justify-between rounded-2xl px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-semibold">
          <span aria-hidden="true">🐾</span>
          MeowVerse AI
        </Link>

        <ul className="hidden items-center gap-6 text-sm font-medium text-muted-foreground md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <Link href={link.href} className="transition-colors hover:text-foreground">
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2">
          {status === "loading" && <div className="size-8" aria-hidden="true" />}

          {status === "guest" && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="hidden rounded-full sm:inline-flex"
                nativeButton={false}
                render={<Link href="/login" />}
              >
                Log in
              </Button>
              <Button
                size="sm"
                className="rounded-full"
                nativeButton={false}
                render={<Link href="/register" />}
              >
                Sign up
              </Button>
            </>
          )}

          {status === "authenticated" && user && (
            <>
              <Button
                variant="ghost"
                size="icon-sm"
                className="hidden sm:inline-flex"
                onClick={handleLogout}
                disabled={logout.isPending}
                title="Log out"
              >
                <LogOut className="size-4" aria-hidden="true" />
                <span className="sr-only">Log out</span>
              </Button>
              <Link href="/profile" aria-label="Your profile" className="hidden sm:block">
                <Avatar size="sm">
                  {user.avatar_url && <AvatarImage src={user.avatar_url} alt="" />}
                  <AvatarFallback>{initialsOf(user.display_name)}</AvatarFallback>
                </Avatar>
              </Link>
            </>
          )}

          {status !== "loading" && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={() => setMobileMenuOpen((v) => !v)}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-nav-menu"
            >
              {mobileMenuOpen ? (
                <X className="size-4" aria-hidden="true" />
              ) : (
                <Menu className="size-4" aria-hidden="true" />
              )}
              <span className="sr-only">Menu</span>
            </Button>
          )}
        </div>
      </nav>

      {mobileMenuOpen && (
        <div
          id="mobile-nav-menu"
          className="glass mx-auto mt-2 flex max-w-6xl flex-col gap-1 rounded-2xl p-3 text-sm font-medium md:hidden"
        >
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              onClick={() => setMobileMenuOpen(false)}
            >
              {link.label}
            </Link>
          ))}

          {status === "guest" && (
            <Link
              href="/login"
              className="rounded-lg px-3 py-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              onClick={() => setMobileMenuOpen(false)}
            >
              Log in
            </Link>
          )}

          {status === "authenticated" && user && (
            <>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-left text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                disabled={logout.isPending}
              >
                Log out
              </button>
            </>
          )}
        </div>
      )}
    </header>
  );
}
