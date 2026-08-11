"use client";

import { Camera, ImagePlus, UploadCloud } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface DropzoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export function Dropzone({ onFileSelected, disabled }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a cat photo — drag and drop, or press to browse files"
      onClick={() => fileInputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        "glass flex cursor-pointer flex-col items-center gap-4 rounded-3xl border-2 border-dashed p-12 text-center transition-colors",
        isDragging ? "border-magic-400 bg-magic-50/60 dark:bg-magic-900/20" : "border-border",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <div className="flex size-16 items-center justify-center rounded-2xl bg-magic-100 text-magic-600 dark:bg-magic-900/50 dark:text-magic-300">
        <UploadCloud className="size-7" aria-hidden="true" />
      </div>

      <div>
        <p className="font-heading text-lg font-semibold">Drop your cat&apos;s photo here</p>
        <p className="mt-1 text-sm text-muted-foreground">
          or choose a file — JPEG, PNG, or WebP, up to 10MB
        </p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          <ImagePlus className="size-4" aria-hidden="true" />
          Browse files
        </button>
        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          <Camera className="size-4" aria-hidden="true" />
          Take a photo
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
