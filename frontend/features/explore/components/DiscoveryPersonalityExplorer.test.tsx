import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { DiscoveryPersonalityExplorer } from "./DiscoveryPersonalityExplorer";

vi.mock("@/services/explore", async () => {
  const actual = await vi.importActual<typeof import("@/services/explore")>("@/services/explore");
  return { ...actual, fetchPersonalityExplorer: vi.fn() };
});

import { fetchPersonalityExplorer } from "@/services/explore";

function makeArchetype(overrides = {}) {
  return {
    id: "dreamy_explorer",
    name: "Dreamy Explorer",
    emoji: "🌙",
    short_description: "Half moonlight, half mischief.",
    long_description: "A wandering spirit.",
    theme_token: "dreamy",
    public_count: 4,
    examples: [],
    disclaimer:
      "Personality archetypes are an AI-inspired interpretation of visual signals, not a scientific classification of your cat's actual behavior.",
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(fetchPersonalityExplorer).mockReset();
});

describe("DiscoveryPersonalityExplorer", () => {
  it("renders each archetype with its emoji and real public count", async () => {
    vi.mocked(fetchPersonalityExplorer).mockResolvedValue([makeArchetype()]);
    renderWithQueryClient(<DiscoveryPersonalityExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/Dreamy Explorer/)).toBeInTheDocument());
    expect(screen.getByText(/\(4\)/)).toBeInTheDocument();
  });

  it("always shows the non-scientific disclaimer", async () => {
    vi.mocked(fetchPersonalityExplorer).mockResolvedValue([makeArchetype()]);
    renderWithQueryClient(<DiscoveryPersonalityExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByText(/not a scientific classification/i)).toBeInTheDocument(),
    );
  });

  it("calls onSelect with the archetype id when clicked", async () => {
    vi.mocked(fetchPersonalityExplorer).mockResolvedValue([makeArchetype()]);
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithQueryClient(<DiscoveryPersonalityExplorer selected={null} onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByText(/Dreamy Explorer/)).toBeInTheDocument());

    await user.click(screen.getByRole("radio", { name: /Dreamy Explorer/ }));
    expect(onSelect).toHaveBeenCalledWith("dreamy_explorer");
  });

  it("disables archetypes with zero public cats", async () => {
    vi.mocked(fetchPersonalityExplorer).mockResolvedValue([
      makeArchetype({ id: "chaos_bean", name: "Chaos Bean", public_count: 0 }),
    ]);
    renderWithQueryClient(<DiscoveryPersonalityExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByRole("radio", { name: /Chaos Bean/ })).toBeDisabled(),
    );
  });
});
