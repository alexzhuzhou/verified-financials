import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ratio } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { FccrReport } from "@/lib/types";

const HORIZON = 4;

/** Parse a quarter label like "Q3-2025" into a {q, year} pair. */
function parseQuarter(label: string): { q: number; year: number } | null {
  const m = /^Q([1-4])-(\d{4})$/.exec(label.trim());
  if (!m) return null;
  return { q: Number(m[1]), year: Number(m[2]) };
}

/** Increment a quarter, rolling the year over after Q4. */
function nextQuarter({ q, year }: { q: number; year: number }): { q: number; year: number } {
  return q >= 4 ? { q: 1, year: year + 1 } : { q: q + 1, year };
}

function fmtQuarter({ q, year }: { q: number; year: number }): string {
  return `Q${q}-${year}`;
}

interface ChartRow {
  quarter: string;
  /** Solid historical series; only present on actual rows. */
  actual: number | null;
  /** Dotted projection; present on the join point + future rows so the line bridges. */
  projected: number | null;
}

interface Projection {
  rows: ChartRow[];
  /** Quarter label where the projection first dips below the covenant, if any. */
  breachQuarter: string | null;
  /** True once we had >=2 points and a downward (negative) slope. */
  declining: boolean;
}

function buildProjection(report: FccrReport): Projection {
  const covenant = Number(report.covenant);
  const history = report.trend
    .map((p) => ({ quarter: p.quarter, value: Number(p.fccr) }))
    .filter((p) => Number.isFinite(p.value));

  const rows: ChartRow[] = history.map((p) => ({
    quarter: p.quarter,
    actual: p.value,
    projected: null,
  }));

  // Need at least two historical points to define a slope.
  if (history.length < 2) {
    return { rows, breachQuarter: null, declining: false };
  }

  const last = history[history.length - 1];
  const prev = history[history.length - 2];
  const slope = last.value - prev.value; // per-quarter change
  const parsedLast = parseQuarter(last.quarter);

  // Only project a breach path when the trend is actually declining and the
  // last quarter label is parseable (so we can mint future labels).
  if (slope >= 0 || !parsedLast) {
    return { rows, breachQuarter: null, declining: false };
  }

  // Bridge: the join point lives on BOTH series so the solid and dotted lines
  // connect visually at the last actual reading.
  rows[rows.length - 1].projected = last.value;

  let breachQuarter: string | null = null;
  let cursor = parsedLast;
  let value = last.value;

  for (let i = 1; i <= HORIZON; i += 1) {
    cursor = nextQuarter(cursor);
    value += slope; // linear extrapolation
    const label = fmtQuarter(cursor);
    rows.push({ quarter: label, actual: null, projected: value });
    if (breachQuarter === null && value < covenant) breachQuarter = label;
  }

  return { rows, breachQuarter, declining: true };
}

export function FccrTrendChart({ report, className }: { report: FccrReport; className?: string }) {
  const covenant = Number(report.covenant);

  const { rows, breachQuarter, declining } = useMemo(() => buildProjection(report), [report]);

  // Domain padding around covenant + every plotted value (actual & projected).
  const { lo, hi } = useMemo(() => {
    const values = rows.flatMap((r) =>
      [r.actual, r.projected].filter((v): v is number => v !== null && Number.isFinite(v)),
    );
    const all = [covenant, ...values];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = Math.max(0.1, (max - min) * 0.15);
    return { lo: min - pad, hi: max + pad };
  }, [rows, covenant]);

  const covLabel = `covenant ${covenant.toFixed(2)}x`;

  const caption = declining
    ? breachQuarter
      ? `Projected to breach the ${ratio(report.covenant)} covenant by ${breachQuarter}.`
      : "No breach projected on the current trajectory."
    : "No breach projected on the current trajectory.";

  const hasProjection = rows.some((r) => r.projected !== null);

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="font-serif text-base">Covenant trend &amp; projection</CardTitle>
        <CardDescription>
          Trailing FCCR with a linear forward projection of the recent trajectory.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No quarterly history available.</p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                {/* Danger zone: covenant down to the chart floor. */}
                <ReferenceArea
                  y1={lo}
                  y2={covenant}
                  fill="hsl(var(--bad))"
                  fillOpacity={0.08}
                  stroke="none"
                  ifOverflow="hidden"
                />
                <XAxis dataKey="quarter" tick={{ fontSize: 12 }} />
                <YAxis
                  domain={[lo, hi]}
                  tickFormatter={(v: number) => `${v.toFixed(2)}x`}
                  tick={{ fontSize: 12 }}
                  width={56}
                  allowDecimals
                />
                <Tooltip
                  formatter={(v: number, name) => [
                    `${v.toFixed(2)}x`,
                    name === "projected" ? "Projected" : "Actual",
                  ]}
                />
                <ReferenceLine
                  y={covenant}
                  stroke="hsl(var(--bad))"
                  strokeDasharray="4 4"
                  label={{
                    value: covLabel,
                    position: "insideBottomRight",
                    fontSize: 11,
                    fill: "hsl(var(--bad))",
                  }}
                />
                {/* Solid historical line. */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="actual"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                {/* Dotted forward projection. */}
                {hasProjection && (
                  <Line
                    type="monotone"
                    dataKey="projected"
                    name="projected"
                    stroke="hsl(var(--warn))"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    dot={{ r: 3, fill: "hsl(var(--warn))" }}
                    connectNulls
                    isAnimationActive={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
            <p
              className={cn(
                "mt-3 text-sm",
                breachQuarter ? "font-medium text-bad" : "text-muted-foreground",
              )}
            >
              {caption}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
