import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { HowMeowVerseKnows } from "@/features/analyze/components/HowMeowVerseKnows";
import { CatsLikeThis } from "@/features/similarity/components/CatsLikeThis";
import { StorySection } from "@/features/story/components/StorySection";

import { CatCard } from "./CatCard";
import { ResultReveal } from "./ResultReveal";

import type { AnalysisResult, PredictionMode, ProfileMode } from "@/types/analysis";

/** Unchanged wording/color from the pre-Phase-8 result summary — real
 * CV predictions must never share styling with AI-generated content. */
function CvModeBadge({ mode }: { mode: PredictionMode }) {
  return mode === "trained" ? (
    <Badge
      variant="secondary"
      className="bg-magic-100 text-magic-700 dark:bg-magic-900/50 dark:text-magic-200"
    >
      Real prediction
    </Badge>
  ) : (
    <Badge variant="outline">Demo mode</Badge>
  );
}

function ProfileModeBadge({ mode }: { mode: ProfileMode }) {
  return mode === "generated" ? (
    <Badge
      variant="secondary"
      className="gap-1 bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200"
    >
      <Sparkles className="size-3" aria-hidden="true" />
      AI-generated
    </Badge>
  ) : (
    <Badge variant="outline" className="gap-1">
      <Sparkles className="size-3" aria-hidden="true" />
      Offline demo content
    </Badge>
  );
}

function SignalModes({ result }: { result: AnalysisResult }) {
  return (
    <dl className="flex flex-col gap-2 text-left text-sm">
      <div className="flex items-center justify-between">
        <dt className="text-muted-foreground">Breed prediction</dt>
        <dd>
          <CvModeBadge mode={result.breed_mode} />
        </dd>
      </div>
      <div className="flex items-center justify-between">
        <dt className="text-muted-foreground">Fur palette</dt>
        <dd>
          <CvModeBadge mode={result.colors_mode} />
        </dd>
      </div>
      <div className="flex items-center justify-between">
        <dt className="text-muted-foreground">Personality &amp; story</dt>
        <dd>
          <ProfileModeBadge mode={result.profile_mode} />
        </dd>
      </div>
    </dl>
  );
}

/**
 * The Phase 8 "MAGICAL EXPERIENCE & CAT CARD" — replaces the Phase 3-7
 * placeholder result summary. Orchestrates the cinematic reveal, the
 * collectible Cat Card, and (unchanged in substance, just re-homed and
 * visually regrouped) the Phase 6/7 real-vs-generated badges,
 * transparency accordion, and story section.
 */
export function ResultExperience({
  result,
  catImageUrl,
}: {
  result: AnalysisResult;
  catImageUrl?: string | null;
}) {
  return (
    <ResultReveal catImageUrl={catImageUrl}>
      {(interactive) => (
        <>
          <div className="mx-auto flex w-full max-w-5xl flex-col items-center gap-8 lg:flex-row lg:items-start lg:justify-center">
            <div className="flex justify-center lg:sticky lg:top-8 lg:shrink-0">
              <CatCard result={result} catImageUrl={catImageUrl} interactive={interactive} />
            </div>

            <div className="glass w-full max-w-md rounded-3xl p-6 text-center lg:text-left">
              <SignalModes result={result} />

              <div className="mt-4">
                <HowMeowVerseKnows result={result} />
              </div>

              <div id="story-section" className="scroll-mt-8">
                <StorySection analysisId={result.id} catImageUrl={catImageUrl} />
              </div>
            </div>
          </div>

          <CatsLikeThis analysisId={result.id} />
        </>
      )}
    </ResultReveal>
  );
}
