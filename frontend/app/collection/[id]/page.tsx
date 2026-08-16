"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { RequireAuth } from "@/features/auth/components/RequireAuth";
import { GradCamExplanation } from "@/features/explanation/components/GradCamExplanation";
import { PersonalityCard } from "@/features/personality/components/PersonalityCard";
import { PortraitStudio } from "@/features/portrait/components/PortraitStudio";
import { CatCard } from "@/features/results/components/CatCard";
import { CatsLikeThis } from "@/features/similarity/components/CatsLikeThis";
import { AnalysisApiError, fetchPublicAnalysis } from "@/services/analyses";

function CollectionDetailContent() {
  const params = useParams<{ id: string }>();
  const query = useQuery({
    queryKey: ["cat", params.id],
    queryFn: () => fetchPublicAnalysis(params.id),
  });

  return (
    <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center gap-6 px-4 py-12">
      <Button
        variant="ghost"
        size="sm"
        className="self-start gap-1.5"
        nativeButton={false}
        render={<Link href="/collection" />}
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to My Cats
      </Button>

      {query.isLoading && <p className="py-16 text-sm text-muted-foreground">Loading...</p>}

      {query.isError && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
          {query.error instanceof AnalysisApiError
            ? query.error.message
            : "The Cat Universe is taking a nap. Try again soon."}
        </div>
      )}

      {query.data && <CatCard result={query.data} />}
      {query.data && <PersonalityCard result={query.data} />}
      {query.data && <PortraitStudio result={query.data} />}
      {query.data && <GradCamExplanation result={query.data} />}
      {query.data && <CatsLikeThis analysisId={query.data.id} />}
    </div>
  );
}

export default function CollectionDetailPage() {
  return (
    <RequireAuth>
      <CollectionDetailContent />
    </RequireAuth>
  );
}
