import { Brain, Palette, Sparkles, Wand2 } from "lucide-react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

import type { AnalysisResult } from "@/types/analysis";

interface KnowsRow {
  icon: typeof Brain;
  label: string;
  source: string;
  detail: string;
}

/**
 * Grouped into two visually distinct sections (spec §12) — this is a
 * major product differentiator, so the split between "we measured
 * this" and "we imagined this" needs to read at a glance, not just be
 * inferable from icon color the way it was pre-Phase-8.
 */
function Group({ title, tone, rows }: { title: string; tone: "real" | "ai"; rows: KnowsRow[] }) {
  return (
    <div>
      <p
        className={
          tone === "real"
            ? "text-xs font-semibold uppercase tracking-wide text-magic-600 dark:text-magic-300"
            : "text-xs font-semibold uppercase tracking-wide text-peach-600 dark:text-peach-300"
        }
      >
        {title}
      </p>
      <ul className="mt-2 flex flex-col gap-3">
        {rows.map((row) => (
          <li key={row.label} className="flex items-start gap-3">
            <div
              className={
                tone === "real"
                  ? "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-magic-100 text-magic-600 dark:bg-magic-900/50 dark:text-magic-300"
                  : "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200"
              }
            >
              <row.icon className="size-3.5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium">
                {row.label} <span className="text-muted-foreground">— {row.source}</span>
              </p>
              <p className="text-xs text-muted-foreground">{row.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function HowMeowVerseKnows({ result }: { result: AnalysisResult }) {
  const real: KnowsRow[] = [
    {
      icon: Brain,
      label: "Breed",
      source: "Computer vision model",
      detail:
        result.breed_mode === "trained"
          ? "A transfer-learning image classifier (MobileNetV3) trained on real cat photos. " +
            "See \"Why this breed?\" below for a real Grad-CAM visual explanation of which " +
            "regions of your photo contributed most to this prediction."
          : "Demo mode right now — no trained model weights were available for this request.",
    },
    {
      icon: Palette,
      label: "Fur colors",
      source: "OpenCV + K-means",
      detail:
        result.colors_mode === "trained"
          ? "Foreground segmentation (GrabCut) then K-means clustering on the actual pixels of your photo."
          : "Demo mode right now — no trained model weights were available for this request.",
    },
    {
      icon: Brain,
      label: "Personality trait scores",
      source: "Deterministic rules engine",
      detail:
        "The 8 trait scores and archetype in the Cat Personality card below are computed by " +
        "documented, non-random rules from the real breed and color signals above — never " +
        "chosen or invented by an AI model. See \"How personality works\" in that card for the " +
        "full breakdown.",
    },
  ];

  const ai: KnowsRow[] = [
    {
      icon: Sparkles,
      label: "Personality story & rarity",
      source: "Generative AI",
      detail:
        "The headline, catchphrase, secret talent and story text in the Cat Personality card " +
        "are written by a large language model from the trait scores above — creative flavor " +
        "only, it cannot change the scores themselves. Rarity is also AI-flavored, not a " +
        "scientific assessment.",
    },
    {
      icon: Wand2,
      label: "Magic power & story",
      source: "Generative AI",
      detail: "Also written by the language model — purely for fun, not a real ability.",
    },
  ];

  return (
    <Accordion className="text-left">
      <AccordionItem value="how-it-works">
        <AccordionTrigger className="text-sm font-medium">
          How MeowVerse knows this
        </AccordionTrigger>
        <AccordionContent>
          <div className="flex flex-col gap-4">
            <Group title="Real computer vision" tone="real" rows={real} />
            <Group title="Generative AI" tone="ai" rows={ai} />
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
