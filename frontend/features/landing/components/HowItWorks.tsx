import { BookOpenText, Sparkles, Upload, Wand2 } from "lucide-react";

const steps = [
  {
    icon: Upload,
    title: "Upload a photo",
    description: "Drag, drop, or snap a picture of your cat — MeowVerse handles the rest.",
  },
  {
    icon: Wand2,
    title: "AI analyzes it",
    description: "Computer vision detects the cat, predicts breed, and reads fur colors.",
  },
  {
    icon: Sparkles,
    title: "A profile is born",
    description: "Personality, magic power, and rarity are generated from what was found.",
  },
  {
    icon: BookOpenText,
    title: "Read their story",
    description: "A short, wholesome tale written just for your cat's new profile.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          How it works
        </h2>
        <p className="mt-4 text-muted-foreground">
          Four steps between a photo and a fully-realized cat universe.
        </p>
      </div>

      <ol className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step, i) => (
          <li
            key={step.title}
            className="glass relative flex flex-col items-start gap-3 rounded-2xl p-6"
          >
            <span className="absolute right-5 top-5 font-heading text-sm font-semibold text-muted-foreground/50">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="flex size-11 items-center justify-center rounded-xl bg-magic-100 text-magic-600 dark:bg-magic-900/50 dark:text-magic-300">
              <step.icon className="size-5" aria-hidden="true" />
            </div>
            <h3 className="font-heading text-lg font-semibold">{step.title}</h3>
            <p className="text-sm text-muted-foreground">{step.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
