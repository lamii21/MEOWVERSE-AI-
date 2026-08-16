import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DiscoveryFilters } from "./DiscoveryFilters";

import type { DiscoveryQuickFilter } from "./DiscoveryFilters";

const DEFAULT: DiscoveryQuickFilter = { rarity: null, hasStory: false, hasPortrait: false };

describe("DiscoveryFilters", () => {
  it("renders all 7 rarity chips (All + 6 tiers)", () => {
    render(<DiscoveryFilters value={DEFAULT} onChange={vi.fn()} />);
    expect(screen.getByRole("radiogroup", { name: "Filter by rarity" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(7);
  });

  it("marks the current rarity as checked", () => {
    render(<DiscoveryFilters value={{ ...DEFAULT, rarity: "Rare" }} onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "Rare" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "All" })).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with the selected rarity", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<DiscoveryFilters value={DEFAULT} onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: "Legendary" }));
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT, rarity: "Legendary" });
  });

  it("toggles the has-story chip", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<DiscoveryFilters value={DEFAULT} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: /has story/i }));
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT, hasStory: true });
  });

  it("toggles the has-portrait chip", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<DiscoveryFilters value={DEFAULT} onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: /has ai portrait/i }));
    expect(onChange).toHaveBeenCalledWith({ ...DEFAULT, hasPortrait: true });
  });

  it("reflects pressed state on the toggle chips via aria-pressed", () => {
    render(<DiscoveryFilters value={{ ...DEFAULT, hasStory: true }} onChange={vi.fn()} />);
    expect(screen.getByRole("button", { name: /has story/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
