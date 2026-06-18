import { cn } from "@/lib/utils";
import { money } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Finding, FactRef } from "@/lib/types";

interface FindingSideProps {
  fact: FactRef;
  align?: "left" | "right";
}

function FindingSide({ fact, align = "left" }: FindingSideProps) {
  return (
    <div className={cn("flex flex-col gap-1", align === "right" && "sm:items-end sm:text-right")}>
      <div className="tnum text-lg font-medium leading-snug">{money(fact.value)}</div>
      <div className="flex flex-col gap-0.5 text-xs text-muted-foreground">
        <span className="font-medium">{fact.ref}</span>
        <span>
          {fact.source_file} · {fact.source_locator}
          {fact.version_tag ? ` (${fact.version_tag})` : ""}
        </span>
      </div>
    </div>
  );
}

export function FindingCard({ finding }: { finding: Finding }) {
  const isPass = finding.status === "pass";
  const accent = isPass ? "hsl(var(--ok))" : "hsl(var(--bad))";

  const deltaVal = Math.abs(Number(finding.delta));
  const tol = Number(finding.tolerance_abs);
  const overTolerance = tol > 0 && Number.isFinite(deltaVal) ? Math.round(deltaVal / tol) : null;

  return (
    <Card className="border-l-4" style={{ borderLeftColor: accent }}>
      <CardContent className="flex flex-col gap-5 p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-serif text-base font-medium leading-snug">{finding.label}</h3>
          {isPass ? (
            <Badge variant="ok">PASS</Badge>
          ) : (
            <Badge variant="bad">{finding.severity.toUpperCase()}</Badge>
          )}
        </div>

        <div className="grid grid-cols-1 items-center gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <FindingSide fact={finding.left} align="left" />
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground sm:px-2">
            vs
          </div>
          <FindingSide fact={finding.right} align="right" />
        </div>

        {isPass ? (
          <p className="text-sm text-ok">Ties out within the {money(finding.tolerance_abs)} tolerance.</p>
        ) : (
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-t pt-3">
            <span className="tnum text-xl font-bold text-bad">Δ {money(finding.delta)}</span>
            <span className="text-xs text-muted-foreground">
              {overTolerance ? `${overTolerance.toLocaleString()}× over` : "exceeds"} the{" "}
              {money(finding.tolerance_abs)} tolerance
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
