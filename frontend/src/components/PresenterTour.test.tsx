import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { useAppStore } from "@/lib/store";
import { TOUR } from "@/lib/tour";

import { PresenterTour } from "./PresenterTour";

function renderTour() {
  return render(
    <TooltipPrimitive.Provider>
      <MemoryRouter>
        <PresenterTour />
      </MemoryRouter>
    </TooltipPrimitive.Provider>,
  );
}

afterEach(() => useAppStore.getState().exitTour());

describe("PresenterTour", () => {
  it("renders nothing when no tour is active", () => {
    useAppStore.getState().exitTour();
    const { container } = renderTour();
    expect(container.firstChild).toBeNull();
  });

  it("shows the first step when started and advances on Next", () => {
    useAppStore.getState().startTour();
    renderTour();
    expect(screen.getByText(/Step 1 of 7/)).toBeInTheDocument();
    expect(screen.getByText(TOUR[0].title)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText(/Step 2 of 7/)).toBeInTheDocument();
    expect(screen.getByText(TOUR[1].title)).toBeInTheDocument();
  });

  it("exits when the close button is clicked", () => {
    useAppStore.getState().startTour();
    renderTour();
    fireEvent.click(screen.getByRole("button", { name: /exit tour/i }));
    expect(useAppStore.getState().tourStep).toBeNull();
  });
});
