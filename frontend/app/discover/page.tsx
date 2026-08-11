"use client";

import { AlertCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Dropzone } from "@/features/upload/components/Dropzone";
import { ImagePreview } from "@/features/upload/components/ImagePreview";
import { usePendingUpload } from "@/hooks/use-pending-upload";
import { validateImageFile } from "@/lib/image-validation";

export default function DiscoverPage() {
  const router = useRouter();
  const { file, previewUrl, setFile, startAnalysis } = usePendingUpload();
  const [error, setError] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  async function handleFileSelected(selected: File) {
    setError(null);
    setIsValidating(true);
    const result = await validateImageFile(selected);
    setIsValidating(false);

    if (!result.valid) {
      setError(result.error ?? "That photo didn't work — try another.");
      return;
    }
    setFile(selected);
  }

  function handleRemove() {
    setFile(null);
    setError(null);
  }

  function handleAnalyze() {
    if (!file) return;
    startAnalysis();
    router.push("/analyze");
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-1 flex-col justify-center px-4 py-16 sm:px-6">
      <div className="mb-10 text-center">
        <h1 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          Discover My Cat
        </h1>
        <p className="mt-3 text-muted-foreground">
          Upload a clear photo of your cat to begin the analysis.
        </p>
      </div>

      {file && previewUrl ? (
        <ImagePreview
          previewUrl={previewUrl}
          fileName={file.name}
          onRemove={handleRemove}
          onAnalyze={handleAnalyze}
        />
      ) : (
        <Dropzone onFileSelected={handleFileSelected} disabled={isValidating} />
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
