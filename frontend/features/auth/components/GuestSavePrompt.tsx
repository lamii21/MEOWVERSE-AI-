"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function GuestSavePrompt({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const pathname = usePathname();
  const next = encodeURIComponent(pathname || "/discover");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Your little friend deserves a home. 🐾</DialogTitle>
          <DialogDescription>
            Create an account to save this cat to your collection — it&apos;ll be waiting for you
            every time you come back.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            nativeButton={false}
            render={<Link href={`/login?next=${next}`} />}
          >
            Log in
          </Button>
          <Button nativeButton={false} render={<Link href={`/register?next=${next}`} />}>
            Create an account
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
