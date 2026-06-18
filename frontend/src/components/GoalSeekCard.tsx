import * as React from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { money, pct } from "@/lib/format";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { GoalSeekResult } from "@/lib/types";

/** Levers the solver can move. All current options resolve to a fraction (0..1). */
const LEVERS = [
  { value: "ar_advance_rate", label: "A/R advance rate" },
  { value: "inventory_advance_rate", label: "Inventory advance rate" },
  { value: "concentration_cap_pct", label: "Concentration cap %" },
] as const;

type LeverValue = (typeof LEVERS)[number]["value"];

const DEFAULT_LEVER: LeverValue = "ar_advance_rate";

export interface GoalSeekCardProps {
  className?: string;
}

export function GoalSeekCard({ className }: GoalSeekCardProps) {
  const dataSource = useAppStore((s) => s.dataSource);
  const overrides = useAppStore((s) => s.overrides);

  const [lever, setLever] = React.useState<LeverValue>(DEFAULT_LEVER);
  const [target, setTarget] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<GoalSeekResult | null>(null);

  const targetValid = target.trim() !== "" && Number.isFinite(Number(target));
  const canSolve = targetValid && !loading;

  async function onSolve() {
    if (!canSolve) return;
    setLoading(true);
    setError(null);
    try {
      const sourceArg =
        dataSource.kind === "upload"
          ? { uploadId: dataSource.uploadId }
          : { scenario: dataSource.scenario };
      const res = await api.goalSeek({
        ...sourceArg,
        configOverrides: overrides,
        lever,
        targetValue: target.trim(),
      });
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Goal-seek failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader>
        <CardTitle className="font-serif">Goal-seek</CardTitle>
        <CardDescription>
          Solve for the rule value that hits a target availability.
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="goal-seek-lever">Lever</Label>
            <Select
              value={lever}
              onValueChange={(v) => setLever(v as LeverValue)}
            >
              <SelectTrigger id="goal-seek-lever">
                <SelectValue placeholder="Choose a lever" />
              </SelectTrigger>
              <SelectContent>
                {LEVERS.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="goal-seek-target">Target excess availability ($)</Label>
            <Input
              id="goal-seek-target"
              type="number"
              inputMode="decimal"
              placeholder="e.g. 5000000"
              className="tnum"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onSolve();
              }}
            />
          </div>
        </div>

        <div>
          <Button onClick={onSolve} disabled={!canSolve}>
            {loading ? "Solving…" : "Solve"}
          </Button>
        </div>

        {error ? (
          <p className="text-sm text-bad" role="alert">
            {error}
          </p>
        ) : null}

        {result ? <GoalSeekOutcome result={result} /> : null}
      </CardContent>
    </Card>
  );
}

function GoalSeekOutcome({ result }: { result: GoalSeekResult }) {
  // All current levers are fractions; render the solved value as a percentage.
  const solvedDisplay = pct(result.solved_value, 1);

  return (
    <div
      className={cn(
        "rounded-md border p-4",
        result.reachable ? "bg-ok-bg" : "bg-bad-bg",
      )}
    >
      {result.reachable ? (
        <>
          <div className="text-xl font-serif font-semibold leading-tight text-card-foreground">
            Set {result.label} to{" "}
            <span className="tnum text-primary">{solvedDisplay}</span>
          </div>
          <div className="mt-1.5 text-sm text-muted-foreground tnum">
            →{" "}
            <span className="font-medium text-ok">
              {money(result.achieved_excess)}
            </span>{" "}
            excess availability (now {money(result.baseline_excess)})
          </div>
        </>
      ) : (
        <div className="text-sm font-medium text-bad">Target not reachable</div>
      )}

      <p
        className={cn(
          "mt-2 text-xs",
          result.reachable ? "text-muted-foreground" : "text-bad",
        )}
      >
        {result.message}
      </p>
    </div>
  );
}
