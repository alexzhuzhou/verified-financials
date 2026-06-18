import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/QueryStates";
import { FccrStatusBadge, fccrStatus } from "@/components/StatusBadge";
import { Term } from "@/components/Term";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WaterfallChart } from "@/features/borrowing-base/WaterfallChart";
import { api, type ComputeArgs } from "@/lib/api";
import { money, ratio } from "@/lib/format";
import { useAppStore, type DataSource } from "@/lib/store";
import type { ComputeResponse, Overrides } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The three sources a column can compare. */
type SourceChoice = "baseline" | "stress" | "current";

const SOURCE_OPTIONS: { value: SourceChoice; label: string }[] = [
  { value: "baseline", label: "Baseline" },
  { value: "stress", label: "Stress" },
  { value: "current", label: "Current (what-if)" },
];

function sourceLabel(choice: SourceChoice): string {
  return SOURCE_OPTIONS.find((o) => o.value === choice)?.label ?? choice;
}

/** Resolve a source choice into compute args (the "current" case reads the live store). */
function resolveArgs(
  choice: SourceChoice,
  dataSource: DataSource,
  overrides: Overrides,
): ComputeArgs {
  if (choice === "baseline") return { scenario: "baseline", configOverrides: {} };
  if (choice === "stress") return { scenario: "stress", configOverrides: {} };
  // "current" — the live what-if, against whichever data source is loaded.
  return dataSource.kind === "upload"
    ? { uploadId: dataSource.uploadId, configOverrides: overrides }
    : { scenario: dataSource.scenario, configOverrides: overrides };
}

/** Stable, source-aware query for one column. The overrides only matter for "current". */
function useSide(choice: SourceChoice) {
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const args = resolveArgs(choice, dataSource, overrides);
  return useQuery({
    queryKey:
      choice === "current"
        ? ["compare", choice, dataSource, JSON.stringify(overrides)]
        : ["compare", choice],
    queryFn: () => api.compute(args),
    placeholderData: keepPreviousData,
  });
}

/** Safe numeric coercion for Decimal strings; null/undefined/NaN -> 0. */
function num(v: string | number | null | undefined): number {
  if (v === null || v === undefined || v === "") return 0;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? 0 : n;
}

type Better = "higher" | "lower";

interface MetricRow {
  key: string;
  /** Rendered label (may wrap a <Term>). */
  label: React.ReactNode;
  /** Plain string for cell display. */
  display: (r: ComputeResponse) => string;
  /** Raw number used to compute the delta. */
  raw: (r: ComputeResponse) => number;
  /** Whether the delta should be formatted as money or a ratio. */
  deltaFormat: "money" | "ratio" | "count";
  /** Direction that counts as an improvement. */
  better: Better;
}

const METRICS: MetricRow[] = [
  {
    key: "borrowing_base",
    label: <Term name="borrowing base">Borrowing base</Term>,
    display: (r) => money(r.borrowing_base.borrowing_base),
    raw: (r) => num(r.borrowing_base.borrowing_base),
    deltaFormat: "money",
    better: "higher",
  },
  {
    key: "excess_availability",
    label: <Term name="excess availability">Excess availability</Term>,
    display: (r) => money(r.borrowing_base.excess_availability),
    raw: (r) => num(r.borrowing_base.excess_availability),
    deltaFormat: "money",
    better: "higher",
  },
  {
    key: "gross_availability",
    label: "Gross availability",
    display: (r) => money(r.borrowing_base.gross_availability),
    raw: (r) => num(r.borrowing_base.gross_availability),
    deltaFormat: "money",
    better: "higher",
  },
  {
    key: "fccr",
    label: <Term name="FCCR">FCCR</Term>,
    display: (r) => ratio(r.fccr.fccr),
    raw: (r) => num(r.fccr.fccr),
    deltaFormat: "ratio",
    better: "higher",
  },
  {
    key: "exceptions",
    label: "Verification exceptions",
    display: (r) => String(r.verification.failed),
    raw: (r) => r.verification.failed,
    deltaFormat: "count",
    better: "lower",
  },
];

/** Format a numeric delta with an explicit sign for the chosen unit. */
function formatDelta(delta: number, fmt: MetricRow["deltaFormat"]): string {
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  const mag = Math.abs(delta);
  if (fmt === "money") return `${sign}${money(mag)}`;
  if (fmt === "ratio") return `${sign}${ratio(mag)}`;
  return `${sign}${mag}`;
}

/** Tailwind tone for a delta given which direction is "better". */
function deltaTone(delta: number, better: Better): string {
  if (delta === 0) return "text-muted-foreground";
  const improved = better === "higher" ? delta > 0 : delta < 0;
  return improved ? "text-ok" : "text-bad";
}

interface SideColumnProps {
  side: "Left" | "Right";
  choice: SourceChoice;
  onChange: (c: SourceChoice) => void;
}

