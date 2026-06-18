import { Download, Eye, Loader2 } from "lucide-react";
import { useState } from "react";

import { Figure } from "@/components/Figure";
import { GoalSeekCard } from "@/components/GoalSeekCard";
import { ErrorState, LoadingState } from "@/components/QueryStates";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TornadoChart } from "@/features/analytics/TornadoChart";
import { WaterfallChart } from "@/features/borrowing-base/WaterfallChart";
import { useCompute, useSensitivity } from "@/hooks/queries";
import { api } from "@/lib/api";
import { money, pct } from "@/lib/format";
import { useAppStore } from "@/lib/store";
import type { AssetClassResult, Overrides } from "@/lib/types";

/** Trigger a browser download of the standalone certificate HTML. */
function downloadHtml(html: string) {
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "Borrowing-Base-Certificate.html";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function CertificatePage() {
  const { data, isLoading, isError, error, refetch } = useCompute();
  const sens = useSensitivity();
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);
  const [busy, setBusy] = useState<null | "view" | "download">(null);
  const [exportError, setExportError] = useState<string | null>(null);

  /** Render the bank-ready certificate for the LIVE state, then open it or save it. */
  async function exportCertificate(mode: "view" | "download") {
    setExportError(null);
    // Open the tab synchronously (inside the click) so popup blockers allow it.
    const win = mode === "view" ? window.open("", "_blank") : null;
    setBusy(mode);
    try {
      const args =
        dataSource.kind === "upload"
          ? { uploadId: dataSource.uploadId, configOverrides: overrides as Overrides }
          : { scenario: dataSource.scenario, configOverrides: overrides as Overrides };
      const html = await api.certificateHtml(args);
      if (win) {
        win.document.open();
        win.document.write(html);
        win.document.close();
      } else {
        downloadHtml(html); // download mode, or popup was blocked
      }
    } catch (e) {
      win?.close();
      setExportError(e instanceof Error ? e.message : "Could not generate the certificate.");
    } finally {
      setBusy(null);
    }
  }

  if (isLoading && !data) return <LoadingState />;
  if (isError || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const c = data.borrowing_base;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl">Borrowing Base Certificate</h1>
          <p className="text-sm text-muted-foreground">{c.facility_name}</p>
        </div>
        <div id="tour-certificate-actions" className="no-print flex shrink-0 items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={busy !== null}
            onClick={() => exportCertificate("view")}
            title="Open the bank-ready certificate in a new tab (print → Save as PDF)"
          >
            {busy === "view" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
            View / Print
          </Button>
          <Button
            size="sm"
            disabled={busy !== null}
            onClick={() => exportCertificate("download")}
            title="Download the self-contained, bank-ready certificate (.html)"
          >
            {busy === "download" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Download
          </Button>
        </div>
      </div>
      {exportError && <p className="no-print text-sm text-bad">{exportError}</p>}

      <Card>
        <CardContent className="grid grid-cols-2 gap-2 pt-5 text-sm">
          <Meta k="Borrower" v={c.borrower} />
          <Meta k="Certificate No." v={String(c.certificate_no)} />
          <Meta k="Collateral as of" v={c.as_of_date} />
          <Meta k="Agreement" v={c.agreement_reference} span />
        </CardContent>
      </Card>

      <div id="tour-waterfall">
        <WaterfallChart cert={c} className="no-print" />
      </div>

      {sens.data && sens.data.levers.length > 0 && (
        <TornadoChart levers={sens.data.levers} className="no-print" />
      )}

      <GoalSeekCard className="no-print" />

      <AssetSection title="A. Accounts Receivable" a={c.accounts_receivable} grossProvenance={{ dataset: "ar_aging", metric: "total" }} />
      <AssetSection title="B. Inventory" a={c.inventory} grossProvenance={{ dataset: "inventory", metric: "value" }} />

      <Card>
        <CardHeader><CardTitle className="text-base">C. Borrowing Base Roll-Up</CardTitle></CardHeader>
        <CardContent className="space-y-1 text-sm">
          <Line label="A/R availability" value={money(c.accounts_receivable.availability)} />
          <Line label="Inventory availability" value={money(c.inventory.availability)} />
          <Line label="Gross availability" value={money(c.gross_availability)} bold border />
          {c.reserve_detail.length === 0 ? (
            <Line label="Less: Reserves" value={`(${money(c.reserves_total)})`} indent />
          ) : (
            c.reserve_detail.map((r) => (
              <Line key={r.id} label={`Less: ${r.label}`} value={`(${money(r.amount)})`} indent />
            ))
          )}
          <Line label="Borrowing base" value={money(c.borrowing_base)} bold border />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">D. Commitment Cap &amp; Availability</CardTitle></CardHeader>
        <CardContent className="space-y-1 text-sm">
          <Line label="Revolver commitment" value={money(c.commitment)} />
          <Line label="Borrowing base" value={money(c.borrowing_base)} />
          <Line label={`Line cap (lesser of) — binding: ${c.binding_constraint.replace("_", " ")}`} value={money(c.borrowing_base)} bold border />
          <Line label="Less: Outstanding revolving loans" value={`(${money(c.outstanding)})`} indent />
          <Line label="Less: Letter-of-credit exposure" value={`(${money(c.lc_exposure)})`} indent />
          <div className="flex items-center justify-between border-t-2 border-primary bg-muted/50 px-1 py-2 font-serif text-base font-bold">
            <span>Excess (net) availability</span>
            <span className="tnum">{money(c.excess_availability)}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5 text-sm">
          The borrower presents <strong>{money(c.gross_availability)}</strong> of gross collateral availability
          against a <strong>{money(c.commitment)}</strong> revolver. After eligibility rules the borrowing base is{" "}
          <strong>{money(c.borrowing_base)}</strong>; with <strong>{money(c.outstanding)}</strong> drawn, only{" "}
          <strong className="text-primary">{money(c.excess_availability)}</strong> of additional availability remains.
          <div className="mt-8 border-t border-foreground pt-1 text-xs">
            Chief Financial Officer · {c.borrower} — certified true, correct and complete.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AssetSection({
  title,
  a,
  grossProvenance,
}: {
  title: string;
  a: AssetClassResult;
  grossProvenance: { dataset: string; metric: string };
}) {
  const isNolv = a.valuation_basis === "nolv";
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        <div className="flex items-center justify-between px-1 py-1">
          <span>Gross {a.asset_class === "inventory" ? "inventory" : "accounts receivable"}</span>
          <Figure value={a.gross} dataset={grossProvenance.dataset} metric={grossProvenance.metric} />
        </div>
        {a.ineligibles.map((line) => (
          <div key={line.rule_id} className="flex items-start justify-between px-1 py-0.5 pl-5">
            <span className="text-muted-foreground">
              Less: {line.label}
              <span className="block text-[10px] italic">{line.citation}</span>
            </span>
            <span className="tnum">({money(line.amount)})</span>
          </div>
        ))}
        {a.concentration.map((cl) => (
          <Line key={cl.customer} indent
            label={`Less: Concentration excess — ${cl.customer} (${pct(cl.pct_of_gross)} of gross; cap ${money(cl.cap_amount)})`}
            value={`(${money(cl.excess_excluded)})`} />
        ))}
        <Line label={`Eligible${isNolv ? " (at cost)" : ""}`} value={money(a.eligible)} bold border />
        {isNolv && (
          <>
            {a.nolv_detail.map((n) => (
              <Line key={n.category} indent
                label={`NOLV — ${n.category} (cost ${money(n.cost)} × ${pct(n.nolv_ratio, 0)})`}
                value={money(n.nolv_value)} />
            ))}
            <Line label="Net orderly liquidation value" value={money(a.eligible_nolv_value)} bold border />
          </>
        )}
        <Line label={`Advance rate${isNolv ? " (of NOLV)" : ""}`} value={pct(a.advance_rate, 0)} />
        <Line label="Availability" value={money(a.availability)} bold border />
      </CardContent>
    </Card>
  );
}

function Meta({ k, v, span }: { k: string; v: string; span?: boolean }) {
  return (
    <div className={span ? "col-span-2" : ""}>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{k}</div>
      <div className="font-medium">{v}</div>
    </div>
  );
}

function Line({
  label,
  value,
  bold,
  border,
  indent,
}: {
  label: string;
  value: string;
  bold?: boolean;
  border?: boolean;
  indent?: boolean;
}) {
  return (
    <div
      className={[
        "flex items-center justify-between px-1 py-0.5",
        bold ? "font-semibold" : "",
        border ? "border-y border-foreground/30" : "",
        indent ? "pl-5 text-muted-foreground" : "",
      ].join(" ")}
    >
      <span>{label}</span>
      <span className="tnum">{value}</span>
    </div>
  );
}
