import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StyleSelector } from "./StyleSelector";

describe("StyleSelector", () => {
  it("renders all 10 styles as an accessible radiogroup", () => {
    render(<StyleSelector value="royal" onChange={vi.fn()} />);

    expect(screen.getByRole("radiogroup", { name: "Portrait style" })).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(10);
    expect(screen.getByRole("radio", { name: /royal portrait/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /cosmic cat/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /cute sticker/i })).toBeInTheDocument();
  });

  it("marks the current value as checked and nothing else", () => {
    render(<StyleSelector value="cosmic" onChange={vi.fn()} />);

    expect(screen.getByRole("radio", { name: /cosmic cat/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: /royal portrait/i })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("calls onChange with the clicked style's id", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<StyleSelector value="royal" onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: /anime-inspired/i }));

    expect(onChange).toHaveBeenCalledWith("anime");
  });

  it("disables every option when disabled is set, e.g. while generating", () => {
    render(<StyleSelector value="royal" onChange={vi.fn()} disabled />);

    for (const radio of screen.getAllByRole("radio")) {
      expect(radio).toBeDisabled();
    }
  });
});
