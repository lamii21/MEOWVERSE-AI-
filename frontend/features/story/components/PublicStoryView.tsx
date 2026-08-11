"use client";

import Link from "next/link";

import { StoryCard } from "./StoryCard";

import type { StoryResponse } from "@/types/story";

export function PublicStoryView({ story }: { story: StoryResponse }) {
  return (
    <div className="flex w-full flex-col items-center gap-4">
      <p className="text-xs text-muted-foreground">Shared from MeowVerse AI</p>
      <StoryCard story={story} />
      <Link href="/discover" className="text-sm text-magic-600 underline-offset-4 hover:underline dark:text-magic-300">
        Discover your own cat&apos;s story
      </Link>
    </div>
  );
}
