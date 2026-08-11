import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toPng } from "html-to-image";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { CatCard } from "./CatCard";

import type { AnalysisResult } from "@/types/analysis";
import type { User } from "@/types/user";

vi.mock("html-to-image", () => ({ toPng: vi.fn() }));

vi.mock("@/services/analyses", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/analyses")>("@/services/analyses");
  return {
    ...actual,
    shareAnalysis: vi.fn(),
    saveAnalysis: vi.fn(),
    favoriteAnalysis: vi.fn(),
    unfavoriteAnalysis: vi.fn(),
  };
});

const mockUseAuth = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}));

import {
  favoriteAnalysis,
  saveAnalysis,
  shareAnalysis,
  unfavoriteAnalysis,
} from "@/services/analyses";

const FAKE_USER: User = {
  id: "u1",
  email: "cat@example.com",
  display_name: "Cat Fan",
  avatar_url: null,
  created_at: "2026-01-01T00:00:00Z",
};

function asGuest() {
  mockUseAuth.mockReturnValue({ user: null, status: "guest" });
}

function asAuthenticated() {
  mockUseAuth.mockReturnValue({ user: FAKE_USER, status: "authenticated" });
}

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
    owned: false,
    is_favorite: false,
    image_url: null,
    gamification: null,
    created_at: "2026-01-01T00:00:00Z",
    has_story: false,
    ...overrides,
  };
}

let writeTextSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.mocked(shareAnalysis).mockReset();
  vi.mocked(saveAnalysis).mockReset();
  vi.mocked(favoriteAnalysis).mockReset();
  vi.mocked(unfavoriteAnalysis).mockReset();
  vi.mocked(toPng).mockReset();
  asAuthenticated();

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
  Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
});

describe("CatCard", () => {
  it("renders the core collectible-card contents", () => {
    renderWithQueryClient(<CatCard result={makeResult()} />);

    expect(screen.getByText("Sable")).toBeInTheDocument();
    expect(screen.getByText("Bombay")).toBeInTheDocument();
    expect(screen.getByText("Legendary")).toBeInTheDocument();
    expect(screen.getByText("Model confidence")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
  });

  describe("Save", () => {
    it("opens the guest prompt instead of saving when signed out", async () => {
      asGuest();
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult()} />);

      await user.click(screen.getByRole("button", { name: /^save$/i }));

      expect(await screen.findByText(/deserves a home/i)).toBeInTheDocument();
      expect(saveAnalysis).not.toHaveBeenCalled();
    });

    it("claims the cat and updates optimistically when signed in", async () => {
      vi.mocked(saveAnalysis).mockResolvedValue(makeResult({ owned: true }));
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);

      await user.click(screen.getByRole("button", { name: /^save$/i }));

      // Optimistic: button flips to "Saved" before the mocked promise
      // above even needs to resolve.
      expect(await screen.findByRole("button", { name: /^saved$/i })).toBeInTheDocument();
      await waitFor(() => expect(saveAnalysis).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111"));
    });

    it("rolls back to unsaved if the save call fails", async () => {
      // The mock rejects instantly, so the optimistic "Saved" frame and
      // its rollback both settle within the same tick — nothing for a
      // real user to see in between here (a real failed request has
      // genuine latency). What matters is the final, settled state.
      vi.mocked(saveAnalysis).mockRejectedValue(new Error("nope"));
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);

      await user.click(screen.getByRole("button", { name: /^save$/i }));

      await waitFor(() =>
        expect(screen.getByRole("button", { name: /^save$/i })).toBeInTheDocument(),
      );
      await waitFor(() => expect(saveAnalysis).toHaveBeenCalledOnce());
    });

    it("does nothing when clicking Save on an already-owned cat", async () => {
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: true })} />);

      const saveButton = screen.getByRole("button", { name: /^saved$/i });
      expect(saveButton).toBeDisabled();
      await user.click(saveButton);
      expect(saveAnalysis).not.toHaveBeenCalled();
    });
  });

  describe("Favorite", () => {
    it("is disabled until the cat is saved", () => {
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);
      expect(screen.getByRole("button", { name: /^favorite$/i })).toBeDisabled();
    });

    it("toggles favorite state optimistically for an owned cat", async () => {
      vi.mocked(favoriteAnalysis).mockResolvedValue(
        makeResult({ owned: true, is_favorite: true }),
      );
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: true, is_favorite: false })} />);

      await user.click(screen.getByRole("button", { name: /^favorite$/i }));

      expect(await screen.findByRole("button", { name: /^favorited$/i })).toBeInTheDocument();
      await waitFor(() =>
        expect(favoriteAnalysis).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111"),
      );
    });

    it("opens the guest prompt when a signed-out visitor clicks Favorite", async () => {
      asGuest();
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);

      await user.click(screen.getByRole("button", { name: /^favorite$/i }));
      expect(await screen.findByText(/deserves a home/i)).toBeInTheDocument();
    });
  });

  describe("Share", () => {
    it("is disabled for a signed-in user until the cat is saved", () => {
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);
      expect(screen.getByRole("button", { name: /^share$/i })).toBeDisabled();
    });

    it("copies a share link once the cat is owned", async () => {
      vi.mocked(shareAnalysis).mockResolvedValue(makeResult({ owned: true, is_public: true }));
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: true })} />);

      await user.click(screen.getByRole("button", { name: /^share$/i }));

      expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
      expect(writeTextSpy).toHaveBeenCalledWith(
        expect.stringContaining("/cat/11111111-1111-1111-1111-111111111111"),
      );
    });

    it("opens the guest prompt when a signed-out visitor clicks Share", async () => {
      asGuest();
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult({ owned: false })} />);

      await user.click(screen.getByRole("button", { name: /^share$/i }));
      expect(await screen.findByText(/deserves a home/i)).toBeInTheDocument();
    });
  });

  describe("Download", () => {
    it("exports and downloads a PNG on click", async () => {
      vi.mocked(toPng).mockResolvedValue("data:image/png;base64,abc123");
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult()} />);

      await user.click(screen.getByRole("button", { name: /download png/i }));

      await waitFor(() => expect(toPng).toHaveBeenCalledOnce());
      expect(screen.queryByText(/download failed/i)).not.toBeInTheDocument();
    });

    it("shows an error state, not a blank/broken image, when export fails", async () => {
      vi.mocked(toPng).mockRejectedValue(new Error("tainted canvas"));
      const user = userEvent.setup();
      renderWithQueryClient(<CatCard result={makeResult()} />);

      await user.click(screen.getByRole("button", { name: /download png/i }));

      expect(await screen.findByText(/download failed/i)).toBeInTheDocument();
    });
  });

  it("scrolls to the story section when Story is clicked", async () => {
    document.body.innerHTML += '<div id="story-section"></div>';
    const user = userEvent.setup();
    renderWithQueryClient(<CatCard result={makeResult()} />);

    await user.click(screen.getByRole("button", { name: /^story$/i }));

    expect(document.getElementById("story-section")?.scrollIntoView).toHaveBeenCalled();
  });

  it("shows Wallpaper as a disabled, honestly-labeled placeholder", () => {
    renderWithQueryClient(<CatCard result={makeResult()} />);
    const wallpaperButton = screen.getByRole("button", { name: /wallpaper/i });
    expect(wallpaperButton).toBeDisabled();
    expect(wallpaperButton).toHaveAttribute("title", "Coming in a future update");
  });
});
