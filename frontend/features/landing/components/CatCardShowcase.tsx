import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const swatches = ["#EAD9C9", "#C9A98C", "#4B3A2F"];

export function CatCardShowcase() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="font-heading text-3xl font-bold tracking-tight sm:text-4xl">
          A card worth collecting
        </h2>
        <p className="mt-4 text-muted-foreground">
          Every analysis becomes a shareable, collectible cat card.
        </p>
      </div>

      <div className="mt-12 flex flex-col items-center">
        <div className="relative w-full max-w-sm rounded-3xl border border-magic-200/60 bg-gradient-to-b from-magic-50 to-peach-50 p-6 text-neutral-900 shadow-xl">
          <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-neutral-900 text-neutral-50">
            Example card — not a real analysis
          </Badge>

          <div className="mx-auto flex aspect-square w-40 items-center justify-center rounded-2xl bg-gradient-to-br from-magic-400 to-magic-600 text-5xl">
            🐱
          </div>

          <div className="mt-4 text-center">
            <h3 className="font-heading text-xl font-semibold">Sir Whiskerton</h3>
            <p className="text-sm text-neutral-500">British Shorthair</p>
          </div>

          <div className="mt-4 flex items-center justify-center gap-2">
            <Badge variant="secondary" className="bg-magic-100 text-magic-700">
              Epic
            </Badge>
            <Badge variant="outline" className="gap-1 border-neutral-300 text-neutral-700">
              <Sparkles className="size-3" aria-hidden="true" />
              Nap Sorcery
            </Badge>
          </div>

          <Separator className="my-4 bg-neutral-900/10" />

          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-500">Fur palette</span>
            <div className="flex gap-1.5">
              {swatches.map((hex) => (
                <span
                  key={hex}
                  className="size-5 rounded-full border border-black/10"
                  style={{ backgroundColor: hex }}
                  title={hex}
                />
              ))}
            </div>
          </div>

          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-neutral-500">Breed confidence</span>
            <span className="font-medium">91%</span>
          </div>
        </div>
      </div>
    </section>
  );
}
