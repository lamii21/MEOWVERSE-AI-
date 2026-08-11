import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GuestSavePrompt } from "./GuestSavePrompt";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analyze",
}));

describe("GuestSavePrompt", () => {
  it("shows the honest, on-brand copy and does not render when closed", () => {
    const { rerender } = render(<GuestSavePrompt open={false} onOpenChange={vi.fn()} />);
    expect(screen.queryByText(/deserves a home/i)).not.toBeInTheDocument();

    rerender(<GuestSavePrompt open onOpenChange={vi.fn()} />);
    expect(screen.getByText(/deserves a home/i)).toBeInTheDocument();
    expect(screen.getByText(/create an account to save this cat/i)).toBeInTheDocument();
  });

  it("links to login and register carrying the current page as `next`", () => {
    // The Button component renders these as <a> tags styled/announced
    // as buttons (role="button") via Base UI's render-prop pattern —
    // same as every other nav CTA in this app (e.g. "Discover My Cat").
    render(<GuestSavePrompt open onOpenChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /log in/i })).toHaveAttribute(
      "href",
      "/login?next=%2Fanalyze",
    );
    expect(screen.getByRole("button", { name: /create an account/i })).toHaveAttribute(
      "href",
      "/register?next=%2Fanalyze",
    );
  });
});
