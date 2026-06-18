import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { ErrorState, LoadingState } from "@/components/QueryStates";
import { Card, CardContent } from "@/components/ui/card";
import { FindingCard } from "@/features/verification/FindingCard";
import { useCompute } from "@/hooks/queries";
import { money } from "@/lib/format";

export function VerificationPage() {
  const { data, isLoading, isError, error, refetch } = useCompute();
  if (isLoading && !data) return <LoadingState />;
  if (isError || !data) return <ErrorState error={error} onRetry={() => refetch()} />;
  const v = data.verification;

  const flagged = v.findings
    .filter((f) => f.status === "fail")
    .reduce((acc, f) => acc + Math.abs(Number(f.delta)), 0);

  // Exceptions first, then passing checks.
  const ordered = [...v.findings].sort((a, b) =>
    a.status === b.status ? 0 : a.status === "fail" ? -1 : 1,
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl">Verification &amp; Tie-Out</h1>
        <p className="text-sm text-muted-foreground">
          Two figures that should agree, compared within tolerance — every value traced to its source file.
        </p>
      </div>

      {/* Summary banner */}
      {v.failed > 0 ? (
        <Card id="tour-verification-summary" className="border-l-4 bg-bad-bg/40" style={{ borderLeftColor: "hsl(var(--bad))" }}>
          <CardContent className="flex items-center gap-3 py-4">
            <AlertTriangle className="h-5 w-5 shrink-0 text-bad" />
            <div className="text-sm">
              <span className="font-serif text-lg font-semibold text-bad">
                {v.failed} reconciliation exception{v.failed === 1 ? "" : "s"}
              </span>{" "}
              · <span className="tnum font-medium">{money(flagged, true)}</span> flagged across the submitted files ·{" "}
              {v.passed} check{v.passed === 1 ? "" : "s"} passed.
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-l-4 bg-ok-bg/40" style={{ borderLeftColor: "hsl(var(--ok))" }}>
          <CardContent className="flex items-center gap-3 py-4">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-ok" />
            <div className="text-sm">
              <span className="font-serif text-lg font-semibold text-ok">All {v.passed} checks tie out</span>{" "}
              within tolerance.
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {ordered.map((f) => (
          <FindingCard key={f.check_id} finding={f} />
        ))}
      </div>
    </div>
  );
}
