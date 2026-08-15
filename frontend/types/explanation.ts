export type ExplanationMode = "trained" | "unavailable";

export interface CatExplanation {
  mode: ExplanationMode;
  /** Set only when `mode === "unavailable"` — a short, honest reason
   * (e.g. "Grad-CAM requires the trained breed model."), never a
   * stack trace. */
  reason: string | null;
  method: "grad-cam" | null;
  target_class: string | null;
  target_class_index: number | null;
  /** Classification confidence for `target_class` — NOT Grad-CAM
   * intensity. These are different concepts and must never be
   * visually conflated in the UI. */
  confidence: number | null;
  target_layer: string | null;
  breed_model_version: string | null;
  heatmap_url: string | null;
  overlay_url: string | null;
  image_width: number | null;
  image_height: number | null;
  created_at: string | null;
  /** True when this response reused a previously-generated
   * explanation instead of running Grad-CAM again just now. */
  cached: boolean;
}

export interface ExplanationRequest {
  target_class?: string;
}
