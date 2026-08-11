import { BadgeCheck, Camera, Fingerprint, Palette, ScanSearch, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const realCapabilities = [
  {
    icon: Camera,
    title: "Breed classification",
    description:
      "A transfer-learning computer vision model predicts breed with a confidence score.",
  },
  {
    icon: Palette,
    title: "Fur color analysis",
    description: "Dominant colors are extracted directly from the image and shown as a palette.",
  },
  {
    icon: ScanSearch,
    title: "Explainable predictions",
    description: "Grad-CAM heatmaps show which parts of the photo drove the prediction.",
  },
  {
    icon: Fingerprint,
    title: "Similarity search",
    description: "Embeddings let you find the most visually similar cats in the collection.",
  },
];

const creativeCapabilities = [
  {
    icon: Sparkles,
    title: "Personality & magic power",
    description: "A playful interpretation generated from the real signals above — not science.",
  },
  {
    icon: BadgeCheck,
    title: "Rarity & collectible card",
    description: "A game-like rarity tier and a shareable card, based on transparent, fun rules.",
  },
];

export function Capabilities() {
  return (
    <section id="capabilities" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          What&apos;s real, what&apos;s magic
        </h2>
        <p className="mt-4 text-muted-foreground">
          We never blur the line between a model&apos;s prediction and a story
          written for fun. Every result on MeowVerse says which one it is.
        </p>
      </div>

      <div className="mt-14 grid grid-cols-1 gap-10 lg:grid-cols-2">
        <div>
          <Badge variant="secondary" className="mb-4 bg-magic-100 text-magic-700 dark:bg-magic-900/50 dark:text-magic-200">
            Real AI prediction
          </Badge>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {realCapabilities.map((cap) => (
              <Card key={cap.title} className="border-magic-200/60 dark:border-magic-800/60">
                <CardHeader>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-magic-100 text-magic-600 dark:bg-magic-900/50 dark:text-magic-300">
                    <cap.icon className="size-4.5" aria-hidden="true" />
                  </div>
                  <CardTitle className="mt-2 text-base">{cap.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{cap.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <Badge variant="secondary" className="mb-4 bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200">
            AI-generated fun content
          </Badge>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {creativeCapabilities.map((cap) => (
              <Card key={cap.title} className="border-peach-200/60 dark:border-peach-700/40">
                <CardHeader>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-peach-100 text-peach-600 dark:bg-peach-600/20 dark:text-peach-200">
                    <cap.icon className="size-4.5" aria-hidden="true" />
                  </div>
                  <CardTitle className="mt-2 text-base">{cap.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{cap.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Playful and collectible by design — never a scientific or veterinary claim.
          </p>
        </div>
      </div>
    </section>
  );
}
