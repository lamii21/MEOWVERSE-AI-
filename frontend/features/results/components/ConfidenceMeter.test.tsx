import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConfidenceMeter } from "./ConfidenceMeter";

describe("ConfidenceMeter", () => {
  it("labels the value 'Model confidence', never certainty about the cat's identity", () => {
    render(<ConfidenceMeter confidence={0.91} />);

    expect(screen.getByText("Model confidence")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.queryByText(/91% certain/i)).not.toBeInTheDocument();
  });

  it("rounds fractional confidence to a whole percentage", () => {
    render(<ConfidenceMeter confidence={0.746} />);
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("includes a short explanation of what the number means", () => {
    render(<ConfidenceMeter confidence={0.5} />);
    expect(screen.getByText(/not a certainty claim/i)).toBeInTheDocument();
  });
});
