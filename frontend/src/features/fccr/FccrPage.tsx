import { Figure } from "@/components/Figure";
import { ErrorState, LoadingState } from "@/components/QueryStates";
import { FccrStatusBadge } from "@/components/StatusBadge";
import { FccrTrendChart } from "@/features/fccr/FccrTrendChart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCompute } from "@/hooks/queries";
import { money, pct, ratio, titleize } from "@/lib/format";

const COMPONENT_LABELS: Record<string, string> = {
  ebitda: "EBITDA",
  unfinanced_capex: "Unfinanced capex",
  cash_taxes: "Cash taxes",
  distributions: "Distributions",
  cash_interest: "Cash interest",
  scheduled_principal: "Scheduled principal",
};

export function FccrPage() {
  const { data, isLoading, isError, error, refetch } = useCompute();
  if (isLoading && !data) return <LoadingState />;
  if (isError || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const r = data.fccr;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">Fixed Charge Coverage Ratio (TTM)</h1>
          <p className="text-sm text-muted-foreground">Covenant {ratio(r.covenant)} minimum · as of {r.as_of_date}</p>
        </div>
        <FccrStatusBadge report={r} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Computation</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Component</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.components.map((cmp) => (
                  <TableRow key={`${cmp.side}-${cmp.name}`}>
                    <TableCell>{cmp.role === "subtract" ? "− " : "+ "}{COMPONENT_LABELS[cmp.name] ?? titleize(cmp.name)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{cmp.side}</TableCell>
                    <TableCell className="text-right">
                      <Figure value={cmp.value} dataset="financials_ttm" metric={cmp.name} />
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="font-semibold">
                  <TableCell>Numerator — FCC-adjusted EBITDA</TableCell>
                  <TableCell />
                  <TableCell className="text-right tnum">{money(r.numerator)}</TableCell>
                </TableRow>
                <TableRow className="font-semibold">
                  <TableCell>Denominator — fixed charges</TableCell>
                  <TableCell />
                  <TableCell className="text-right tnum">{money(r.denominator)}</TableCell>
                </TableRow>
                <TableRow className="bg-muted/50 font-serif text-base font-bold">
                  <TableCell>FCCR (TTM)</TableCell>
                  <TableCell />
                  <TableCell className="text-right tnum">{ratio(r.fccr)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Headroom</CardTitle></CardHeader>
            <CardContent className="space-y-1 text-sm">
              <Row label="Covenant minimum" value={ratio(r.covenant)} />
              <Row label="Actual FCCR" value={ratio(r.fccr)} />
              <Row label="Headroom (turns)" value={ratio(r.headroom_abs)} />
              <Row label="Headroom (% over covenant)" value={pct(r.headroom_pct)} />
              <div className="flex justify-between border-t pt-1 font-semibold">
                <span>EBITDA cushion before breach</span>
                <span className="tnum">{money(r.ebitda_cushion)}</span>
              </div>
            </CardContent>
          </Card>

          {r.springing_enabled && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Springing covenant</CardTitle>
                  <Badge variant={r.covenant_active ? "bad" : "ok"}>{r.covenant_active ? "Active" : "Dormant"}</Badge>
                </div>
                <CardDescription>Tested only when availability falls below the trigger.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <Row label="Excess availability" value={money(r.excess_availability)} />
                <Row label="Springing trigger" value={money(r.springing_trigger)} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <div id="tour-fccr-trend">
        <FccrTrendChart report={r} />
      </div>

      {r.equity_cure_enabled && r.covenant_active && !r.in_compliance && (
        <Card className="border-warn/40 bg-warn-bg/40">
          <CardHeader><CardTitle className="text-base">Equity cure</CardTitle></CardHeader>
          <CardContent className="text-sm">
            An equity injection of <strong>{money(r.equity_cure_needed)}</strong> (deemed EBITDA add-back) would restore the
            FCCR to the {ratio(r.covenant)} covenant. Cures remaining: {r.cures_remaining_year} this year,
            {" "}{r.cures_remaining_lifetime} over the life of the facility.
          </CardContent>
        </Card>
      )}

      {r.early_warning && (
        <Card className="border-warn/40 bg-warn-bg/40">
          <CardHeader><CardTitle className="text-base">Early warning</CardTitle></CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 text-sm">
              {r.warning_reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="tnum">{value}</span>
    </div>
  );
}
