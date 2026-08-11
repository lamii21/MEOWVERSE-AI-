import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StoryCard } from "./StoryCard";

import type { StoryResponse } from "@/types/story";

function makeStory(overrides: Partial<StoryResponse> = {}): StoryResponse {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    analysis_id: "22222222-2222-2222-2222-222222222222",
    style: "cozy_wholesome",
    story: {
      title: "Whiskers and the Warm Sunbeam",
      subtitle: "A tale of naps and gentle magic",
      opening: "Once upon a time, in a cozy little house...",
      chapters: [
        { chapter_number: 1, title: "The Sunny Spot", text: "Whiskers found the warmest windowsill." },
        { chapter_number: 2, title: "A New Friend", text: "A ladybug landed nearby, and they became friends." },
        { chapter_number: 3, title: "Home Again", text: "As evening came, Whiskers curled up to sleep." },
      ],
      ending: "And so Whiskers drifted off to sleep, happy and warm.",
      moral: "Sometimes the best adventures are the quiet ones.",
      quote: "Home is wherever the sunbeam falls.",
    },
    story_mode: "demo",
    provider: "demo",
    is_public: false,
    created_at: "2026-08-10T12:00:00Z",
    gamification: null,
    ...overrides,
  };
}

let writeTextSpy: ReturnType<typeof vi.fn<(data: string) => Promise<void>>>;

beforeEach(() => {
  if (!navigator.clipboard) {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      configurable: true,
    });
  }
  writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  window.HTMLAnchorElement.prototype.click = vi.fn();
  if (!URL.createObjectURL) {
    URL.createObjectURL = vi.fn(() => "blob:mock");
  } else {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
  }
  if (!URL.revokeObjectURL) {
    URL.revokeObjectURL = vi.fn();
  } else {
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  }
});

describe("StoryCard", () => {
  it("renders the story content", () => {
    render(<StoryCard story={makeStory()} />);

    expect(screen.getByText("Whiskers and the Warm Sunbeam")).toBeInTheDocument();
    expect(screen.getByText("A tale of naps and gentle magic")).toBeInTheDocument();
    expect(screen.getByText(/Once upon a time/)).toBeInTheDocument();
    expect(screen.getByText(/Chapter 1: The Sunny Spot/)).toBeInTheDocument();
    expect(screen.getByText(/Chapter 2: A New Friend/)).toBeInTheDocument();
    expect(screen.getByText(/Chapter 3: Home Again/)).toBeInTheDocument();
    expect(screen.getByText("Sometimes the best adventures are the quiet ones.")).toBeInTheDocument();
  });

  it("shows the offline-demo badge for demo mode and the AI-generated badge for generated mode", () => {
    const { rerender } = render(<StoryCard story={makeStory({ story_mode: "demo" })} />);
    expect(screen.getByText("Offline demo story")).toBeInTheDocument();

    rerender(<StoryCard story={makeStory({ story_mode: "generated" })} />);
    expect(screen.getByText("AI-generated")).toBeInTheDocument();
  });

  it("only shows a Regenerate button when onRegenerate is provided", () => {
    const { rerender } = render(<StoryCard story={makeStory()} />);
    expect(screen.queryByRole("button", { name: /regenerate/i })).not.toBeInTheDocument();

    rerender(<StoryCard story={makeStory()} onRegenerate={vi.fn()} />);
    expect(screen.getByRole("button", { name: /regenerate/i })).toBeInTheDocument();
  });

  it("calls onRegenerate when the Regenerate button is clicked", async () => {
    const onRegenerate = vi.fn();
    const user = userEvent.setup();
    render(<StoryCard story={makeStory()} onRegenerate={onRegenerate} />);

    await user.click(screen.getByRole("button", { name: /regenerate/i }));

    expect(onRegenerate).toHaveBeenCalledOnce();
  });

  it("toggles favorite state and persists it to localStorage", async () => {
    const user = userEvent.setup();
    render(<StoryCard story={makeStory()} />);

    const favoriteButton = screen.getByRole("button", { name: /^favorite$/i });
    await user.click(favoriteButton);

    expect(screen.getByRole("button", { name: /favorited/i })).toHaveAttribute("aria-pressed", "true");
    expect(JSON.parse(window.localStorage.getItem("meowverse:favorite-stories") ?? "[]")).toContain(
      "11111111-1111-1111-1111-111111111111",
    );
  });

  it("copies a share link to the clipboard when Share is clicked", async () => {
    const onShare = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<StoryCard story={makeStory()} onShare={onShare} />);

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
    expect(onShare).toHaveBeenCalledOnce();
    expect(writeTextSpy).toHaveBeenCalledWith(
      expect.stringContaining("/story/11111111-1111-1111-1111-111111111111"),
    );
  });
});
