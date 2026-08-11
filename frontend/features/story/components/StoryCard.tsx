"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Check, Download, Heart, Link2, Printer, RefreshCw, Sparkles } from "lucide-react";
import { useState, useSyncExternalStore } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { STORY_STYLE_OPTIONS } from "@/types/story";

import type { StoryMode, StoryResponse } from "@/types/story";

const FAVORITES_KEY = "meowverse:favorite-stories";
const FAVORITES_CHANGED_EVENT = "meowverse:favorites-changed";

function readFavorites(): string[] {
  try {
    const raw = window.localStorage.getItem(FAVORITES_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function writeFavorites(next: string[]) {
  window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
  // localStorage's own "storage" event only fires in *other* tabs, not
  // the one that made the write — dispatch a same-tab event so
  // useSyncExternalStore's subscribers re-check the snapshot.
  window.dispatchEvent(new Event(FAVORITES_CHANGED_EVENT));
}

function subscribeToFavorites(onChange: () => void) {
  window.addEventListener(FAVORITES_CHANGED_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(FAVORITES_CHANGED_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/**
 * localStorage isn't available during SSR, so a plain useState/useEffect
 * pair renders "not favorited" on the server and (possibly) "favorited"
 * after the client mounts — a hydration mismatch. useSyncExternalStore
 * is the primitive React ships specifically for this: it takes an
 * explicit server snapshot (`false`, always correct pre-hydration) and
 * only reads the real client value once mounted.
 */
function useIsFavorite(storyId: string) {
  const isFavorite = useSyncExternalStore(
    subscribeToFavorites,
    () => readFavorites().includes(storyId),
    () => false,
  );

  const toggle = () => {
    const current = readFavorites();
    const next = current.includes(storyId)
      ? current.filter((id) => id !== storyId)
      : [...current, storyId];
    writeFavorites(next);
  };

  return [isFavorite, toggle] as const;
}

/**
 * Deliberately reuses ProfileModeBadge's wording and peach palette (see
 * features/results/components/ResultExperience.tsx) — a story is the
 * same class of content (AI-generated / creative), never a "prediction,"
 * so it gets the same honest, distinct treatment as the profile badge.
 */
function StoryModeBadge({ mode }: { mode: StoryMode }) {
  return mode === "generated" ? (
    <Badge
      variant="secondary"
      className="gap-1 bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200"
    >
      <Sparkles className="size-3" aria-hidden="true" />
      AI-generated
    </Badge>
  ) : (
    <Badge variant="outline" className="gap-1">
      <Sparkles className="size-3" aria-hidden="true" />
      Offline demo story
    </Badge>
  );
}

/**
 * The quote is rendered wrapped in our own curly quotes below — strip
 * any quote marks the content already carries (demo templates used to
 * include them, and an LLM-generated quote might too) so it's never
 * double-quoted.
 */
function stripQuoteMarks(text: string): string {
  return text.trim().replace(/^["'“”‘’]+/, "").replace(/["'“”‘’]+$/, "");
}

function downloadStoryAsText(story: StoryResponse) {
  const lines = [
    story.story.title,
    story.story.subtitle,
    "",
    story.story.opening,
    "",
    ...story.story.chapters.flatMap((c) => [`Chapter ${c.chapter_number}: ${c.title}`, c.text, ""]),
    story.story.ending,
    "",
    `Moral: ${story.story.moral}`,
    `"${stripQuoteMarks(story.story.quote)}"`,
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${story.story.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "cat-story"}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const containerVariants = (reduceMotion: boolean | null): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: reduceMotion ? 0 : 0.18 } },
});

const itemVariants = (reduceMotion: boolean | null): Variants =>
  reduceMotion
    ? { hidden: { opacity: 1 }, show: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: 14 },
        show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
      };

interface StoryCardProps {
  story: StoryResponse;
  catImageUrl?: string | null;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  /** Marks the story public on the backend. Omitted on the read-only
   * public /story/[id] page, where it's already public. */
  onShare?: () => Promise<void>;
}

export function StoryCard({ story, catImageUrl, onRegenerate, isRegenerating, onShare }: StoryCardProps) {
  const reduceMotion = useReducedMotion();
  const [isFavorite, toggleFavorite] = useIsFavorite(story.id);
  const [copyState, setCopyState] = useState<"idle" | "sharing" | "copied">("idle");
  const styleOption = STORY_STYLE_OPTIONS.find((o) => o.value === story.style);

  const handleShare = async () => {
    setCopyState("sharing");
    try {
      if (onShare) await onShare();
      const url = `${window.location.origin}/story/${story.id}`;
      await navigator.clipboard.writeText(url);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 2500);
    } catch {
      setCopyState("idle");
    }
  };

  return (
    <motion.article
      variants={containerVariants(reduceMotion)}
      initial="hidden"
      animate="show"
      className="glass w-full max-w-lg rounded-3xl p-6 text-left sm:p-8"
    >
      <motion.div variants={itemVariants(reduceMotion)} className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {styleOption && (
            <span className="text-xl" aria-hidden="true">
              {styleOption.emoji}
            </span>
          )}
          <Badge variant="outline">{styleOption?.title ?? story.style}</Badge>
        </div>
        <StoryModeBadge mode={story.story_mode} />
      </motion.div>

      {catImageUrl && (
        <motion.img
          variants={itemVariants(reduceMotion)}
          src={catImageUrl}
          alt=""
          className="mx-auto mt-4 size-20 rounded-full object-cover ring-2 ring-magic-300"
        />
      )}

      <motion.h2
        variants={itemVariants(reduceMotion)}
        className="mt-4 text-center font-heading text-2xl font-bold text-gradient-magic"
      >
        {story.story.title}
      </motion.h2>
      <motion.p
        variants={itemVariants(reduceMotion)}
        className="mt-1 text-center text-sm italic text-muted-foreground"
      >
        {story.story.subtitle}
      </motion.p>

      <motion.p variants={itemVariants(reduceMotion)} className="mt-5 text-sm leading-relaxed">
        {story.story.opening}
      </motion.p>

      <div className="mt-5 flex flex-col gap-4">
        {story.story.chapters.map((chapter) => (
          <motion.div key={chapter.chapter_number} variants={itemVariants(reduceMotion)}>
            <h3 className="font-heading text-sm font-semibold text-magic-600 dark:text-magic-300">
              Chapter {chapter.chapter_number}: {chapter.title}
            </h3>
            <p className="mt-1 text-sm leading-relaxed">{chapter.text}</p>
          </motion.div>
        ))}
      </div>

      <motion.p variants={itemVariants(reduceMotion)} className="mt-5 text-sm leading-relaxed">
        {story.story.ending}
      </motion.p>

      <motion.div variants={itemVariants(reduceMotion)}>
        <Separator className="my-5" />
        <p className="text-sm font-medium">{story.story.moral}</p>
        <p className="mt-2 text-center text-sm italic text-muted-foreground">
          “{stripQuoteMarks(story.story.quote)}”
        </p>
      </motion.div>

      <motion.div
        variants={itemVariants(reduceMotion)}
        className="mt-6 flex flex-wrap items-center justify-center gap-2 border-t border-border pt-5"
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleFavorite}
          aria-pressed={isFavorite}
          className="gap-1.5"
        >
          <Heart
            className={cn("size-4", isFavorite && "fill-destructive text-destructive")}
            aria-hidden="true"
          />
          {isFavorite ? "Favorited" : "Favorite"}
        </Button>
        <Button variant="ghost" size="sm" onClick={handleShare} className="gap-1.5">
          {copyState === "copied" ? (
            <Check className="size-4" aria-hidden="true" />
          ) : (
            <Link2 className="size-4" aria-hidden="true" />
          )}
          {copyState === "copied" ? "Link copied!" : copyState === "sharing" ? "Sharing..." : "Share"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => downloadStoryAsText(story)} className="gap-1.5">
          <Download className="size-4" aria-hidden="true" />
          Download
        </Button>
        <Button variant="ghost" size="sm" onClick={() => window.print()} className="gap-1.5">
          <Printer className="size-4" aria-hidden="true" />
          Print
        </Button>
        {onRegenerate && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="gap-1.5"
          >
            <RefreshCw className={cn("size-4", isRegenerating && "animate-spin")} aria-hidden="true" />
            {isRegenerating ? "Regenerating..." : "Regenerate"}
          </Button>
        )}
      </motion.div>
    </motion.article>
  );
}
