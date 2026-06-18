import * as React from "react";

import { cn } from "@/lib/utils";
import { money } from "@/lib/format";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import type { SensitivityLever } from "@/lib/types";

interface TornadoChartProps {
  levers: SensitivityLever[];
  className?: string;
}

const BAD = "hsl(var(--bad))";
const OK = "hsl(var(--ok))";

/** Render a delta with an explicit typographic minus and absolute money() value. */
function signedMoney(n: number): string {
  if (n === 0) return money(0, true);
  const sign = n < 0 ? "−" : "+";
  return `${sign}${money(Math.abs(n), true)}`;
}

export function TornadoChart({ levers, className }: TornadoChartProps) {
  // Animate bars from 0 -> full width on mount via a single rAF flip.
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  // Sort defensively by magnitude of impact, descending.
  const rows = React.useMemo(() => {
    return (levers ?? [])
      .map((lever) => {
        const delta = Number(lever.delta_excess);
        return { lever, delta: Number.isFinite(delta) ? delta : 0 };
      })
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  }, [levers]);

  const maxAbs = React.useMemo(
    () => rows.reduce((m, r) => Math.max(m, Math.abs(r.delta)), 0),
    [rows],
  );

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="font-serif">What moves availability most</CardTitle>
        <CardDescription>
          Each bar shows the hit to excess availability if that rule tightened ~10%.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 || maxAbs === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No sensitivity to display.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {rows.map(({ lever, delta }, i) => {
              const negative = delta < 0;
              const fill = maxAbs > 0 ? Math.abs(delta) / maxAbs : 0;
              const widthPct = mounted ? fill * 100 : 0;
              const color = negative ? BAD : OK;
              return (
                <li key={lever.id} className="grid grid-cols-[10rem_1fr_8rem] items-center gap-3">
                  <span
                    className="truncate text-sm font-medium text-foreground"
                    title={lever.label}
                  >
                    {lever.label}
                  </span>

                  <div className="relative h-6 overflow-hidden rounded-sm bg-muted">
                    <div
                      className="h-full rounded-sm"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: color,
                        transition: "width 700ms cubic-bezier(0.16, 1, 0.3, 1)",
                        transitionDelay: `${i * 60}ms`,
                      }}
                    />
                  </div>

                  <span
                    className={cn(
                      "tnum text-right text-sm font-semibold",
                      negative ? "text-bad" : "text-ok",
                    )}
                  >
                    {signedMoney(delta)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
