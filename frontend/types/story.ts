import type { GamificationEvent } from "@/types/gamification";

export type StoryStyle =
  | "magical_adventure"
  | "cozy_wholesome"
  | "funny_chaotic"
  | "dreamy_emotional"
  | "fantasy_quest";

export interface StoryStyleOption {
  value: StoryStyle;
  emoji: string;
  title: string;
  description: string;
}

export const STORY_STYLE_OPTIONS: StoryStyleOption[] = [
  {
    value: "magical_adventure",
    emoji: "✨",
    title: "Magical Adventure",
    description: "A sparkling quest full of wonder.",
  },
  {
    value: "cozy_wholesome",
    emoji: "🌸",
    title: "Cozy & Wholesome",
    description: "A gentle, heartwarming little tale.",
  },
  {
    value: "funny_chaotic",
    emoji: "😂",
    title: "Funny & Chaotic",
    description: "Silly antics and delightful chaos.",
  },
  {
    value: "dreamy_emotional",
    emoji: "🌙",
    title: "Dreamy & Emotional",
    description: "A soft, wistful, dreamlike story.",
  },
  {
    value: "fantasy_quest",
    emoji: "🧙",
    title: "Fantasy Quest",
    description: "An epic-feeling adventure in miniature.",
  },
];

export interface StoryChapter {
  chapter_number: number;
  title: string;
  text: string;
}

/** AI-generated creative content — same honesty contract as CatProfile. */
export interface CatStory {
  title: string;
  subtitle: string;
  opening: string;
  chapters: StoryChapter[];
  ending: string;
  moral: string;
  quote: string;
}

/** Deliberately not PredictionMode's "demo" | "trained" — a story is
 * never a "prediction," so it can't be labeled with words implying it is. */
export type StoryMode = "demo" | "generated";

export interface StoryResponse {
  id: string;
  analysis_id: string;
  style: StoryStyle;
  story: CatStory;
  story_mode: StoryMode;
  provider: string;
  is_public: boolean;
  created_at: string;
  gamification: GamificationEvent | null;
}
