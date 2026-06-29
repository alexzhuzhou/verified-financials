import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { WeekPosition } from "@/lib/types";

export function ForecastVsActualCard({
  closed,
  actuals,
  onChange,
  onReset,
}: {
  closed: WeekPosition[];
  actuals: Record<number, number>;
  onChange: (week: number, value: number) => void;
  onReset: () => void;
}) {
  const last = closed[closed.length - 1];
  const toDate = last ? (actuals[last.week] ?? 0) - Number(last.closing) : 0;
  const tone = toDate < -0.5 ? "behind" : toDate > 0.5 ? "ahead" : "on plan";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-serif text-base">Forecast vs. actual — variance to date</CardTitle>
            <CardDescription>
              {closed.length} week(s) closed. Edit an actual to see variance and the chart update live.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onReset}>
            <RotateCcw className="h-4 w-4" /> Reset to reported
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Week</TableHead>
              <TableHead className="text-right">Forecast closing</TableHead>
              <TableHead className="text-right">Actual closing</TableHead>
              <TableHead className="text-right">Variance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {closed.map((p) => {
              const actual = actuals[p.week] ?? 0;
              const variance = actual - Number(p.closing);
              return (
                <TableRow key={p.week}>
                  <TableCell className="font-medium">W{p.week}</TableCell>
                  <TableCell className="text-right tnum">{money(p.closing, true)}</TableCell>
                  <TableCell className="text-right">
                    <Input
                      type="number"
                      step="10000"
                      className="ml-auto h-8 w-36 text-right tnum"
                      value={Number.isFinite(actual) ? actual : ""}
                      onChange={(e) => onChange(p.week, Number(e.target.value))}
                    />
                  </TableCell>
                  <TableCell
                    className={cn("text-right tnum font-medium", variance < 0 ? "text-bad" : variance > 0 ? "text-ok" : "")}
                  >
                    {variance >= 0 ? "+" : ""}{money(variance, true)}
                  </TableCell>
                </TableRow>
              );
            })}
            <TableRow className="border-t-2 font-semibold">
              <TableCell colSpan={3}>
                Variance to date — running <span className={cn(tone === "behind" && "text-bad", tone === "ahead" && "text-ok")}>{tone}</span>
              </TableCell>
              <TableCell className={cn("text-right tnum", toDate < 0 ? "text-bad" : toDate > 0 ? "text-ok" : "")}>
                {toDate >= 0 ? "+" : ""}{money(toDate, true)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
