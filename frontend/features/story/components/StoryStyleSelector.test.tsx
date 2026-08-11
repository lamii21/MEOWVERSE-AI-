import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StoryStyleSelector } from "./StoryStyleSelector";

describe("StoryStyleSelector", () => {
  it("renders all five styles", () => {
    render(<StoryStyleSelector value="magical_adventure" onChange={vi.fn()} />);

    expect(screen.getByRole("radio", { name: /magical adventure/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /cozy & wholesome/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /funny & chaotic/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /dreamy & emotional/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /fantasy quest/i })).toBeInTheDocument();
  });

  it("marks the current value as checked and nothing else", () => {
    render(<StoryStyleSelector value="funny_chaotic" onChange={vi.fn()} />);

    expect(screen.getByRole("radio", { name: /funny & chaotic/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("radio", { name: /cozy & wholesome/i })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("calls onChange with the clicked style", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<StoryStyleSelector value="magical_adventure" onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: /dreamy & emotional/i }));

    expect(onChange).toHaveBeenCalledWith("dreamy_emotional");
  });

  it("disables every option when disabled is set", () => {
    render(<StoryStyleSelector value="magical_adventure" onChange={vi.fn()} disabled />);

    for (const radio of screen.getAllByRole("radio")) {
      expect(radio).toBeDisabled();
    }
  });
});
