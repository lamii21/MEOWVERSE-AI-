"use client";

import { useSyncExternalStore } from "react";

const SAVED_KEY = "meowverse:saved-cats";
const SAVED_CHANGED_EVENT = "meowverse:saved-cats-changed";

function readSaved(): string[] {
  try {
    const raw = window.localStorage.getItem(SAVED_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function writeSaved(next: string[]) {
  window.localStorage.setItem(SAVED_KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(SAVED_CHANGED_EVENT));
}

function subscribe(onChange: () => void) {
  window.addEventListener(SAVED_CHANGED_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(SAVED_CHANGED_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * "Save" doubles as the Cat Card's favorite mechanic (spec §7 listed
 * Save and Favorite separately, but with no collection page to view
 * either against yet — Phase 10 — two divergent local-only flags would
 * be dead-end UI; this is the single, honest local bookmark both
 * collapse into). Same `useSyncExternalStore` pattern as the Phase 7
 * story-favorite hook, for the same SSR-hydration-safety reason.
 */
export function useSavedCat(analysisId: string | null) {
  const isSaved = useSyncExternalStore(
    subscribe,
    () => (analysisId ? readSaved().includes(analysisId) : false),
    () => false,
  );

  const toggle = () => {
    if (!analysisId) return;
    const current = readSaved();
    const next = current.includes(analysisId)
      ? current.filter((id) => id !== analysisId)
      : [...current, analysisId];
    writeSaved(next);
  };

  return [isSaved, toggle] as const;
}
