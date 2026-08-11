import { Progress } from "@/components/ui/progress";

/**
 * Deliberately labeled "Model confidence," never "% certainty about
 * your cat's identity" (spec §13) — this is how sure the classifier is
 * in its own top guess, not a claim about ground truth.
 */
export function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Model confidence</span>
        <span className="font-medium tabular-nums">{pct}%</span>
      </div>
      {/* No custom ProgressTrack/Indicator children here — Progress
       * always renders its own default track+indicator *in addition*
       * to any children passed to it (see components/ui/progress.tsx),
       * so supplying one produced two stacked bars. Its default
       * bg-primary indicator already matches the design system's
       * violet accent. */}
      <Progress value={pct} className="mt-1.5" />
      <p className="mt-1.5 text-xs text-muted-foreground">
        How sure the model is in its own top guess — not a certainty claim about your cat&apos;s
        actual breed.
      </p>
    </div>
  );
}
