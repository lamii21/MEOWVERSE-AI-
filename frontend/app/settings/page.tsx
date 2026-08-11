"use client";

import { AlertCircle, Check, LogOut } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { useAuth, useLogout, useUpdateProfile } from "@/hooks/use-auth";
import { AuthApiError } from "@/services/auth";

/** RequireAuth (the only thing that renders this) doesn't mount its
 * children until `status === "authenticated"`, so `user` is always
 * already non-null by the time this component's very first render
 * happens — no effect needed to "catch up" `displayName` once the
 * user loads, unlike a component that could render before auth
 * resolves. */
function SettingsContent() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const logout = useLogout();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [saved, setSaved] = useState(false);

  if (!user) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaved(false);
    try {
      await updateProfile.mutateAsync({ display_name: displayName });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      // surfaced via updateProfile.error
    }
  }

  async function handleLogout() {
    await logout.mutateAsync();
    // Hard navigation, not router.push — see AppNavbar's handleLogout
    // for why (a real race with RequireAuth's redirect, found while
    // testing this exact page).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/";
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-8 px-4 py-12">
      <h1 className="font-heading text-2xl font-bold">Settings</h1>

      <form onSubmit={handleSubmit} className="glass flex flex-col gap-4 rounded-3xl p-6">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" value={user.email} disabled />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="display-name">Display name</Label>
          <Input
            id="display-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={60}
          />
        </div>

        {updateProfile.error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>
              {updateProfile.error instanceof AuthApiError
                ? updateProfile.error.message
                : "Couldn't save your changes — please try again."}
            </span>
          </div>
        )}

        <Button type="submit" className="gap-1.5 self-start rounded-full" disabled={updateProfile.isPending}>
          {saved ? (
            <>
              <Check className="size-4" aria-hidden="true" />
              Saved
            </>
          ) : updateProfile.isPending ? (
            "Saving..."
          ) : (
            "Save changes"
          )}
        </Button>
      </form>

      <Separator />

      <Button
        variant="outline"
        className="gap-1.5 self-start rounded-full"
        onClick={handleLogout}
        disabled={logout.isPending}
      >
        <LogOut className="size-4" aria-hidden="true" />
        Log out
      </Button>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <SettingsContent />
    </RequireAuth>
  );
}
