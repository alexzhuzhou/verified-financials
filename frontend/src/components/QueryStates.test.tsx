import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ErrorState } from "./QueryStates";

describe("ErrorState", () => {
  it("shows the error message and calls onRetry when clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorState error={new Error("inventory.csv row 5: expected a number")} onRetry={onRetry} />);

    expect(screen.getByText(/inventory\.csv row 5/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("humanizes an unreachable-API network error", () => {
    render(<ErrorState error={new TypeError("Failed to fetch")} />);
    expect(screen.getByText(/Couldn't reach the API/i)).toBeInTheDocument();
  });
});
