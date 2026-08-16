"use client";

import Link from "next/link";

import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { resolveMediaUrl } from "@/lib/media";

import type { AnalysisResult } from "@/types/analysis";
import type { CatPortrait } from "@/types/portrait";

/** The public `/portrait/[id]` share page (Phase 14 spec §35) — the
 * generated artwork, style, and (only if the parent cat is itself
 * independently public) safe cat-name/breed context. No private data:
 * `CatPortrait` structurally has no email/user_id field to leak, and
 * `catContext`, when present, is already the same public-safe shape
 * `/cat/[id]` renders. */
export function PublicPortraitView({
  portrait,
  catContext,
}: {
  portrait: CatPortrait;
  catContext: AnalysisResult | null;
}) {
  const catName = catContext?.profile.name ?? "This cat";
  const imageUrl = resolveMediaUrl(portrait.image_url);

  return (
    <div className="flex w-full flex-col items-center gap-4">
      <p className="text-xs text-muted-foreground">Shared from MeowVerse AI</p>

      <div className="glass w-full max-w-xs rounded-3xl p-4 text-center">
        <Badge className="mx-auto gap-1 bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200">
          <Sparkles className="size-3" aria-hidden="true" />
          AI-generated artwork
        </Badge>

        <p className="mt-2 text-lg" aria-hidden="true">
          {portrait.style_emoji}
        </p>
        <h1 className="font-heading text-xl font-bold">{portrait.style_name}</h1>
        <p className="text-sm text-muted-foreground">
          {catName}
          {catContext?.breed ? ` · ${catContext.breed.label}` : ""}
        </p>

        {imageUrl && (
          <div className="mx-auto mt-3 max-w-xs overflow-hidden rounded-2xl bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt={`AI-generated ${portrait.style_name.toLowerCase()} artwork of ${catName} — an artistic interpretation, not a photograph.`}
              className="aspect-square w-full object-cover"
            />
          </div>
        )}

        <p className="mt-3 text-xs text-muted-foreground">
          An AI-generated artistic interpretation based on {catName}&apos;s reference photo — not
          an actual photograph.
        </p>
      </div>

      <Link
        href="/discover"
        className="text-sm text-magic-600 underline-offset-4 hover:underline dark:text-magic-300"
      >
        Create your own cat&apos;s portrait
      </Link>
    </div>
  );
}
