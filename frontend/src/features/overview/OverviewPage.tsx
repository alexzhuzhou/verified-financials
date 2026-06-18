import { AlertTriangle, ArrowRight, Gauge, Landmark, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { AnimatedNumber } from "@/components/AnimatedNumber";
import { KpiTile } from "@/components/KpiTile";
import { ErrorState, LoadingState } from "@/components/QueryStates";
import { fccrStatus } from "@/components/StatusBadge";
import { Term } from "@/components/Term";
import { Card, CardContent } from "@/components/ui/card";
import { WaterfallChart } from "@/features/borrowing-base/WaterfallChart";
import { useBaseline, useCompute } from "@/hooks/queries";
import { money, ratio } from "@/lib/format";
import { useAppStore } from "@/lib/store";

function fmtDelta(cur?: string, base?: string, kind: "money" | "ratio" = "money"): string | undefined {
  if (cur == null || base == null) return undefined;
  const d = Number(cur) - Number(base);
  const eps = kind === "ratio" ? 0.005 : 0.5;
  if (!Number.isFinite(d) || Math.abs(d) < eps) return undefined;
  const sign = d > 0 ? "+" : "−";
  const mag = kind === "ratio" ? `${Math.abs(d).toFixed(2)}x` : money(Math.abs(d), true);
  return `${sign}${mag} vs filed`;
}

export function OverviewPage() {
  const { data, isLoading, isError, error, refetch } = useCompute();
  const { data: baseline } = useBaseline();
  const whatIf = useAppStore((s) => Object.keys(s.overrides).length > 0);

  if (isLoading && !data) return <LoadingState />;
  if (isError || !data) return <ErrorState error={error} onRetry={() => refetch()} />;

  const { verification: v, borrowing_base: bb, fccr } = data;
  const base = whatIf ? baseline : undefined;
  const status = fccrStatus(fccr);

  const flagged = v.findings
    .filter((f) => f.status === "fail")
    .reduce((acc, f) => acc + Math.abs(Number(f.delta)), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl">Overview</h1>
        <p className="text-sm text-muted-foreground">
          {bb.borrower} · as of {bb.as_of_date}
          {whatIf && <span className="ml-2 font-medium text-warn">· what-if active (deltas vs as-filed)</span>}
        </p>
      </div>

      {/* Narrative briefing */}
      <Card>
        <CardContent className="pt-5 text-sm leading-relaxed">
          After eligibility rules, the <Term name="borrowing base">borrowing base</Term> is{" "}
          <strong>{money(bb.borrowing_base)}</strong> against a {money(bb.commitment)} revolver; with{" "}
          {money(bb.outstanding)} drawn, <strong className="text-primary">{money(bb.excess_availability)}</strong>{" "}
          of <Term name="excess availability">availability</Term> remains. The{" "}
          <Term name="FCCR">FCCR</Term> is <strong>{ratio(fccr.fccr)}</strong> versus the {ratio(fccr.covenant)}{" "}
          <Term name="covenant">covenant</Term>
          {fccr.early_warning ? " — compliant but inside the early-warning band" : ""}. {v.failed}{" "}
          reconciliation {v.failed === 1 ? "exception" : "exceptions"} flagged across the submitted files.
        </CardContent>
      </Card>

      {/* KPI tiles */}
      <div id="tour-kpis" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label={<Term name="excess availability">Excess availability</Term>}
          icon={<Landmark />}
          value={<AnimatedNumber value={bb.excess_availability} />}
          sublabel="room left to draw"
          status={Number(bb.excess_availability) > 0 ? "ok" : "bad"}
          delta={fmtDelta(bb.excess_availability, base?.borrowing_base.excess_availability)}
        />
        <KpiTile
          label={<Term name="borrowing base">Borrowing base</Term>}
          icon={<Gauge />}
          value={<AnimatedNumber value={bb.borrowing_base} />}
          sublabel={`of ${money(bb.commitment, true)} commitment · binding: ${bb.binding_constraint.replace("_", " ")}`}
          delta={fmtDelta(bb.borrowing_base, base?.borrowing_base.borrowing_base)}
        />
        <KpiTile
          label={<Term name="FCCR">FCCR (TTM)</Term>}
          icon={<Gauge />}
          value={<AnimatedNumber value={fccr.fccr} format="ratio" />}
          sublabel={`vs ${ratio(fccr.covenant)} covenant`}
          status={status.variant}
          delta={fmtDelta(fccr.fccr, base?.fccr.fccr, "ratio")}
        />
        <KpiTile
          label="Verification"
          icon={v.failed ? <AlertTriangle /> : <ShieldCheck />}
          value={<span className="tnum">{v.failed}</span>}
          sublabel={v.failed ? `${money(flagged, true)} flagged · ${v.passed} passed` : `all ${v.passed} checks passed`}
          status={v.failed ? "bad" : "ok"}
        />
      </div>

      {/* The hero: collateral → availability cascade */}
      <WaterfallChart cert={bb} />

      <div className="flex flex-wrap gap-4 text-sm">
        <Link to="/verification" className="inline-flex items-center gap-1 text-primary hover:underline">
          Verification findings <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <Link to="/borrowing-base" className="inline-flex items-center gap-1 text-primary hover:underline">
          Borrowing base certificate <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <Link to="/fccr" className="inline-flex items-center gap-1 text-primary hover:underline">
          FCCR covenant <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
