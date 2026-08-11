"use client";

import { RotateCcw, Sparkles } from "lucide-react";
import Image from "next/image";

import { Button } from "@/components/ui/button";

interface ImagePreviewProps {
  previewUrl: string;
  fileName: string;
  onRemove: () => void;
  onAnalyze: () => void;
}

export function ImagePreview({ previewUrl, fileName, onRemove, onAnalyze }: ImagePreviewProps) {
  return (
    <div className="glass flex flex-col items-center gap-6 rounded-3xl p-8 text-center">
      <div className="relative aspect-square w-full max-w-xs overflow-hidden rounded-2xl border border-border">
        <Image
          src={previewUrl}
          alt={`Preview of ${fileName}`}
          fill
          unoptimized
          className="object-cover"
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={onRemove}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          <RotateCcw className="size-4" aria-hidden="true" />
          Choose a different photo
        </button>
        <Button size="lg" className="rounded-full" onClick={onAnalyze}>
          <Sparkles className="size-4" aria-hidden="true" />
          Discover My Cat
        </Button>
      </div>
    </div>
  );
}
