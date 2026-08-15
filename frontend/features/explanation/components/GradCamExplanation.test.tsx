import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { GradCamExplanation } from "./GradCamExplanation";

vi.mock("@/services/explanation", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/explanation")>("@/services/explanation");
  return { ...actual, fetchExplanation: vi.fn() };
});

import { ExplanationApiError, fetchExplanation } from "@/services/explanation";

import type { AnalysisResult } from "@/types/analysis";
import type { CatExplanation } from "@/types/explanation";

function makeResult(overrides: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "analysis-1",
    detected: true,
    breed: { label: "British Shorthair", confidence: 0.91 },
    breed_mode: "trained",
    colors: [],
    colors_mode: "trained",
    embedding_available: true,
    profile: {
      name: "Sable",
      title: "Whisperer of the Air Vents",
      personality: "Mysterious.",
      magic_power: "Vanishing.",
      kingdom: "Shadows",
      favorite_activity: "Patrolling",
      favorite_food: "Whatever",
      favorite_season: "Autumn",
      rarity: "Legendary",
      description: "Independent.",
    },
    profile_mode: "generated",
    is_public: false,
    owned: true,
    is_favorite: false,
    image_url: "/media/cat.jpg",
    gamification: null,
    created_at: "2026-01-01T00:00:00Z",
    has_story: false,
    ...overrides,
  };
}

function makeExplanation(overrides: Partial<CatExplanation> = {}): CatExplanation {
  return {
    mode: "trained",
    reason: null,
    method: "grad-cam",
    target_class: "British Shorthair",
    target_class_index: 4,
    confidence: 0.91,
    target_layer: "features.12",
    breed_model_version: "0.1.0",
    heatmap_url: "/media/heatmap.png",
    overlay_url: "/media/overlay.png",
    image_width: 500,
    image_height: 333,
    created_at: "2026-01-01T00:00:00Z",
    cached: false,
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(fetchExplanation).mockReset();
});

describe("GradCamExplanation", () => {
  it("renders nothing when the analysis has no id", () => {
    const { container } = renderWithQueryClient(
      <GradCamExplanation result={makeResult({ id: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there is no breed prediction at all", () => {
    const { container } = renderWithQueryClient(
      <GradCamExplanation result={makeResult({ breed: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the breed name in the heading and a trigger button, not auto-loaded", () => {
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    expect(screen.getByText("Why MeowVerse thinks this is a British Shorthair")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Why this breed?" })).toBeInTheDocument();
    expect(fetchExplanation).not.toHaveBeenCalled();
  });

  it("shows a loading state after clicking, then the result", async () => {
    let resolvePromise: (value: CatExplanation) => void = () => {};
    vi.mocked(fetchExplanation).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }),
    );
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);

    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    expect(screen.getByText(/Tracing the model's attention/)).toBeInTheDocument();

    resolvePromise(makeExplanation());
    await waitFor(() =>
      expect(screen.getByRole("radiogroup", { name: "Explanation view" })).toBeInTheDocument(),
    );
  });

  it("shows the real prediction confidence, never fabricated", async () => {
    vi.mocked(fetchExplanation).mockResolvedValue(makeExplanation({ confidence: 0.8734 }));
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    await waitFor(() => expect(screen.getByText("87%")).toBeInTheDocument());
  });

  it("defaults to the Overlay view and switches views on click", async () => {
    vi.mocked(fetchExplanation).mockResolvedValue(makeExplanation());
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    await waitFor(() => expect(screen.getByRole("radio", { name: "Overlay" })).toHaveAttribute(
      "aria-checked",
      "true",
    ));

    await userEvent.click(screen.getByRole("radio", { name: "AI Focus" }));
    expect(screen.getByRole("radio", { name: "AI Focus" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "Overlay" })).toHaveAttribute("aria-checked", "false");

    await userEvent.click(screen.getByRole("radio", { name: "Original" }));
    expect(screen.getByRole("radio", { name: "Original" })).toHaveAttribute("aria-checked", "true");
  });

  it("shows an honest unavailable message for a demo-mode analysis, never a fake heatmap", async () => {
    vi.mocked(fetchExplanation).mockResolvedValue(
      makeExplanation({
        mode: "unavailable",
        reason: "Grad-CAM requires the trained breed model.",
        method: null,
        confidence: null,
        heatmap_url: null,
        overlay_url: null,
      }),
    );
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));

    await waitFor(() =>
      expect(screen.getByText("Visual explanation unavailable")).toBeInTheDocument(),
    );
    expect(screen.getByText("Grad-CAM requires the trained breed model.")).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });

  it("shows an error message on failure, never a stack trace", async () => {
    vi.mocked(fetchExplanation).mockRejectedValue(
      new ExplanationApiError("This cat couldn't be found.", "not_found"),
    );
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("This cat couldn't be found."),
    );
  });

  it("includes descriptive alt text naming the predicted breed for accessibility", async () => {
    vi.mocked(fetchExplanation).mockResolvedValue(makeExplanation());
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    await waitFor(() =>
      expect(
        screen.getByAltText(/Grad-CAM overlay highlighting.*British Shorthair/),
      ).toBeInTheDocument(),
    );
  });

  it("shows the scientific disclaimer, not a claim of certainty", async () => {
    vi.mocked(fetchExplanation).mockResolvedValue(makeExplanation());
    renderWithQueryClient(<GradCamExplanation result={makeResult()} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this breed?" }));
    await waitFor(() =>
      expect(screen.getByText(/not proof, certainty, or a causal explanation/)).toBeInTheDocument(),
    );
  });
});
