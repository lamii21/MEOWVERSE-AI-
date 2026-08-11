import Link from "next/link";

import { Button } from "@/components/ui/button";

import { CatMascot } from "./CatMascot";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="bg-aurora absolute inset-0 -z-10" aria-hidden="true" />

      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 py-20 sm:px-6 md:grid-cols-2 md:py-28">
        <div className="flex flex-col items-center text-center md:items-start md:text-left">
          <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-magic-200 bg-magic-50 px-3 py-1 text-xs font-medium text-magic-700 dark:border-magic-800 dark:bg-magic-900/40 dark:text-magic-200">
            ✨ Computer vision meets storytelling
          </span>

          <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Every cat has{" "}
            <span className="text-gradient-magic">a story.</span>
          </h1>

          <p className="mt-6 max-w-md text-lg text-muted-foreground">
            Turn a simple photo into a magical AI-powered cat universe —
            real breed analysis, plus a personality only your cat could have.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button
              size="lg"
              className="rounded-full text-base"
              nativeButton={false}
              render={<Link href="/discover" />}
            >
              Discover My Cat
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="rounded-full text-base"
              nativeButton={false}
              render={<a href="#how-it-works" />}
            >
              See how it works
            </Button>
          </div>
        </div>

        <CatMascot />
      </div>
    </section>
  );
}
