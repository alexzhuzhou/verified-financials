import { describe, expect, it } from "vitest";

import { setPath, useAppStore } from "./store";

describe("data source switching", () => {
  it("switching scenario sets the source and clears what-if overrides", () => {
    useAppStore.getState().setOverride(["facility", "commitment"], "50000000");
    expect(useAppStore.getState().hasOverrides()).toBe(true);

    useAppStore.getState().setScenario("stress");
    expect(useAppStore.getState().dataSource).toEqual({ kind: "scenario", scenario: "stress" });
    expect(useAppStore.getState().hasOverrides()).toBe(false);
  });

  it("switching to an upload sets an upload source", () => {
    useAppStore.getState().setUpload("abc123");
    expect(useAppStore.getState().dataSource).toEqual({ kind: "upload", uploadId: "abc123" });
    useAppStore.getState().setScenario("baseline"); // reset for other tests
  });
});

describe("guided tour state", () => {
  it("startTour begins at step 0 and closes the welcome dialog", () => {
    useAppStore.getState().setGuideOpen(true);
    useAppStore.getState().startTour();
    expect(useAppStore.getState().tourStep).toBe(0);
    expect(useAppStore.getState().guideOpen).toBe(false);
  });

  it("next/prev advance and clamp at 0", () => {
    useAppStore.getState().startTour();
    useAppStore.getState().nextTourStep();
    expect(useAppStore.getState().tourStep).toBe(1);
    useAppStore.getState().prevTourStep();
    useAppStore.getState().prevTourStep(); // clamp at 0
    expect(useAppStore.getState().tourStep).toBe(0);
  });

  it("exitTour clears the tour and restores a clean baseline", () => {
    useAppStore.getState().startTour();
    useAppStore.getState().setScenario("stress");
    useAppStore.getState().setOverride(["fccr", "covenant_threshold"], "1.20");
    useAppStore.getState().exitTour();
    expect(useAppStore.getState().tourStep).toBeNull();
    expect(useAppStore.getState().dataSource).toEqual({ kind: "scenario", scenario: "baseline" });
    expect(useAppStore.getState().hasOverrides()).toBe(false);
  });
});

describe("setPath (what-if override construction)", () => {
  it("sets a nested leaf immutably", () => {
    const out = setPath({}, ["borrowing_base", "accounts_receivable", "advance_rate"], "0.90");
    expect(out).toEqual({
      borrowing_base: { accounts_receivable: { advance_rate: "0.90" } },
    });
  });

  it("merges into an existing subtree without clobbering siblings", () => {
    const base = { borrowing_base: { accounts_receivable: { advance_rate: "0.85" } } };
    const out = setPath(base, ["borrowing_base", "inventory", "valuation"], "nolv");
    expect(out).toEqual({
      borrowing_base: {
        accounts_receivable: { advance_rate: "0.85" },
        inventory: { valuation: "nolv" },
      },
    });
    // original untouched
    expect(base).toEqual({ borrowing_base: { accounts_receivable: { advance_rate: "0.85" } } });
  });

  it("replaces a leaf (e.g. reserves array) wholesale", () => {
    const out = setPath({ borrowing_base: { reserves: [{ id: "a" }] } }, ["borrowing_base", "reserves"], [
      { id: "a", amount: "1" },
    ]);
    expect(out.borrowing_base.reserves).toEqual([{ id: "a", amount: "1" }]);
  });
});
