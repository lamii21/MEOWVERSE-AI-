"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

import { submitAnalysis } from "@/services/analyses";
import type { AnalysisResult } from "@/types/analysis";

type AnalysisStatus = "idle" | "pending" | "success" | "error";

interface PendingUploadContextValue {
  file: File | null;
  previewUrl: string | null;
  setFile: (file: File | null) => void;
  analysisStatus: AnalysisStatus;
  analysisResult: AnalysisResult | null;
  analysisError: Error | null;
  startAnalysis: () => void;
}

const PendingUploadContext = createContext<PendingUploadContextValue | null>(null);

/**
 * Holds the in-memory File the user picked on /discover, and drives the
 * analysis submission itself, so both survive the client-side navigation
 * to /analyze regardless of that page's own mount/remount lifecycle.
 *
 * This lives here — not as a useMutation call inside the /analyze page —
 * because a mutation started from a page-local hook is torn down if that
 * page instance unmounts before the request resolves (observed in dev:
 * the App Router can navigate to the same route twice in quick
 * succession, e.g. prefetch + navigate, remounting the page). The
 * provider itself never unmounts across in-app navigation, so the
 * request survives.
 */
export function PendingUploadProvider({ children }: { children: React.ReactNode }) {
  const [file, setFileState] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<Error | null>(null);
  const inFlightFor = useRef<File | null>(null);

  const setFile = useCallback((next: File | null) => {
    setPreviewUrl((prevUrl) => {
      if (prevUrl) URL.revokeObjectURL(prevUrl);
      return next ? URL.createObjectURL(next) : null;
    });
    setFileState(next);
    setAnalysisStatus("idle");
    setAnalysisResult(null);
    setAnalysisError(null);
    inFlightFor.current = null;
  }, []);

  const startAnalysis = useCallback(() => {
    if (!file || inFlightFor.current === file) return;
    inFlightFor.current = file;
    setAnalysisStatus("pending");
    setAnalysisError(null);

    submitAnalysis(file)
      .then((result) => {
        setAnalysisResult(result);
        setAnalysisStatus("success");
      })
      .catch((err) => {
        setAnalysisError(err instanceof Error ? err : new Error("Unknown error"));
        setAnalysisStatus("error");
        // Allow retrying the same file after a failure.
        inFlightFor.current = null;
      });
  }, [file]);

  const value = useMemo(
    () => ({
      file,
      previewUrl,
      setFile,
      analysisStatus,
      analysisResult,
      analysisError,
      startAnalysis,
    }),
    [file, previewUrl, setFile, analysisStatus, analysisResult, analysisError, startAnalysis],
  );

  return (
    <PendingUploadContext.Provider value={value}>{children}</PendingUploadContext.Provider>
  );
}

export function usePendingUpload() {
  const ctx = useContext(PendingUploadContext);
  if (!ctx) throw new Error("usePendingUpload must be used within PendingUploadProvider");
  return ctx;
}
