"use client";

import Link from "next/link";

import { CatCard } from "./CatCard";

import type { AnalysisResult } from "@/types/analysis";

export function PublicCatView({ result }: { result: AnalysisResult }) {
  return (
    <div className="flex w-full flex-col items-center gap-4">
      <p className="text-xs text-muted-foreground">Shared from MeowVerse AI</p>
      <CatCard result={result} />
      <Link
        href="/discover"
        className="text-sm text-magic-600 underline-offset-4 hover:underline dark:text-magic-300"
      >
        Discover your own cat
      </Link>
    </div>
  );
}
