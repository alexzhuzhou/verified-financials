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
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CashFlowForecast } from "@/lib/types";

function fmtAxis(v: number): string {
  const sign = v < 0 ? "-" : "";
  const a = Math.abs(v);
  if (a >= 1e6) return `${sign}$${(a / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${sign}$${Math.round(a / 1e3)}k`;
  return `${sign}$${a}`;
}

export function ClosingCashChart({
  forecast,
  emphasis = "behavioral",
  className,
}: {
  forecast: CashFlowForecast;
  emphasis?: "behavioral" | "contractual";
  className?: string;
}) {
  const floor = Number(forecast.cash_floor);

  const rows = useMemo(
    () =>
      forecast.positions.map((p) => ({
        week: `W${p.week}`,
        behavioral: Number(p.closing),
        contractual: Number(p.closing_contractual),
        below: p.below_floor,
      })),
    [forecast],
  );

  const { lo, hi } = useMemo(() => {
    const values = rows.flatMap((r) => [r.behavioral, r.contractual]);
    // Frame to the floor + the actual closings — don't force zero into view, so a
    // healthy baseline sits calmly above the floor and only stress dips negative.
    const all = [floor, ...values];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = Math.max(50_000, (max - min) * 0.12);
    return { lo: min - pad, hi: max + pad };
  }, [rows, floor]);

  const weeksBelow = forecast.kpis.weeks_below_floor;
  const caption =
    weeksBelow > 0
      ? `Closing cash breaches the ${money(forecast.cash_floor, true)} floor in ${weeksBelow} week(s); the trough is ${money(forecast.kpis.min_closing, true)} in week ${forecast.kpis.min_closing_week}.`
      : `Closing cash stays above the ${money(forecast.cash_floor, true)} floor across the horizon; the trough is ${money(forecast.kpis.min_closing, true)} in week ${forecast.kpis.min_closing_week}.`;

  const behavioralActive = emphasis === "behavioral";

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <CardTitle className="font-serif text-base">Closing cash by week</CardTitle>
        <CardDescription>
          The realistic <strong>behavioral</strong> edge (settle&nbsp;+&nbsp;lag) vs the optimistic{" "}
          <strong>contractual</strong> edge (paid on terms). The gap is the timing band.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            {/* Danger zone: the chart floor up to the cash floor. */}
            <ReferenceArea
              y1={lo}
              y2={floor}
              fill="hsl(var(--bad))"
              fillOpacity={0.08}
              stroke="none"
              ifOverflow="hidden"
            />
            <XAxis dataKey="week" tick={{ fontSize: 12 }} />
            <YAxis
              domain={[lo, hi]}
              tickFormatter={fmtAxis}
              tick={{ fontSize: 12 }}
              width={64}
            />
            <Tooltip
              formatter={(v: number, name) => [money(v), name === "behavioral" ? "Behavioral" : "Contractual"]}
            />
            <ReferenceLine
              y={floor}
              stroke="hsl(var(--bad))"
              strokeDasharray="4 4"
              label={{
                value: `cash floor ${fmtAxis(floor)}`,
                position: "insideBottomRight",
                fontSize: 11,
                fill: "hsl(var(--bad))",
              }}
            />
            <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeOpacity={0.4} />
            {/* Optimistic contractual edge. */}
            <Line
              type="monotone"
              dataKey="contractual"
              name="contractual"
              stroke="hsl(var(--ok))"
              strokeWidth={behavioralActive ? 1.5 : 2.5}
              strokeDasharray="5 4"
              dot={false}
              isAnimationActive={false}
            />
            {/* Realistic behavioral edge, with below-floor weeks marked red. */}
            <Line
              type="monotone"
              dataKey="behavioral"
              name="behavioral"
              stroke="hsl(var(--primary))"
              strokeWidth={behavioralActive ? 2.75 : 1.75}
              isAnimationActive={false}
              dot={(props: { cx?: number; cy?: number; payload?: { below?: boolean } }) => {
                const { cx, cy, payload } = props;
                if (cx == null || cy == null) return <g />;
                const bad = Boolean(payload?.below);
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={bad ? 4.5 : 3}
                    fill={bad ? "hsl(var(--bad))" : "hsl(var(--primary))"}
                    stroke="white"
                    strokeWidth={1}
                  />
                );
              }}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className={cn("mt-3 text-sm", weeksBelow > 0 ? "font-medium text-bad" : "text-muted-foreground")}>
          {caption}
        </p>
      </CardContent>
    </Card>
  );
}
