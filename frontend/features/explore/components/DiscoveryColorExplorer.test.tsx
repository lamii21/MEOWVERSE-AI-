import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithQueryClient } from "@/test-utils/render-with-query";

import { DiscoveryColorExplorer } from "./DiscoveryColorExplorer";

vi.mock("@/services/explore", async () => {
  const actual = await vi.importActual<typeof import("@/services/explore")>("@/services/explore");
  return { ...actual, fetchColorExplorer: vi.fn() };
});

import { fetchColorExplorer } from "@/services/explore";

beforeEach(() => {
  vi.mocked(fetchColorExplorer).mockReset();
});

describe("DiscoveryColorExplorer", () => {
  it("renders each color group with its name and real public count", async () => {
    vi.mocked(fetchColorExplorer).mockResolvedValue([
      { color_name: "orange", hex: "#D98B4B", public_count: 5, examples: [] },
    ]);
    renderWithQueryClient(<DiscoveryColorExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/orange/)).toBeInTheDocument());
    expect(screen.getByText(/\(5\)/)).toBeInTheDocument();
  });

  it("never conveys color only through the swatch — the name is always shown as text", async () => {
    vi.mocked(fetchColorExplorer).mockResolvedValue([
      { color_name: "cream", hex: "#F3E5D8", public_count: 2, examples: [] },
    ]);
    renderWithQueryClient(<DiscoveryColorExplorer selected={null} onSelect={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/cream/)).toBeInTheDocument());
  });

  it("calls onSelect with the color name when clicked", async () => {
    vi.mocked(fetchColorExplorer).mockResolvedValue([
      { color_name: "orange", hex: "#D98B4B", public_count: 5, examples: [] },
    ]);
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithQueryClient(<DiscoveryColorExplorer selected={null} onSelect={onSelect} />);
    await waitFor(() => expect(screen.getByText(/orange/)).toBeInTheDocument());

    await user.click(screen.getByRole("radio", { name: /orange/ }));
    expect(onSelect).toHaveBeenCalledWith("orange");
  });

  it("renders nothing when there are no public colors yet", async () => {
    vi.mocked(fetchColorExplorer).mockResolvedValue([]);
    const { container } = renderWithQueryClient(
      <DiscoveryColorExplorer selected={null} onSelect={vi.fn()} />,
    );
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
