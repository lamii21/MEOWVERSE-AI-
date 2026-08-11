"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { AnalysisLoader } from "@/features/analyze/components/AnalysisLoader";
import { ResultExperience } from "@/features/results/components/ResultExperience";
import { usePendingUpload } from "@/hooks/use-pending-upload";
import { AnalysisApiError } from "@/services/analyses";

export default function AnalyzePage() {
  const { file, previewUrl, analysisStatus, analysisResult, analysisError, startAnalysis } =
    usePendingUpload();

  if (!file) {
    return (
      <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center gap-4 px-4 py-16 text-center">
        <AlertCircle className="size-8 text-muted-foreground" aria-hidden="true" />
        <h1 className="font-heading text-xl font-semibold">No photo to analyze yet</h1>
        <p className="text-muted-foreground">
          Head back to Discover My Cat and choose a photo to get started.
        </p>
        <Button render={<Link href="/discover" />} nativeButton={false} className="rounded-full">
          Discover My Cat
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-1 flex-col items-center justify-center gap-8 px-4 py-16">
      {(analysisStatus === "idle" || analysisStatus === "pending") && <AnalysisLoader />}

      {analysisStatus === "error" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <div
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>
              {analysisError instanceof AnalysisApiError
                ? analysisError.message
                : "The Cat Universe is taking a nap. Try again soon."}
            </span>
          </div>
          <Button variant="outline" className="rounded-full" onClick={startAnalysis}>
            Try again
          </Button>
        </div>
      )}

      {analysisStatus === "success" && analysisResult && (
        <ResultExperience result={analysisResult} catImageUrl={previewUrl} />
      )}
    </div>
  );
}
