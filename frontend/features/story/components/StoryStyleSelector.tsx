"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import { STORY_STYLE_OPTIONS } from "@/types/story";

import type { StoryStyle } from "@/types/story";

interface StoryStyleSelectorProps {
  value: StoryStyle;
  onChange: (style: StoryStyle) => void;
  disabled?: boolean;
}

export function StoryStyleSelector({ value, onChange, disabled }: StoryStyleSelectorProps) {
  return (
    <div role="radiogroup" aria-label="Story style" className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {STORY_STYLE_OPTIONS.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            className={cn(
              "group relative flex flex-col items-start gap-1 rounded-2xl border p-3 text-left transition-all",
              "focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
              "disabled:pointer-events-none disabled:opacity-50",
              selected
                ? "border-magic-400 bg-magic-100/70 ring-2 ring-magic-400 dark:bg-magic-900/40"
                : "border-border bg-background hover:border-magic-300 hover:bg-magic-50 dark:hover:bg-magic-900/20",
            )}
          >
            {selected && (
              <span className="absolute right-2 top-2 flex size-5 items-center justify-center rounded-full bg-magic-500 text-white">
                <Check className="size-3" aria-hidden="true" />
              </span>
            )}
            <span className="text-2xl" aria-hidden="true">
              {option.emoji}
            </span>
            <span className="font-heading text-sm font-semibold">{option.title}</span>
            <span className="text-xs text-muted-foreground">{option.description}</span>
          </button>
        );
      })}
    </div>
  );
}
