import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { generateStory, shareStory, StoryApiError } from "@/services/stories";

import { StorySection } from "./StorySection";

import type { StoryResponse } from "@/types/story";

vi.mock("@/services/stories", async () => {
  const actual = await vi.importActual<typeof import("@/services/stories")>("@/services/stories");
  return {
    ...actual,
    generateStory: vi.fn(),
    shareStory: vi.fn(),
  };
});

function makeStory(overrides: Partial<StoryResponse> = {}): StoryResponse {
  return {
    id: "story-1",
    analysis_id: "analysis-1",
    style: "magical_adventure",
    story: {
      title: "A Magical Tale",
      subtitle: "Subtitle here",
      opening: "It began one starry night...",
      chapters: [
        { chapter_number: 1, title: "One", text: "Text one." },
        { chapter_number: 2, title: "Two", text: "Text two." },
        { chapter_number: 3, title: "Three", text: "Text three." },
      ],
      ending: "And that was the end.",
      moral: "Magic is everywhere.",
      quote: "Onward, always.",
    },
    story_mode: "demo",
    provider: "demo",
    is_public: false,
    created_at: "2026-08-10T12:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(generateStory).mockReset();
  vi.mocked(shareStory).mockReset();
});

describe("StorySection", () => {
  it("shows a persistence-unavailable message when analysisId is null", () => {
    render(<StorySection analysisId={null} />);

    expect(screen.getByText(/couldn't reach the database/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /write my cat's story/i })).not.toBeInTheDocument();
  });

  it("does not call generateStory until the CTA is clicked", () => {
    render(<StorySection analysisId="analysis-1" />);

    expect(screen.getByText(/your cat's story is waiting/i)).toBeInTheDocument();
    expect(generateStory).not.toHaveBeenCalled();
  });

  it("generates a story on demand and renders it", async () => {
    vi.mocked(generateStory).mockResolvedValue(makeStory());
    const user = userEvent.setup();
    render(<StorySection analysisId="analysis-1" />);

    await user.click(screen.getByRole("button", { name: /write my cat's story/i }));

    await waitFor(() => expect(screen.getByText("A Magical Tale")).toBeInTheDocument());
    expect(generateStory).toHaveBeenCalledWith("analysis-1", "magical_adventure", false);
  });

  it("shows an error message and lets the user retry when generation fails", async () => {
    vi.mocked(generateStory).mockRejectedValueOnce(
      new StoryApiError("The Cat Universe is taking a nap. Try again soon.", "server"),
    );
    const user = userEvent.setup();
    render(<StorySection analysisId="analysis-1" />);

    await user.click(screen.getByRole("button", { name: /write my cat's story/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/taking a nap/i);
    expect(screen.getByRole("button", { name: /write my cat's story/i })).toBeInTheDocument();
  });

  it("regenerates with the same style when Regenerate is clicked", async () => {
    vi.mocked(generateStory).mockResolvedValue(makeStory());
    const user = userEvent.setup();
    render(<StorySection analysisId="analysis-1" />);

    await user.click(screen.getByRole("button", { name: /write my cat's story/i }));
    await waitFor(() => expect(screen.getByText("A Magical Tale")).toBeInTheDocument());

    vi.mocked(generateStory).mockResolvedValue(makeStory({ id: "story-2" }));
    await user.click(screen.getByRole("button", { name: /^regenerate$/i }));

    await waitFor(() =>
      expect(generateStory).toHaveBeenLastCalledWith("analysis-1", "magical_adventure", true),
    );
  });
});
