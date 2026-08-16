import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { DiscoveryBreedExplorer } from "./DiscoveryBreedExplorer";

vi.mock("@/services/explore", async () => {
  const actual = await vi.importActual<typeof import("@/services/explore")>("@/services/explore");
  return { ...actual, fetchBreedExplorer: vi.fn() };
});

import { fetchBreedExplorer } from "@/services/explore";

beforeEach(() => {
  vi.mocked(fetchBreedExplorer).mockReset();
});

describe("DiscoveryBreedExplorer", () => {
  it("renders each breed with its real public count", async () => {
    vi.mocked(fetchBreedExplorer).mockResolvedValue([
      { breed: "Persian", public_count: 3, examples: [] },
      { breed: "Siamese", public_count: 0, examples: [] },
    ]);
    renderWithQueryClient(<DiscoveryBreedExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/Persian/)).toBeInTheDocument());
    expect(screen.getByText(/\(3\)/)).toBeInTheDocument();
    expect(screen.getByText(/\(0\)/)).toBeInTheDocument();
  });

  it("disables breeds with zero public cats", async () => {
    vi.mocked(fetchBreedExplorer).mockResolvedValue([
      { breed: "Siamese", public_count: 0, examples: [] },
    ]);
    renderWithQueryClient(<DiscoveryBreedExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByRole("radio", { name: /Siamese/ })).toBeDisabled(),
    );
  });

  it("calls onSelect with the breed name when clicked", async () => {
    vi.mocked(fetchBreedExplorer).mockResolvedValue([
      { breed: "Persian", public_count: 3, examples: [] },
    ]);
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithQueryClient(<DiscoveryBreedExplorer selected={null} onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByText(/Persian/)).toBeInTheDocument());

    await user.click(screen.getByRole("radio", { name: /Persian/ }));
    expect(onSelect).toHaveBeenCalledWith("Persian");
  });

  it("deselects (calls onSelect with null) when the same breed is clicked again", async () => {
    vi.mocked(fetchBreedExplorer).mockResolvedValue([
      { breed: "Persian", public_count: 3, examples: [] },
    ]);
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithQueryClient(<DiscoveryBreedExplorer selected="Persian" onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByText(/Persian/)).toBeInTheDocument());

    await user.click(screen.getByRole("radio", { name: /Persian/ }));
    expect(onSelect).toHaveBeenCalledWith(null);
  });
});
