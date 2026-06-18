import { HelpCircle, PlayCircle, RotateCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useScenarios } from "@/hooks/queries";
import { useAppStore } from "@/lib/store";

export function TopBar() {
  const { data: scenarios } = useScenarios();
  const dataSource = useAppStore((s) => s.dataSource);
  const setScenario = useAppStore((s) => s.setScenario);
  const reset = useAppStore((s) => s.reset);
  const setGuideOpen = useAppStore((s) => s.setGuideOpen);
  const startTour = useAppStore((s) => s.startTour);
  const hasOverrides = useAppStore((s) => Object.keys(s.overrides).length > 0);
  const value = dataSource.kind === "upload" ? "custom" : dataSource.scenario;

  return (
    <header className="no-print flex items-center justify-between border-b bg-background px-6 py-3">
      <div>
        <div className="font-serif text-[11px] font-bold uppercase tracking-[0.18em] text-primary">
          Red Lion Advisory
        </div>
        <div className="font-serif text-xl font-semibold">Verified Financials</div>
      </div>

      <div className="flex items-center gap-3">
        {hasOverrides && (
          <>
            <Badge variant="warn">What-if active</Badge>
            <Button variant="outline" size="sm" onClick={reset}>
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </Button>
          </>
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Scenario</span>
          <Select value={value} onValueChange={(v) => v !== "custom" && setScenario(v)}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(scenarios ?? [{ id: "baseline", label: "Baseline", description: "" }]).map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.label}
                </SelectItem>
              ))}
              {dataSource.kind === "upload" && (
                <SelectItem value="custom">Custom (uploaded)</SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
        <Button variant="outline" size="sm" onClick={startTour}>
          <PlayCircle className="h-4 w-4" /> Guided tour
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setGuideOpen(true)} aria-label="Guide">
          <HelpCircle className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
