import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ColorPalette } from "./ColorPalette";

const SWATCHES = [
  { name: "cream", hex: "#F3E5D8", percentage: 48 },
  { name: "caramel", hex: "#C9A98C", percentage: 34 },
  { name: "charcoal", hex: "#4B3A2F", percentage: 18 },
];

describe("ColorPalette", () => {
  it("renders name, hex, and percentage for every swatch", () => {
    render(<ColorPalette colors={SWATCHES} />);

    for (const swatch of SWATCHES) {
      expect(screen.getByText(swatch.name)).toBeInTheDocument();
      expect(screen.getByText(swatch.hex)).toBeInTheDocument();
      expect(screen.getByText(`${swatch.percentage}%`)).toBeInTheDocument();
    }
  });

  it("renders nothing for an empty palette", () => {
    const { container } = render(<ColorPalette colors={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one proportional strip segment per swatch", () => {
    const { container } = render(<ColorPalette colors={SWATCHES} />);
    const strip = container.querySelector(".flex.h-3");
    expect(strip?.children.length).toBe(SWATCHES.length);
  });
});