function SideSelector({ side, choice, onChange }: SideColumnProps) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {side}
      </p>
      <Select value={choice} onValueChange={(v) => onChange(v as SourceChoice)}>
        <SelectTrigger aria-label={`${side} source`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SOURCE_OPTIONS.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** A single value cell — shows a placeholder while a side is still computing. */
function ValueCell({
  data,
  render,
  loading,
}: {
  data: ComputeResponse | undefined;
  render: (r: ComputeResponse) => string;
  loading: boolean;
}) {
  if (data) return <span className="tnum">{render(data)}</span>;
  return (
    <span className="text-xs italic text-muted-foreground">
      {loading ? "Computing…" : "—"}
    </span>
  );
}

/** Compliance status as a check / cross plus the worded badge. */
function ComplianceCell({ data }: { data: ComputeResponse | undefined }) {
  if (!data) return <span className="text-muted-foreground">—</span>;
  const ok = data.fccr.in_compliance;
  return (
    <span className="inline-flex items-center gap-2">
      <span className={cn("tnum text-base font-semibold", ok ? "text-ok" : "text-bad")}>
        {ok ? "✓" : "✗"}
      </span>
      <FccrStatusBadge report={data.fccr} />
    </span>
  );
}

export function ComparePage() {
  const [leftChoice, setLeftChoice] = useState<SourceChoice>("baseline");
  const [rightChoice, setRightChoice] = useState<SourceChoice>("stress");

  const left = useSide(leftChoice);
  const right = useSide(rightChoice);

  const leftData = left.data;
  const rightData = right.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-3xl font-semibold leading-tight">Compare</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Place two scenarios side by side — as-filed, stressed, or your live what-if — and
          watch every figure move.
        </p>
      </div>

      {/* Source pickers */}
      <div className="grid gap-4 sm:grid-cols-2">
        <SideSelector side="Left" choice={leftChoice} onChange={setLeftChoice} />
        <SideSelector side="Right" choice={rightChoice} onChange={setRightChoice} />
      </div>

      {/* Comparison grid */}
      <div className="overflow-hidden rounded-lg border bg-card">
        <div className="grid grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] items-center gap-x-4 border-b bg-muted/50 px-4 py-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <span>Metric</span>
          <span className="text-right">{sourceLabel(leftChoice)}</span>
          <span className="text-right">{sourceLabel(rightChoice)}</span>
          <span className="text-right">Δ</span>
        </div>

        <div className="divide-y divide-border/60">
          {METRICS.map((m) => {
            const hasBoth = !!leftData && !!rightData;
            const delta = hasBoth ? m.raw(rightData) - m.raw(leftData) : 0;
            return (
              <div
                key={m.key}
                className="grid grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] items-center gap-x-4 px-4 py-3 text-sm"
              >
                <span className="font-medium">{m.label}</span>
                <span className="text-right">
                  <ValueCell data={leftData} render={m.display} loading={left.isFetching} />
                </span>
                <span className="text-right">
                  <ValueCell data={rightData} render={m.display} loading={right.isFetching} />
                </span>
                <span
                  className={cn(
                    "tnum text-right font-medium",
                    hasBoth ? deltaTone(delta, m.better) : "text-muted-foreground",
                  )}
                >
                  {hasBoth ? formatDelta(delta, m.deltaFormat) : "—"}
                </span>
              </div>
            );
          })}

          {/* FCCR in-compliance — rendered as status, not a numeric delta. */}
          <div className="grid grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] items-center gap-x-4 px-4 py-3 text-sm">
            <span className="font-medium">
              <Term name="FCCR">FCCR</Term> in compliance
            </span>
            <span className="flex justify-end">
              <ComplianceCell data={leftData} />
            </span>
            <span className="flex justify-end">
              <ComplianceCell data={rightData} />
            </span>
            <ComplianceDelta left={leftData} right={rightData} />
          </div>
        </div>
      </div>

      {/* Side-by-side cascades */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SideCascade choice={leftChoice} query={left} />
        <SideCascade choice={rightChoice} query={right} />
      </div>
    </div>
  );
}

/** The Δ cell for the compliance row: improving = moving into compliance. */
function ComplianceDelta({
  left,
  right,
}: {
  left: ComputeResponse | undefined;
  right: ComputeResponse | undefined;
}) {
  if (!left || !right) return <span className="text-right text-muted-foreground">—</span>;
  const l = left.fccr.in_compliance;
  const r = right.fccr.in_compliance;
  if (l === r) {
    // No change in pass/fail — surface any shift in the worded status instead.
    const ls = fccrStatus(left.fccr).label;
    const rs = fccrStatus(right.fccr).label;
    return (
      <span className="text-right text-xs text-muted-foreground">
        {ls === rs ? "no change" : `${ls} → ${rs}`}
      </span>
    );
  }
  // r === true means we moved into compliance (better); false means we fell out.
  return (
    <span className={cn("text-right text-xs font-medium", r ? "text-ok" : "text-bad")}>
      {r ? "→ in compliance" : "→ breach"}
    </span>
  );
}

interface SideCascadeProps {
  choice: SourceChoice;
  query: ReturnType<typeof useSide>;
}

function SideCascade({ choice, query }: SideCascadeProps) {
  return (
    <div className="space-y-3">
      <h2 className="font-serif text-lg font-semibold">{sourceLabel(choice)}</h2>
      {query.data ? (
        <WaterfallChart cert={query.data.borrowing_base} />
      ) : query.isError ? (
        <ErrorState
          error={query.error}
          onRetry={() => query.refetch()}
          title="Couldn't compute this side"
        />
      ) : (
        <div className="flex h-48 items-center justify-center rounded-lg border bg-card text-sm italic text-muted-foreground">
          Computing…
        </div>
      )}
    </div>
  );
}
