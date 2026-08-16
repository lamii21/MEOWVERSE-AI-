import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toPng } from "html-to-image";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { PersonalityCard } from "./PersonalityCard";

vi.mock("html-to-image", () => ({ toPng: vi.fn() }));

vi.mock("@/services/personality", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/personality")>("@/services/personality");
  return { ...actual, fetchPersonality: vi.fn(), regeneratePersonality: vi.fn() };
});

import {
  PersonalityApiError,
  fetchPersonality,
  regeneratePersonality,
} from "@/services/personality";

import type { AnalysisResult } from "@/types/analysis";
import type { CatPersonality } from "@/types/personality";

function makeResult(overrides: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "analysis-1",
    detected: true,
    breed: { label: "Abyssinian", confidence: 0.91 },
    breed_mode: "trained",
    colors: [],
    colors_mode: "trained",
    embedding_available: true,
    profile: {
      name: "Luna",
      title: "Keeper of Sunbeams",
      personality: "Warm.",
      magic_power: "Finding sunspots.",
      kingdom: "Sunlit Archives",
      favorite_activity: "Napping",
      favorite_food: "Anything",
      favorite_season: "Summer",
      rarity: "Uncommon",
      description: "Gentle.",
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

function makeTrait(score: number, level: CatPersonality["traits"][string]["level"]) {
  return { score, level, label: `${level} trait`, description: "desc" };
}

function makePersonality(overrides: Partial<CatPersonality> = {}): CatPersonality {
  return {
    id: "personality-1",
    analysis_id: "analysis-1",
    personality_engine_version: "1.0",
    archetype: {
      id: "dreamy_explorer",
      name: "Dreamy Explorer",
      emoji: "🌙",
      short_description: "A wandering dreamer.",
      long_description: "Every unopened door is an invitation.",
      theme_token: "dreamy",
    },
    traits: {
      curiosity: makeTrait(69, "High"),
      playfulness: makeTrait(62, "High"),
      calmness: makeTrait(51, "Balanced"),
      cuddliness: makeTrait(44, "Balanced"),
      confidence: makeTrait(46, "Balanced"),
      mischief: makeTrait(48, "Balanced"),
      elegance: makeTrait(57, "Balanced"),
      adventurousness: makeTrait(64, "High"),
    },
    created_at: "2026-01-01T00:00:00Z",
    interpretation_mode: "demo",
    interpretation_model: null,
    interpretation_version: "1.0",
    interpretation: {
      headline: "A wanderer with moonlight in their eyes",
      description: "Every unopened door is an invitation.",
      catchphrase: "I heard a sound three rooms away.",
      secret_talent: "Finding the one dust mote worth staring at.",
      fictional_job: "Chief Field Researcher of Unexplained Noises.",
      fun_fact: "Has a theory about where the sun goes at night.",
    },
    interpretation_created_at: "2026-01-01T00:00:00Z",
    interpretation_cached: false,
    disclaimer:
      "Personality is an AI-inspired interpretation of visual signals, not a scientific assessment of your cat's behavior.",
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(fetchPersonality).mockReset();
  vi.mocked(regeneratePersonality).mockReset();
  vi.mocked(toPng).mockReset();
});

describe("PersonalityCard", () => {
  it("renders nothing when the analysis has no id", () => {
    const { container } = renderWithQueryClient(
      <PersonalityCard result={makeResult({ id: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there is no breed prediction at all", () => {
    const { container } = renderWithQueryClient(
      <PersonalityCard result={makeResult({ breed: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("auto-loads without a trigger button, unlike Grad-CAM", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    expect(fetchPersonality).toHaveBeenCalledWith("analysis-1");
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());
  });

  it("shows a loading reveal while the query is pending", () => {
    vi.mocked(fetchPersonality).mockReturnValue(new Promise(() => {}));
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders all 8 trait bars with real scores, never fabricated", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getAllByRole("progressbar")).toHaveLength(8));
    expect(screen.getByRole("progressbar", { name: /curiosity/ })).toHaveAttribute(
      "aria-valuenow",
      "69",
    );
  });

  it("shows the archetype header, headline, and catchphrase", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());
    expect(screen.getByText("A wanderer with moonlight in their eyes")).toBeInTheDocument();
    expect(screen.getByText(/I heard a sound three rooms away/)).toBeInTheDocument();
  });

  it("always shows the non-scientific disclaimer", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() =>
      expect(
        screen.getByText(/AI-inspired interpretation of visual signals/),
      ).toBeInTheDocument(),
    );
  });

  it('shows "Offline demo content" for demo mode, never claiming a real generation happened', async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality({ interpretation_mode: "demo" }));
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("Offline demo content")).toBeInTheDocument());
    expect(screen.queryByText("AI-generated")).not.toBeInTheDocument();
  });

  it('shows "AI-generated" badge for generated mode', async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(
      makePersonality({ interpretation_mode: "generated", interpretation_model: "claude-sonnet-4-5" }),
    );
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("AI-generated")).toBeInTheDocument());
  });

  it("shows an error message on failure, never a stack trace", async () => {
    vi.mocked(fetchPersonality).mockRejectedValue(
      new PersonalityApiError("This cat couldn't be found.", "not_found"),
    );
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("This cat couldn't be found."),
    );
  });

  it("shows a Regenerate button for the owner, and it updates the card without changing scores", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    vi.mocked(regeneratePersonality).mockResolvedValue(
      makePersonality({
        interpretation: {
          headline: "A new headline",
          description: "Still dreamy.",
          catchphrase: "New catchphrase.",
          secret_talent: "Still finding dust motes.",
          fictional_job: "Still a researcher.",
          fun_fact: "Still curious.",
        },
      }),
    );
    renderWithQueryClient(<PersonalityCard result={makeResult({ owned: true })} />);
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /regenerate/i }));
    await waitFor(() => expect(screen.getByText("A new headline")).toBeInTheDocument());

    // The trait scores must be untouched by regeneration.
    expect(screen.getByRole("progressbar", { name: /curiosity/ })).toHaveAttribute(
      "aria-valuenow",
      "69",
    );
  });

  it("hides the Regenerate button for a non-owner (guest/public view)", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    renderWithQueryClient(<PersonalityCard result={makeResult({ owned: false })} />);
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /regenerate/i })).not.toBeInTheDocument();
  });

  it("downloads a PNG via the shared export mechanism", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    vi.mocked(toPng).mockResolvedValue("data:image/png;base64,abc123");
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /download png/i }));
    await waitFor(() => expect(toPng).toHaveBeenCalledOnce());
  });

  it("shows a failure message if the PNG export fails, never crashing", async () => {
    vi.mocked(fetchPersonality).mockResolvedValue(makePersonality());
    vi.mocked(toPng).mockRejectedValue(new Error("tainted canvas"));
    renderWithQueryClient(<PersonalityCard result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("Dreamy Explorer")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /download png/i }));
    await waitFor(() => expect(screen.getByText("Download failed")).toBeInTheDocument());
  });
});
