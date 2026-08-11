import Link from "next/link";

import { Button } from "@/components/ui/button";

export function CtaSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="bg-aurora relative overflow-hidden rounded-3xl border border-magic-200/60 px-6 py-16 text-center dark:border-magic-800/60">
        <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          Ready to meet your cat&apos;s universe?
        </h2>
        <p className="mx-auto mt-4 max-w-md text-muted-foreground">
          It takes one photo. The story is already waiting.
        </p>
        <Button
          size="lg"
          className="mt-8 rounded-full text-base"
          nativeButton={false}
          render={<Link href="/discover" />}
        >
          Discover My Cat
        </Button>
      </div>
    </section>
  );
}
