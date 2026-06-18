import { create } from "zustand";

import type { Overrides } from "./types";

/** Immutably set a nested path (array of keys) on a plain object. */
export function setPath(obj: Overrides, path: string[], value: unknown): Overrides {
  if (path.length === 0) return obj;
  const [head, ...rest] = path;
  const child = (obj[head] ?? {}) as Overrides;
  return {
    ...obj,
    [head]: rest.length === 0 ? value : setPath(child, rest, value),
  };
}

/** What the engines run against: a built-in scenario or a user upload. */
export type DataSource =
  | { kind: "scenario"; scenario: string }
  | { kind: "upload"; uploadId: string };

/** Uploaded data uses the baseline config as its rule template. */
export function configScenarioOf(ds: DataSource): string {
  return ds.kind === "scenario" ? ds.scenario : "baseline";
}

interface AppState {
  dataSource: DataSource;
  overrides: Overrides;
  guideOpen: boolean;
  /** Active step of the guided presenter tour; null when the tour is off. */
  tourStep: number | null;
  setScenario: (s: string) => void;
  setUpload: (uploadId: string) => void;
  setOverride: (path: string[], value: unknown) => void;
  setOverrides: (o: Overrides) => void;
  setGuideOpen: (open: boolean) => void;
  reset: () => void;
  hasOverrides: () => boolean;
  startTour: () => void;
  nextTourStep: () => void;
  prevTourStep: () => void;
  exitTour: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  dataSource: { kind: "scenario", scenario: "baseline" },
  overrides: {},
  guideOpen: false,
  tourStep: null,
  setGuideOpen: (guideOpen) => set({ guideOpen }),
  // switching the data source always clears what-if edits
  setScenario: (scenario) => set({ dataSource: { kind: "scenario", scenario }, overrides: {} }),
  setUpload: (uploadId) => set({ dataSource: { kind: "upload", uploadId }, overrides: {} }),
  setOverride: (path, value) => set({ overrides: setPath(get().overrides, path, value) }),
  setOverrides: (overrides) => set({ overrides }),
  reset: () => set({ overrides: {} }),
  hasOverrides: () => Object.keys(get().overrides).length > 0,
  startTour: () => set({ tourStep: 0, guideOpen: false }),
  nextTourStep: () => set((s) => ({ tourStep: s.tourStep === null ? null : s.tourStep + 1 })),
  prevTourStep: () => set((s) => ({ tourStep: s.tourStep === null ? null : Math.max(0, s.tourStep - 1) })),
  // exit always lands on a clean baseline so the next walk-through starts fresh
  exitTour: () => set({ tourStep: null, dataSource: { kind: "scenario", scenario: "baseline" }, overrides: {} }),
}));
