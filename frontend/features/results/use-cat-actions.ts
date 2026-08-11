"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "@/hooks/use-auth";
import { pushGamificationEvent } from "@/lib/discovery-toast-store";
import { favoriteAnalysis, saveAnalysis, unfavoriteAnalysis } from "@/services/analyses";

import type { AnalysisResult } from "@/types/analysis";

/**
 * Centralizes the Save/Favorite backend calls + optimistic UI (Phase 9
 * spec §13: "update optimistically when safe... handle rollback if the
 * API fails") in one hook, shared by every place a Cat Card can appear
 * (fresh analysis, collection grid, public share page) instead of
 * duplicating mutation logic per call site.
 */
export function useCatActions(initial: AnalysisResult) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [result, setResult] = useState(initial);
  // Adjusts local state when the `initial` prop identity changes (e.g.
  // this same CatCard instance gets reused for a different cat in a
  // list) — computed during render, not an effect; see React's guidance
  // on "adjusting state when a prop changes."
  if (initial.id !== result.id) {
    setResult(initial);
  }

  const [showGuestPrompt, setShowGuestPrompt] = useState(false);

  function invalidateCollectionQueries() {
    queryClient.invalidateQueries({ queryKey: ["collection"] });
    queryClient.invalidateQueries({ queryKey: ["stats"] });
    queryClient.invalidateQueries({ queryKey: ["achievements"] });
  }

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!result.id) throw new Error("This cat hasn't been saved to the database yet.");
      return saveAnalysis(result.id);
    },
    onMutate: () => {
      const previous = result;
      setResult((r) => ({ ...r, owned: true }));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context) setResult(context.previous);
    },
    onSuccess: (updated) => {
      setResult(updated);
      pushGamificationEvent(updated.gamification);
      invalidateCollectionQueries();
    },
  });

  const favoriteMutation = useMutation({
    mutationFn: (next: boolean) => {
      if (!result.id) throw new Error("This cat hasn't been saved to the database yet.");
      return next ? favoriteAnalysis(result.id) : unfavoriteAnalysis(result.id);
    },
    onMutate: (next: boolean) => {
      const previous = result;
      setResult((r) => ({ ...r, is_favorite: next }));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context) setResult(context.previous);
    },
    onSuccess: (updated) => {
      setResult(updated);
      pushGamificationEvent(updated.gamification);
      invalidateCollectionQueries();
    },
  });

  function handleSaveClick() {
    if (!user) {
      setShowGuestPrompt(true);
      return;
    }
    if (result.owned) return;
    saveMutation.mutate();
  }

  function handleToggleFavoriteClick() {
    if (!user) {
      setShowGuestPrompt(true);
      return;
    }
    if (!result.owned) return;
    favoriteMutation.mutate(!result.is_favorite);
  }

  return {
    result,
    isGuest: !user,
    showGuestPrompt,
    setShowGuestPrompt,
    handleSaveClick,
    handleToggleFavoriteClick,
    isSaving: saveMutation.isPending,
    isTogglingFavorite: favoriteMutation.isPending,
  };
}
