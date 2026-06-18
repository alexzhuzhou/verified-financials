import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BorrowingBaseCertificate } from "@/lib/types";

type StepKind = "start" | "reduction" | "subtotal" | "final";

interface Step {
  label: string;
  /** Signed amount for this step: reductions are negative. */
  amount: number;
  /** Running total of the cascade after this step. */
  running: number;
  kind: StepKind;
  /** Optional caption rendered under emphasized steps. */
  caption?: string;
}

/** Safe numeric coercion for Decimal strings; null/undefined/NaN -> 0. */
function num(v: string | number | null | undefined): number {
  if (v === null || v === undefined || v === "") return 0;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function sum<T>(rows: T[] | undefined, pick: (row: T) => string | number | null | undefined): number {
  if (!rows) return 0;
  return rows.reduce((acc, row) => acc + num(pick(row)), 0);
}

function buildSteps(cert: BorrowingBaseCertificate): Step[] {
  const ar = cert.accounts_receivable;
  const inv = cert.inventory;

  const arIneligible = sum(ar?.ineligibles, (r) => r.amount);
  const arConcentration = sum(ar?.concentration, (r) => r.excess_excluded);
  const arHaircut = num(ar?.eligible) - num(ar?.availability);

  const invIneligible = sum(inv?.ineligibles, (r) => r.amount);
  const invBasis = inv?.eligible_nolv_value ?? inv?.eligible;
  const invHaircut = num(invBasis) - num(inv?.availability);

  const start = num(ar?.gross) + num(inv?.gross);
  const reserves = num(cert.reserves_total);
  const lc = num(cert.lc_exposure);

  // Raw step descriptors; running totals are derived from the authoritative
  // subtotal markers so the cascade always ends exactly on the DTO figures.
  const steps: Step[] = [];

  steps.push({
    label: "Gross collateral (A/R + Inventory)",
    amount: start,
    running: start,
    kind: "start",
  });
  steps.push({
    label: "A/R ineligible (aged, foreign, intercompany)",
    amount: -arIneligible,
    running: 0,
    kind: "reduction",
  });
  steps.push({
    label: "A/R concentration excess",
    amount: -arConcentration,
    running: 0,
    kind: "reduction",
  });
  steps.push({
    label: "A/R advance-rate haircut",
    amount: -arHaircut,
    running: 0,
    kind: "reduction",
  });
  steps.push({
    label: "Inventory ineligible (obsolete)",
    amount: -invIneligible,
    running: 0,
    kind: "reduction",
  });
  steps.push({
    label: "Inventory haircut (NOLV / advance)",
    amount: -invHaircut,
    running: 0,
    kind: "reduction",
  });
  steps.push({
    label: "Gross availability",
    amount: num(cert.gross_availability),
    running: num(cert.gross_availability),
    kind: "subtotal",
  });
  if (reserves !== 0) {
    steps.push({
      label: "Reserves",
      amount: -reserves,
      running: 0,
      kind: "reduction",
    });
  }
  steps.push({
    label: "Borrowing base",
    amount: num(cert.borrowing_base),
    running: num(cert.borrowing_base),
    kind: "subtotal",
  });
  steps.push({
    label: "Outstanding drawn",
    amount: -num(cert.outstanding),
    running: 0,
    kind: "reduction",
  });
  if (lc !== 0) {
    steps.push({
      label: "L/C exposure",
      amount: -lc,
      running: 0,
      kind: "reduction",
    });
  }
  steps.push({
    label: "Excess availability",
    amount: num(cert.excess_availability),
    running: num(cert.excess_availability),
    kind: "final",
    caption: "what you can still draw",
  });

  // Fill running totals for reduction rows by walking the cascade. Subtotal /
  // start / final rows carry their own authoritative running value.
  let run = 0;
  for (const step of steps) {
    if (step.kind === "reduction") {
      run += step.amount; // amount is negative
      step.running = run;
    } else {
      run = step.running;
    }
  }

  return steps;
}

interface WaterfallRowProps {
  step: Step;
  /** Width fraction (0..1) the bar should occupy at its target. */
  target: number;
  /** Whether bars have been "armed" to grow (mount animation). */
  grown: boolean;
  /** Per-row stagger in ms. */
  delay: number;
}

function WaterfallRow({ step, target, grown, delay }: WaterfallRowProps) {
  const isReduction = step.kind === "reduction";
  const isFinal = step.kind === "final";
  const isSubtotal = step.kind === "subtotal";
  const isStart = step.kind === "start";

  const widthPct = grown ? `${Math.max(target * 100, target > 0 ? 1.5 : 0)}%` : "0%";

  // Reductions render as a faint negative sliver; structural rows (start /
  // subtotal / final) render as solid brand bars whose width tracks the
  // running total so the cascade visibly steps down.
  const barClass = cn(
    "h-full rounded-sm transition-all duration-500 ease-out",
    isReduction ? "bg-bad/70" : "bg-primary",
    isFinal && "bg-primary",
  );

  const amountText =
    step.amount < 0
      ? `(−${money(Math.abs(step.amount))})`
      : money(step.amount);

  return (
    <div
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 py-2 sm:grid-cols-[14rem_minmax(0,1fr)_auto]",
        (isSubtotal || isFinal) && "mt-1 border-t-2 border-border pt-3",
        isFinal && "border-primary",
      )}
    >
      {/* Label */}
      <div
        className={cn(
          "order-1 min-w-0 truncate text-sm sm:order-none",
          isReduction ? "text-muted-foreground" : "font-medium",
          isFinal && "text-base font-semibold text-primary",
          (isStart || isSubtotal) && "font-semibold",
        )}
        title={step.label}
      >
        {step.label}
      </div>

      {/* Bar track */}
      <div
        className={cn(
          "order-3 col-span-2 h-2.5 w-full overflow-hidden rounded-sm bg-muted sm:order-none sm:col-span-1",
          isFinal && "h-4",
        )}
        role="presentation"
      >
        <div
          className={barClass}
          style={{
            width: widthPct,
            transitionDelay: `${delay}ms`,
          }}
        />
      </div>

      {/* Amount */}
      <div
        className={cn(
          "tnum order-2 whitespace-nowrap text-right text-sm sm:order-none",
          isReduction && "text-bad",
          (isStart || isSubtotal) && "font-semibold",
          isFinal && "text-base font-bold text-primary",
        )}
      >
        {amountText}
      </div>
    </div>
  );
}

interface WaterfallChartProps {
  cert: BorrowingBaseCertificate;
  className?: string;
}

export function WaterfallChart({ cert, className }: WaterfallChartProps) {
  const steps = buildSteps(cert);

  // Bars are sized against the largest running total in the cascade (the gross
  // collateral, in practice) so every later bar is proportionally shorter.
  const maxRunning = steps.reduce((m, s) => Math.max(m, Math.abs(s.running)), 0);

  const [grown, setGrown] = useState(false);
  useEffect(() => {
    // Arm the grow transition on the next frame so the 0% start width paints
    // first, then animates to target.
    const raf = requestAnimationFrame(() => setGrown(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader>
        <CardTitle>From collateral to availability</CardTitle>
        <CardDescription>
          {money(steps[0]?.running)} of gross collateral steps down, haircut by haircut, to{" "}
          {money(cert.excess_availability)} of room left to draw.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col divide-y divide-border/40">
          {steps.map((step, i) => (
            <WaterfallRow
              key={`${step.label}-${i}`}
              step={step}
              target={maxRunning > 0 ? Math.abs(step.running) / maxRunning : 0}
              grown={grown}
              delay={i * 70}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
