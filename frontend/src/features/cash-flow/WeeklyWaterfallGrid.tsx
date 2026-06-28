import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CashFlowForecast, CategoryRow, LedgerLine } from "@/lib/types";

/** Compact $thousands for dense grid cells; near-zero shows a dot. */
function k(value: string | number): string {
  const n = Number(value);
  if (!Number.isFinite(n) || Math.abs(n) < 1) return "·";
  return Math.round(n / 1000).toLocaleString("en-US");
}

interface Drill {
  category: string;
  kind: "inflow" | "outflow";
  week: number | null;
}

export function WeeklyWaterfallGrid({ forecast }: { forecast: CashFlowForecast }) {
  const [drill, setDrill] = useState<Drill | null>(null);
  const weeks = forecast.positions.map((p) => p.week);

  const lines: LedgerLine[] = drill
    ? forecast.ledger.filter(
        (li) =>
          li.category === drill.category &&
          li.kind === drill.kind &&
          (drill.week === null || li.week === drill.week),
      )
    : [];

  const renderRow = (row: CategoryRow) => (
    <TableRow key={`${row.kind}-${row.category}`}>
      <TableCell className="sticky left-0 z-10 bg-background">
        <button
          type="button"
          className="text-left hover:text-primary hover:underline"
          onClick={() => setDrill({ category: row.category, kind: row.kind, week: null })}
          title="Show the ledger events behind this row"
        >
          {row.category}
        </button>
      </TableCell>
      {row.weeks.map((cell) => {
        const n = Number(cell.forecast);
        const zero = Math.abs(n) < 1;
        return (
          <TableCell key={cell.week} className="text-right tnum">
            {zero ? (
              <span className="text-muted-foreground/40">·</span>
            ) : (
              <button
                type="button"
                className={cn(
                  "hover:underline",
                  row.kind === "inflow" ? "text-ok" : "text-bad",
                )}
                onClick={() => setDrill({ category: row.category, kind: row.kind, week: cell.week })}
              >
                {k(cell.forecast)}
              </button>
            )}
          </TableCell>
        );
      })}
      <TableCell className="text-right font-semibold tnum">{k(row.period_total)}</TableCell>
    </TableRow>
  );

  const totalRow = (
    label: string,
    perWeek: (w: number) => string,
    total: string,
    opts: { className?: string; belowFloor?: (w: number) => boolean } = {},
  ) => (
    <TableRow className={cn("font-semibold", opts.className)}>
      <TableCell className="sticky left-0 z-10 bg-inherit">{label}</TableCell>
      {forecast.positions.map((p) => (
        <TableCell
          key={p.week}
          className={cn("text-right tnum", opts.belowFloor?.(p.week) && "text-bad")}
        >
          {k(perWeek(p.week))}
        </TableCell>
      ))}
      <TableCell className="text-right tnum">{k(total)}</TableCell>
    </TableRow>
  );

  const pos = (w: number) => forecast.positions[w - 1];

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border">
        <Table className="text-xs">
          <TableHeader>
            <TableRow>
              <TableHead className="sticky left-0 z-10 bg-background">Category</TableHead>
              {weeks.map((w) => (
                <TableHead key={w} className="text-right">W{w}</TableHead>
              ))}
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow className="bg-muted/40">
              <TableCell colSpan={weeks.length + 2} className="py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Receipts
              </TableCell>
            </TableRow>
            {forecast.inflow_rows.map(renderRow)}
            {totalRow("Total Receipts", (w) => pos(w).total_receipts, forecast.kpis.total_receipts, {
              className: "border-t",
            })}

            <TableRow className="bg-muted/40">
              <TableCell colSpan={weeks.length + 2} className="py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Disbursements
              </TableCell>
            </TableRow>
            {forecast.outflow_rows.map(renderRow)}
            {totalRow("Total Disbursements", (w) => pos(w).total_disbursements, forecast.kpis.total_disbursements, {
              className: "border-t",
            })}

            {totalRow("Opening Cash", (w) => pos(w).opening, forecast.opening_cash, {
              className: "border-t-2 border-foreground/30",
            })}
            {totalRow("Net Cash Flow", (w) => pos(w).net, forecast.kpis.net_cash_flow)}
            {totalRow("Closing Cash", (w) => pos(w).closing, forecast.positions[forecast.positions.length - 1].closing, {
              className: "bg-muted/50",
              belowFloor: (w) => pos(w).below_floor,
            })}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        $ in thousands · behavioral timing · click any figure to trace it to the ledger events behind it.
      </p>

      <Dialog open={drill !== null} onOpenChange={(o) => !o && setDrill(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {drill?.category} · {drill?.kind === "inflow" ? "receipts" : "disbursements"}
              {drill?.week ? ` · week ${drill.week}` : ""}
            </DialogTitle>
            <DialogDescription>
              The individual cash events behind this figure — the audit trail.
            </DialogDescription>
          </DialogHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>Ref</TableHead>
                <TableHead>Party</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">Wk</TableHead>
                <TableHead>Timing</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lines.map((li) => (
                <TableRow key={li.row_id}>
                  <TableCell className="text-xs">{li.row_id} · {li.type}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{li.po_so}</TableCell>
                  <TableCell className="text-xs">{li.party}</TableCell>
                  <TableCell className="text-right tnum">{money(li.amount, true)}</TableCell>
                  <TableCell className="text-right tnum">{li.week || "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {li.lag_basis === "FIXED" || li.lag_basis === "MANUAL"
                      ? li.lag_basis.toLowerCase()
                      : `+${Number(li.lag_days).toFixed(0)}d (${li.lag_basis.toLowerCase()})`}
                  </TableCell>
                </TableRow>
              ))}
              {lines.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-sm text-muted-foreground">No events.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </div>
  );
}
