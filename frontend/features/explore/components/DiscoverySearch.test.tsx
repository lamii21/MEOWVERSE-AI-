import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { DiscoverySearch } from "./DiscoverySearch";

/** A real controlled wrapper, same shape as the actual page's usage —
 * asserting behavior against a component that never updates `value`
 * between keystrokes would only ever observe the single latest
 * character, not real typed input. */
function ControlledSearch({ onChange }: { onChange: (value: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <DiscoverySearch
      value={value}
      onChange={(v) => {
        setValue(v);
        onChange(v);
      }}
    />
  );
}

describe("DiscoverySearch", () => {
  it("renders an accessible search input", () => {
    render(<DiscoverySearch value="" onChange={vi.fn()} />);
    expect(screen.getByLabelText("Search public cats")).toBeInTheDocument();
  });

  it("calls onChange as the user types, accumulating the full value", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ControlledSearch onChange={onChange} />);

    await user.type(screen.getByLabelText("Search public cats"), "Luna");
    expect(onChange).toHaveBeenCalled();
    expect(onChange.mock.calls.at(-1)?.[0]).toBe("Luna");
  });

  it("reflects the current value", () => {
    render(<DiscoverySearch value="Bengal" onChange={vi.fn()} />);
    expect(screen.getByLabelText("Search public cats")).toHaveValue("Bengal");
  });
});
