import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toPng } from "html-to-image";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { PortraitCard } from "./PortraitCard";

vi.mock("html-to-image", () => ({ toPng: vi.fn() }));

vi.mock("@/services/portrait", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/portrait")>("@/services/portrait");
  return { ...actual, sharePortrait: vi.fn() };
});

import { PortraitApiError, sharePortrait } from "@/services/portrait";

import type { CatPortrait } from "@/types/portrait";

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

let writeTextSpy: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.mocked(sharePortrait).mockReset();
  vi.mocked(toPng).mockReset();

  if (!navigator.clipboard) {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      configurable: true,
    });
  }
  writeTextSpy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
  window.HTMLAnchorElement.prototype.click = vi.fn();
});

describe("PortraitCard", () => {
  it("renders nothing for a non-succeeded portrait", () => {
    const { container } = renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait({ status: "failed" })}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("always shows the AI-generated artwork label, never presenting it as a photo", () => {
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );
    expect(screen.getByText("AI-generated artwork")).toBeInTheDocument();
    expect(screen.getByText(/not an actual photograph/i)).toBeInTheDocument();
  });

  it("shows the style name and emoji", () => {
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait({ style_name: "Cosmic Cat", style_emoji: "🪐" })}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );
    expect(screen.getByText("Cosmic Cat")).toBeInTheDocument();
  });

  it("downloads a PNG via the shared export mechanism", async () => {
    vi.mocked(toPng).mockResolvedValue("data:image/png;base64,abc123");
    const user = userEvent.setup();
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /download png/i }));
    await waitFor(() => expect(toPng).toHaveBeenCalledOnce());
    expect(screen.queryByText(/download failed/i)).not.toBeInTheDocument();
  });

  it("shows a failure message if PNG export fails, never crashing", async () => {
    vi.mocked(toPng).mockRejectedValue(new Error("tainted canvas"));
    const user = userEvent.setup();
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /download png/i }));
    expect(await screen.findByText(/download failed/i)).toBeInTheDocument();
  });

  it("shares via the existing /share endpoint and copies a real link", async () => {
    vi.mocked(sharePortrait).mockResolvedValue(makePortrait({ is_public: true }));
    const user = userEvent.setup();
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
    expect(writeTextSpy).toHaveBeenCalledWith(expect.stringContaining("/portrait/portrait-1"));
  });

  it("shows an error message if sharing fails, never a stack trace", async () => {
    vi.mocked(sharePortrait).mockRejectedValue(
      new PortraitApiError("This portrait couldn't be found.", "not_found"),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /^share$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This portrait couldn't be found.",
    );
  });

  it("calls onGenerateAgain when clicked", async () => {
    const onGenerateAgain = vi.fn();
    const user = userEvent.setup();
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={onGenerateAgain}
        isGeneratingAgain={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /generate again/i }));
    expect(onGenerateAgain).toHaveBeenCalledOnce();
  });

  it("disables Generate Again while a regeneration is already in flight", () => {
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={true}
      />,
    );
    expect(screen.getByRole("button", { name: /generating/i })).toBeDisabled();
  });

  it("shows an Original/AI Portrait comparison toggle when the original image is available", () => {
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl="/media/original.jpg"
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );
    expect(screen.getByRole("radiogroup", { name: "Portrait comparison" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Original" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "AI Portrait" })).toBeInTheDocument();
  });

  it("omits the comparison toggle when no original image is available", () => {
    renderWithQueryClient(
      <PortraitCard
        portrait={makePortrait()}
        catName="Luna"
        originalImageUrl={null}
        onGenerateAgain={vi.fn()}
        isGeneratingAgain={false}
      />,
    );
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });
});
