import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { PortraitStudio } from "./PortraitStudio";

vi.mock("@/services/portrait", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/portrait")>("@/services/portrait");
  return { ...actual, fetchPortraits: vi.fn(), generatePortrait: vi.fn() };
});

import { PortraitApiError, fetchPortraits, generatePortrait } from "@/services/portrait";

import type { AnalysisResult } from "@/types/analysis";
import type { CatPortrait } from "@/types/portrait";

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

function makePortrait(overrides: Partial<CatPortrait> = {}): CatPortrait {
  return {
    id: "portrait-1",
    analysis_id: "analysis-1",
    style: "royal",
    style_name: "Royal Portrait",
    style_emoji: "👑",
    status: "succeeded",
    image_url: "/media/portrait-1.png",
    provider: "openai",
    model: "gpt-image-1",
    prompt_version: "1.0",
    error_code: null,
    error_message: null,
    is_public: false,
    owned: true,
    reused: false,
    created_at: "2026-01-01T00:00:00Z",
    completed_at: "2026-01-01T00:00:05Z",
    gamification: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(fetchPortraits).mockReset();
  vi.mocked(generatePortrait).mockReset();
});

describe("PortraitStudio", () => {
  it("renders nothing when the analysis has no id", () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    const { container } = renderWithQueryClient(
      <PortraitStudio result={makeResult({ id: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there is no breed prediction at all", () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    const { container } = renderWithQueryClient(
      <PortraitStudio result={makeResult({ breed: null })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the style selector and generate button for the owner", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    renderWithQueryClient(<PortraitStudio result={makeResult({ owned: true })} />);
    await waitFor(() =>
      expect(screen.getByRole("radiogroup", { name: "Portrait style" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /generate/i })).toBeInTheDocument();
  });

  it("hides the generate form for a non-owner (guest/public view)", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    renderWithQueryClient(<PortraitStudio result={makeResult({ owned: false })} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());
    expect(screen.queryByRole("radiogroup", { name: "Portrait style" })).not.toBeInTheDocument();
  });

  it("shows existing succeeded portraits", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [makePortrait()] });
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(screen.getByText("Royal Portrait")).toBeInTheDocument());
  });

  it("shows a loading reveal while generating, then the new portrait", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    let resolvePromise: (value: CatPortrait) => void = () => {};
    vi.mocked(generatePortrait).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: /generate/i }));
    expect(screen.getByRole("status")).toBeInTheDocument();

    resolvePromise(makePortrait());
    await waitFor(() => expect(screen.getByText("Royal Portrait")).toBeInTheDocument());
  });

  it("shows an honest unavailable message when no provider is configured, never a fake portrait", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    vi.mocked(generatePortrait).mockResolvedValue(
      makePortrait({
        status: "failed",
        image_url: null,
        error_code: "provider_unavailable",
        error_message: "Portrait generation is currently unavailable.",
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: /generate/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/currently unavailable/i);
    expect(screen.queryByAltText(/AI-generated/i)).not.toBeInTheDocument();
  });

  it("shows a rate-limited message distinctly", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    vi.mocked(generatePortrait).mockResolvedValue(
      makePortrait({
        status: "failed",
        image_url: null,
        error_code: "rate_limited",
        error_message: "Too many portraits requested.",
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: /generate/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/please wait a moment/i);
  });

  it("shows a network/API error message, never a stack trace", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    vi.mocked(generatePortrait).mockRejectedValue(
      new PortraitApiError("Please sign in to do that.", "unauthorized"),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: /generate/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Please sign in to do that.");
  });

  it("lets the user type an optional customization idea within the character limit", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    const input = screen.getByLabelText(/add something special/i);
    await user.type(input, "Put Luna in a moonlit library.");
    expect(input).toHaveValue("Put Luna in a moonlit library.");
    expect(screen.getByText("30/120")).toBeInTheDocument();
  });

  it("sends the selected style and customization when generating", async () => {
    vi.mocked(fetchPortraits).mockResolvedValue({ portraits: [] });
    vi.mocked(generatePortrait).mockResolvedValue(makePortrait({ style: "cosmic" }));
    const user = userEvent.setup();
    renderWithQueryClient(<PortraitStudio result={makeResult()} />);
    await waitFor(() => expect(fetchPortraits).toHaveBeenCalled());

    await user.click(screen.getByRole("radio", { name: /cosmic cat/i }));
    await user.type(screen.getByLabelText(/add something special/i), "sparkles please");
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() =>
      expect(generatePortrait).toHaveBeenCalledWith(
        "analysis-1",
        "cosmic",
        "sparkles please",
        false,
      ),
    );
  });
});
