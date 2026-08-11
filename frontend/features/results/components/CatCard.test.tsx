import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toPng } from "html-to-image";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { shareAnalysis } from "@/services/analyses";

import { CatCard } from "./CatCard";

import type { AnalysisResult } from "@/types/analysis";

vi.mock("html-to-image", () => ({ toPng: vi.fn() }));

vi.mock("@/services/analyses", async () => {
  const actual = await vi.importActual<typeof import("@/services/analyses")>("@/services/analyses");
  return { ...actual, shareAnalysis: vi.fn() };
});

function makeResult(overrides: Partial<AnalysisResult> = {}): AnalysisResult {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    detected: true,
    breed: { label: "Bombay", confidence: 0.91 },
    breed_mode: "trained",
    colors: [
      { name: "cream", hex: "#F3E5D8", percentage: 48 },
      { name: "caramel", hex: "#C9A98C", percentage: 34 },
      { name: "charcoal", hex: "#4B3A2F", percentage: 18 },
    ],
    colors_mode: "trained",
    embedding_available: false,
    profile: {
      name: "Sable",
      title: "Whisperer of the Air Vents",
      personality: "Mysterious and independent, seen mostly at dawn and dusk.",
      magic_power: "Can vanish mid-sentence.",
      kingdom: "The Shadow Between Rooms",
      favorite_activity: "Patrolling the perimeter of absolutely nothing",
      favorite_food: "Whatever arrives at 5:58am",
      favorite_season: "Autumn",
      rarity: "Legendary",
      description: "Answers to no one, keeps their own counsel.",
    },
    profile_mode: "generated",
    is_public: false,
    ...overrides,
  };
}

let writeTextSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.mocked(shareAnalysis).mockReset();
  vi.mocked(toPng).mockReset();
  window.localStorage.clear();
  // See features/story/components/StoryCard.test.tsx for why this
  // checks for an existing navigator.clipboard first: jsdom 30 ships a
  // real (non-configurable-looking, but actually fine) Clipboard
  // instance, and redefining the whole property doesn't reliably route
  // through a fresh mock — spying on the existing object's method does.
  if (!navigator.clipboard) {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      configurable: true,
    });
  }
  writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
    value: vi.fn(),
    configurable: true,
  });
  window.HTMLAnchorElement.prototype.click = vi.fn();
  // Ensure no leftover navigator.share from a previous test's stub.
  Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
});

describe("CatCard", () => {
  it("renders the core collectible-card contents", () => {
    render(<CatCard result={makeResult()} />);

    expect(screen.getByText("Sable")).toBeInTheDocument();
    expect(screen.getByText("“Whisperer of the Air Vents”")).toBeInTheDocument();
    expect(screen.getByText("Bombay")).toBeInTheDocument();
    expect(screen.getByText("Legendary")).toBeInTheDocument();
    expect(screen.getByText("Can vanish mid-sentence.")).toBeInTheDocument();
    expect(screen.getByText("Mysterious and independent, seen mostly at dawn and dusk.")).toBeInTheDocument();
    expect(screen.getByText("Answers to no one, keeps their own counsel.")).toBeInTheDocument();
    expect(screen.getByText("cream")).toBeInTheDocument();
    expect(screen.getByText("Model confidence")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
  });

  it("shows a short MeowVerse ID derived from the analysis id", () => {
    render(<CatCard result={makeResult({ id: "abcdef12-3456-7890-abcd-ef1234567890" })} />);
    expect(screen.getByTitle("MeowVerse ID")).toHaveTextContent("#ABCDEF12");
  });

  it("shows UNSAVED and disables Share when the analysis has no id", () => {
    render(<CatCard result={makeResult({ id: null })} />);
    expect(screen.getByTitle("MeowVerse ID")).toHaveTextContent("UNSAVED");
    expect(screen.getByRole("button", { name: /^share$/i })).toBeDisabled();
  });

  it("toggles Save and persists it to localStorage", async () => {
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByRole("button", { name: /^saved$/i })).toHaveAttribute("aria-pressed", "true");
    expect(JSON.parse(window.localStorage.getItem("meowverse:saved-cats") ?? "[]")).toContain(
      "11111111-1111-1111-1111-111111111111",
    );
  });

  it("shares via clipboard fallback when the native share API is unavailable", async () => {
    vi.mocked(shareAnalysis).mockResolvedValue(makeResult({ is_public: true }));
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
    expect(shareAnalysis).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111");
    expect(writeTextSpy).toHaveBeenCalledWith(
      expect.stringContaining("/cat/11111111-1111-1111-1111-111111111111"),
    );
  });

  it("prefers the native share sheet when available, and skips the clipboard", async () => {
    vi.mocked(shareAnalysis).mockResolvedValue(makeResult({ is_public: true }));
    const shareSpy = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { value: shareSpy, configurable: true });
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    await waitFor(() => expect(shareSpy).toHaveBeenCalledOnce());
    expect(writeTextSpy).not.toHaveBeenCalled();
  });

  it("shows an error state when sharing fails", async () => {
    vi.mocked(shareAnalysis).mockRejectedValue(new Error("network down"));
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    expect(await screen.findByText(/couldn't share/i)).toBeInTheDocument();
  });

  it("exports and downloads a PNG on Download click", async () => {
    vi.mocked(toPng).mockResolvedValue("data:image/png;base64,abc123");
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /download png/i }));

    await waitFor(() => expect(toPng).toHaveBeenCalledOnce());
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /download png/i })).not.toBeDisabled(),
    );
    expect(screen.queryByText(/download failed/i)).not.toBeInTheDocument();
  });

  it("shows an error state, not a blank/broken image, when export fails", async () => {
    vi.mocked(toPng).mockRejectedValue(new Error("tainted canvas"));
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /download png/i }));

    expect(await screen.findByText(/download failed/i)).toBeInTheDocument();
  });

  it("scrolls to the story section when Story is clicked", async () => {
    document.body.innerHTML += '<div id="story-section"></div>';
    const user = userEvent.setup();
    render(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^story$/i }));

    expect(document.getElementById("story-section")?.scrollIntoView).toHaveBeenCalled();
  });

  it("shows Wallpaper as a disabled, honestly-labeled placeholder", () => {
    render(<CatCard result={makeResult()} />);
    const wallpaperButton = screen.getByRole("button", { name: /wallpaper/i });
    expect(wallpaperButton).toBeDisabled();
    expect(wallpaperButton).toHaveAttribute("title", "Coming in a future update");
  });
});
