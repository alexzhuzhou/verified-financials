import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { configScenarioOf, useAppStore, type DataSource } from "@/lib/store";
import type { Overrides } from "@/lib/types";

import { useDebounce } from "./useDebounce";

export function useScenarios() {
  return useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
}

export function useConfig(scenario: string) {
  return useQuery({ queryKey: ["config", scenario], queryFn: () => api.config(scenario) });
}

function sourceArgs(ds: DataSource) {
  return ds.kind === "upload" ? { uploadId: ds.uploadId } : { scenario: ds.scenario };
}

/** Single source of truth: recompute (debounced) whenever the data source or rules change. */
export function useCompute() {
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const debounced = useDebounce(overrides, 250);
  return useQuery({
    queryKey: ["compute", dataSource, JSON.stringify(debounced)],
    queryFn: () => api.compute({ ...sourceArgs(dataSource), configOverrides: debounced as Overrides }),
    placeholderData: keepPreviousData,
  });
}

/** The unmodified ("as-filed") result for the current data source — for delta-vs-baseline.
 *  Keyed identically to useCompute with empty overrides, so it shares that cache entry. */
export function useBaseline() {
  const dataSource = useAppStore((s) => s.dataSource);
  return useQuery({
    queryKey: ["compute", dataSource, JSON.stringify({})],
    queryFn: () => api.compute({ ...sourceArgs(dataSource), configOverrides: {} }),
  });
}

/** The AI (or rule-generated) executive briefing for the current source + rules. */
export function useBriefing() {
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const debounced = useDebounce(overrides, 400);
  return useQuery({
    queryKey: ["briefing", dataSource, JSON.stringify(debounced)],
    queryFn: () => api.briefing({ ...sourceArgs(dataSource), configOverrides: debounced as Overrides }),
    placeholderData: keepPreviousData,
  });
}

/** Sensitivity ("which lever moves availability most") for the current source + rules. */
export function useSensitivity() {
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const debounced = useDebounce(overrides, 400);
  return useQuery({
    queryKey: ["sensitivity", dataSource, JSON.stringify(debounced)],
    queryFn: () => api.sensitivity({ ...sourceArgs(dataSource), configOverrides: debounced as Overrides }),
    placeholderData: keepPreviousData,
  });
}

export function useFacts(args: { dataset?: string; metric?: string; entity?: string } | null) {
  const dataSource = useAppStore((s) => s.dataSource);
  return useQuery({
    queryKey: ["facts", dataSource, args],
    queryFn: () => api.facts({ ...sourceArgs(dataSource), ...(args ?? {}) }),
    enabled: args !== null,
  });
}

/** The scenario whose config drives the rule editor (baseline for uploads). */
export function useConfigScenario(): string {
  const dataSource = useAppStore((s) => s.dataSource);
  return configScenarioOf(dataSource);
}
