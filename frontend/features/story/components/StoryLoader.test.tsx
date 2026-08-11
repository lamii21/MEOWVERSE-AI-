import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StoryLoader } from "./StoryLoader";

describe("StoryLoader", () => {
  it("announces the first staged message via a live region", () => {
    render(<StoryLoader />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Opening the Cat Universe...");
    expect(status).toHaveAttribute("aria-live", "polite");
  });
});
