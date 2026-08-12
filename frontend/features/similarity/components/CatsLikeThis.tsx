"use client";

import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchSimilarCats, SimilarityApiError } from "@/services/similarity";

import { HowSimilarityWorks } from "./HowSimilarityWorks";
import { SimilarCatCard } from "./SimilarCatCard";

const LOADING_MESSAGES = [
  "Searching the Cat Universe...",
  "Finding your cat's lookalikes...",
  "Sniffing out similar whiskers...",
];

function useRotatingLoadingMessage(active: boolean): string {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % LOADING_MESSAGES.length);
    }, 1800);
    return () => clearInterval(timer);
  }, [active]);
  return LOADING_MESSAGES[index];
}

interface CatsLikeThisProps {
  /** Null when the analysis couldn't be persisted — similarity search
   * needs a stable id to look up, same reasoning as story generation. */
  analysisId: string | null;
}

export function CatsLikeThis({ analysisId }: CatsLikeThisProps) {
  const query = useQuery({
    queryKey: ["similar-cats", analysisId],
    queryFn: () => fetchSimilarCats(analysisId as string, { k: 6 }),
    enabled: analysisId !== null,
  });
  const loadingMessage = useRotatingLoadingMessage(query.isLoading);

  if (analysisId === null) return null;

  return (
    <section className="mx-auto mt-10 w-full max-w-5xl px-4 text-center sm:px-6">
      <h2 className="font-heading text-xl font-bold">Cats Like This 🐾</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Discover cats from the MeowVerse that share a similar visual appearance.
      </p>

      {query.isLoading && (
        <p className="mt-8 flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="size-4 animate-pulse text-magic-400" aria-hidden="true" />
          {loadingMessage}
        </p>
      )}

      {query.isError && (
        <p className="mt-8 text-sm text-destructive" role="alert">
          {query.error instanceof SimilarityApiError
            ? query.error.message
            : "The Cat Universe is taking a nap. Try again soon."}
        </p>
      )}

      {query.data && query.data.search_mode === "unavailable" && (
        <p className="mt-8 text-sm text-muted-foreground">
          Visual similarity isn&apos;t available for this cat right now.
        </p>
      )}

      {query.data &&
        query.data.search_mode === "embedding" &&
        query.data.similar_cats.length === 0 && (
          <p className="mt-8 text-sm text-muted-foreground">
            Your cat might be one of a kind. 🐾
          </p>
        )}

      {query.data && query.data.similar_cats.length > 0 && (
        <>
          <p className="mt-6 text-sm italic text-muted-foreground">
            Your cat has some friends in the universe...
          </p>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {query.data.similar_cats.map((cat) => (
              <SimilarCatCard key={cat.analysis_id} cat={cat} />
            ))}
          </div>
        </>
      )}

      {query.data && query.data.search_mode === "embedding" && <HowSimilarityWorks />}
    </section>
  );
}
