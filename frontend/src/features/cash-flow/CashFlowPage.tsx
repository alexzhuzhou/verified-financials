import { AlertTriangle, ArrowDownToLine, Download, Eye, Loader2, TrendingDown, Waves } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AnimatedNumber } from "@/components/AnimatedNumber";
import { KpiTile } from "@/components/KpiTile";
import { ErrorState, LoadingState } from "@/components/QueryStates";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CashExceptionsTable } from "@/features/cash-flow/CashExceptionsTable";
import { ClosingCashChart } from "@/features/cash-flow/ClosingCashChart";
import { ForecastVsActualCard } from "@/features/cash-flow/ForecastVsActualCard";
import { WeeklyWaterfallGrid } from "@/features/cash-flow/WeeklyWaterfallGrid";
import { useCashFlow } from "@/hooks/queries";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { Overrides } from "@/lib/types";

function downloadHtml(html: string) {
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "13-Week-Cash-Flow-Forecast.html";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function CashFlowPage() {
  const { data, isLoading, isError, error, refetch } = useCashFlow();
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const whatIf = useAppStore((s) => Object.keys(s.overrides).length > 0);
  const [edge, setEdge] = useState<"behavioral" | "contractual">("behavioral");
  const [busy, setBusy] = useState<null | "view" | "download">(null);
  const [exportError, setExportError] = useState<string | null>(null);

  // Editable reported actuals for the closed weeks, seeded from the forecast.
  const [actuals, setActuals] = useState<Record<number, number>>({});
  const seed = useMemo(() => {
    const fc = data?.forecast;
    if (!fc) return {} as Record<number, number>;
    return Object.fromEntries(
      fc.positions.filter((p) => p.actual_closing != null).map((p) => [p.week, Number(p.actual_closing)]),
    );
  }, [data?.forecast]);
  const seedKey = JSON.stringify(seed);
  // Re-seed when the scenario's reported actuals change (not on every what-if recompute).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setActuals(seed), [seedKey]);

  async function exportForecast(mode: "view" | "download") {
    setExportError(null);
    const win = mode === "view" ? window.open("", "_blank") : null;
    setBusy(mode);
    try {
      const args =
        dataSource.kind === "upload"
          ? { uploadId: dataSource.uploadId, configOverrides: overrides as Overrides }
          : { scenario: dataSource.scenario, configOverrides: overrides as Overrides };
      const html = await api.cashflowHtml(args);
      if (win) {
        win.document.open();
        win.document.write(html);
        win.document.close();
      } else {
        downloadHtml(html);
      }
    } catch (e) {
      win?.close();
      setExportError(e instanceof Error ? e.message : "Could not generate the forecast.");
    } finally {
      setBusy(null);
    }
  }

  if (isLoading && !data) return <LoadingState />;
  if (isError || !data) return <ErrorState error={error} onRetry={() => refetch()} />;

  if (!data.available || !data.forecast) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Cash flow uses scenario data</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          The 13-week cash-flow forecast runs on the built-in scenarios' cash-event ledger. Switch
          back to the Baseline or Stress scenario to view it. (Uploading a cash-event ledger is a
          planned next step.)
        </CardContent>
      </Card>
    );
  }

  const f = data.forecast;
  const kpis = edge === "behavioral" ? f.kpis : f.kpis_contractual;
  const alert = kpis.weeks_below_floor > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl">13-Week Cash Flow Forecast</h1>
          <p className="text-sm text-muted-foreground">
            {f.borrower} · anchored {f.anchor_date} · floor {money(f.cash_floor, true)}
            {whatIf && <span className="ml-2 font-medium text-warn">· what-if active</span>}
          </p>
        </div>
        <Badge variant={alert ? "bad" : "ok"}>{alert ? "Liquidity alert" : "Above floor"}</Badge>
      </div>

      {/* Narrative */}
      <Card>
        <CardContent className="pt-5 text-sm leading-relaxed">
          Over the next {f.horizon_weeks} weeks the forecast collects{" "}
          <strong>{money(f.kpis.total_receipts)}</strong> and pays out{" "}
          <strong>{money(f.kpis.total_disbursements)}</strong>, a net{" "}
          <strong className={cn(Number(f.kpis.net_cash_flow) >= 0 ? "text-ok" : "text-bad")}>
            {money(f.kpis.net_cash_flow)}
          </strong>{" "}
          from a {money(f.opening_cash)} opening balance. The realistic (behavioral) closing trough is{" "}
          <strong className={alert ? "text-bad" : "text-primary"}>{money(f.kpis.min_closing)}</strong> in
          week {f.kpis.min_closing_week}
          {f.kpis.weeks_below_floor > 0
            ? `, below the ${money(f.cash_floor, true)} floor in ${f.kpis.weeks_below_floor} week(s) — a near-term financing need.`
            : `, staying above the ${money(f.cash_floor, true)} floor throughout.`}
        </CardContent>
      </Card>

      {/* Edge toggle + export */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-md border p-0.5 text-sm">
          {(["behavioral", "contractual"] as const).map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setEdge(e)}
              className={cn(
                "rounded px-3 py-1 capitalize transition-colors",
                edge === e ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {e}
            </button>
          ))}
          <span className="self-center px-2 text-xs text-muted-foreground">timing edge (KPIs)</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => exportForecast("view")} disabled={busy !== null}>
            {busy === "view" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />} View
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportForecast("download")} disabled={busy !== null}>
            {busy === "download" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Download
          </Button>
        </div>
      </div>
      {exportError && <p className="text-sm text-bad">{exportError}</p>}

      {/* KPI tiles */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Min closing cash"
          icon={<TrendingDown />}
          value={<AnimatedNumber value={kpis.min_closing} />}
          sublabel={`week ${kpis.min_closing_week} · ${edge}`}
          status={alert ? "bad" : "ok"}
        />
        <KpiTile
          label="Weeks below floor"
          icon={<AlertTriangle />}
          value={<span className="tnum">{kpis.weeks_below_floor}</span>}
          sublabel={`of ${f.horizon_weeks} weeks vs ${money(f.cash_floor, true)} floor`}
          status={alert ? "bad" : "ok"}
        />
        <KpiTile
          label="Net cash flow (13W)"
          icon={<Waves />}
          value={<AnimatedNumber value={kpis.net_cash_flow} />}
          sublabel={`${money(kpis.total_receipts, true)} in · ${money(kpis.total_disbursements, true)} out`}
          status={Number(kpis.net_cash_flow) >= 0 ? "ok" : "bad"}
        />
        <KpiTile
          label="Open exceptions"
          icon={<ArrowDownToLine />}
          value={<span className="tnum">{kpis.exception_count}</span>}
          sublabel="flagged ledger rows"
          status={kpis.exception_count > 0 ? "warn" : "ok"}
        />
      </div>

      <div id="tour-cashflow-chart">
        <ClosingCashChart forecast={f} emphasis={edge} actuals={actuals} />
      </div>

      {f.actuals_through_week > 0 && (
        <ForecastVsActualCard
          closed={f.positions.filter((p) => p.actual_closing != null)}
          actuals={actuals}
          onChange={(week, value) => setActuals((a) => ({ ...a, [week]: value }))}
          onReset={() => setActuals(seed)}
        />
      )}

      <Card>
        <CardHeader><CardTitle className="font-serif text-base">Weekly waterfall</CardTitle></CardHeader>
        <CardContent>
          <WeeklyWaterfallGrid forecast={f} />
        </CardContent>
      </Card>

      <CashExceptionsTable exceptions={f.exceptions} />

      {/* Observed payment behavior */}
      <Card>
        <CardHeader><CardTitle className="font-serif text-base">Observed payment behavior</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 text-sm">
            {f.segment_lags.map((s) => (
              <span key={s.segment} className="rounded-md border px-3 py-1.5">
                <span className="font-medium">{s.segment}</span>{" "}
                <span className="text-muted-foreground">
                  avg {Number(s.avg_lag_days).toFixed(1)}d late (±{Number(s.std_dev_days).toFixed(1)}, n={s.sample_count})
                </span>
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
