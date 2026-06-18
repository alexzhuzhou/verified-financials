import type { ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useConfig, useConfigScenario } from "@/hooks/queries";
import { pct, titleize } from "@/lib/format";
import { useAppStore } from "@/lib/store";
import type { AppConfig } from "@/lib/types";

function getAt(obj: any, path: string[]): any {
  return path.reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-3 border-b py-4 last:border-b-0">
      <h3 className="font-serif text-sm font-semibold uppercase tracking-wide text-primary">{title}</h3>
      {children}
    </div>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  display,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <span className="tnum text-xs font-semibold">{display}</span>
      </div>
      <Slider min={min} max={max} step={step} value={[value]} onValueChange={(v) => onChange(v[0])} />
    </div>
  );
}

function SwitchRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <Label>{label}</Label>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

export function WhatIfPanel() {
  const scenario = useConfigScenario();
  const overrides = useAppStore((s) => s.overrides);
  const setOverride = useAppStore((s) => s.setOverride);
  const { data: base } = useConfig(scenario);

  if (!base) return <div className="p-4 text-sm text-muted-foreground">Loading rules…</div>;

  const eff = (path: string[]): any => {
    const o = getAt(overrides, path);
    return o !== undefined ? o : getAt(base, path);
  };
  const num = (path: string[]): number => Number(eff(path));

  const ar = ["borrowing_base", "accounts_receivable"];
  const inv = ["borrowing_base", "inventory"];
  const nolvCats = Object.keys(((base as AppConfig).borrowing_base?.inventory?.nolv_by_category) ?? {});
  const reserves: any[] = eff(["borrowing_base", "reserves"]) ?? [];

  const setReserve = (idx: number, field: string, value: string) => {
    const next = reserves.map((r, i) => (i === idx ? { ...r, [field]: value } : { ...r }));
    setOverride(["borrowing_base", "reserves"], next);
  };

  // NOLV already bakes in the liquidation haircut, so it's advanced at a much
  // higher rate than cost (≈80% vs 50%). Snap the advance rate to the mode's
  // typical default whenever valuation changes, so the two can't drift apart.
  const setValuation = (v: string) => {
    setOverride([...inv, "valuation"], v);
    setOverride([...inv, "advance_rate"], v === "nolv" ? "0.80" : "0.50");
  };

  return (
    <div className="px-4">
      <div className="py-3">
        <h2 className="font-serif text-base font-semibold">What-if</h2>
        <p className="text-xs text-muted-foreground">Edit the agreement; everything recomputes live.</p>
      </div>

      <Section title="Facility">
        <div className="space-y-1.5">
          <Label>Revolver commitment ($)</Label>
          <Input type="number" step="1000000" value={String(eff(["facility", "commitment"]))}
            onChange={(e) => setOverride(["facility", "commitment"], e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Outstanding drawn ($)</Label>
          <Input type="number" step="1000000" value={String(eff(["facility", "outstanding"]))}
            onChange={(e) => setOverride(["facility", "outstanding"], e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>As-of date</Label>
          <Input type="date" value={String(eff(["facility", "as_of_date"]))}
            onChange={(e) => setOverride(["facility", "as_of_date"], e.target.value)} />
        </div>
      </Section>

      <Section title="Accounts Receivable">
        <SliderRow label="Advance rate" value={num([...ar, "advance_rate"])} min={0.5} max={1} step={0.01}
          display={pct(num([...ar, "advance_rate"]), 0)}
          onChange={(v) => setOverride([...ar, "advance_rate"], v.toFixed(2))} />
        <SliderRow label="Concentration cap" value={num([...ar, "concentration_cap", "pct"])} min={0.05} max={0.5} step={0.01}
          display={pct(num([...ar, "concentration_cap", "pct"]), 0)}
          onChange={(v) => setOverride([...ar, "concentration_cap", "pct"], v.toFixed(2))} />
        <div className="space-y-1.5">
          <Label>Concentration basis</Label>
          <Select value={String(eff([...ar, "concentration_cap", "basis"]))}
            onValueChange={(v) => setOverride([...ar, "concentration_cap", "basis"], v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="post_categorical">Post-categorical base</SelectItem>
              <SelectItem value="gross">Gross A/R</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <SwitchRow label="Cross-aging taint" checked={Boolean(eff([...ar, "cross_aging", "enabled"]))}
          onChange={(v) => setOverride([...ar, "cross_aging", "enabled"], v)} />
        {Boolean(eff([...ar, "cross_aging", "enabled"])) && (
          <SliderRow label="Cross-age threshold" value={num([...ar, "cross_aging", "threshold_pct"])} min={0.2} max={0.9} step={0.05}
            display={pct(num([...ar, "cross_aging", "threshold_pct"]), 0)}
            onChange={(v) => setOverride([...ar, "cross_aging", "threshold_pct"], v.toFixed(2))} />
        )}
      </Section>

      <Section title="Inventory">
        <div className="space-y-1.5">
          <Label>Valuation</Label>
          <Select value={String(eff([...inv, "valuation"]))} onValueChange={setValuation}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="cost">% of cost</SelectItem>
              <SelectItem value="nolv">% of NOLV (per-category)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <SliderRow label="Advance rate" value={num([...inv, "advance_rate"])} min={0.2} max={1} step={0.01}
          display={pct(num([...inv, "advance_rate"]), 0)}
          onChange={(v) => setOverride([...inv, "advance_rate"], v.toFixed(2))} />
        {String(eff([...inv, "valuation"])) === "nolv" &&
          nolvCats.map((cat) => (
            <SliderRow key={cat} label={`NOLV — ${cat}`} value={num([...inv, "nolv_by_category", cat])} min={0.1} max={1} step={0.05}
              display={pct(num([...inv, "nolv_by_category", cat]), 0)}
              onChange={(v) => setOverride([...inv, "nolv_by_category", cat], v.toFixed(2))} />
          ))}
      </Section>

      <Section title="Reserves">
        {reserves.length === 0 && <p className="text-xs text-muted-foreground">None in this agreement.</p>}
        {reserves.map((r, i) => (
          <div key={r.id} className="space-y-1.5">
            <Label>{titleize(r.type)} — {r.label?.split("(")[0]}</Label>
            {r.type === "dilution" ? (
              <div className="flex gap-2">
                <Input type="number" step="0.01" value={r.dilution_pct ?? "0"} title="dilution %"
                  onChange={(e) => setReserve(i, "dilution_pct", e.target.value)} />
                <Input type="number" step="0.01" value={r.threshold_pct ?? "0"} title="threshold %"
                  onChange={(e) => setReserve(i, "threshold_pct", e.target.value)} />
              </div>
            ) : (
              <Input type="number" step="50000" value={r.amount ?? "0"}
                onChange={(e) => setReserve(i, "amount", e.target.value)} />
            )}
          </div>
        ))}
      </Section>

      <Section title="FCCR Covenant">
        <SliderRow label="Covenant threshold" value={num(["fccr", "covenant_threshold"])} min={1.0} max={1.5} step={0.05}
          display={`${num(["fccr", "covenant_threshold"]).toFixed(2)}x`}
          onChange={(v) => setOverride(["fccr", "covenant_threshold"], v.toFixed(2))} />
        <SwitchRow label="Springing covenant" checked={Boolean(eff(["fccr", "springing", "enabled"]))}
          onChange={(v) => setOverride(["fccr", "springing", "enabled"], v)} />
        {Boolean(eff(["fccr", "springing", "enabled"])) && (
          <>
            <SliderRow label="Trigger (% of commitment)" value={num(["fccr", "springing", "trigger_pct"])} min={0.05} max={0.3} step={0.025}
              display={pct(num(["fccr", "springing", "trigger_pct"]), 1)}
              onChange={(v) => setOverride(["fccr", "springing", "trigger_pct"], v.toFixed(3))} />
            <div className="space-y-1.5">
              <Label>Trigger floor ($)</Label>
              <Input type="number" step="500000" value={String(eff(["fccr", "springing", "trigger_floor"]))}
                onChange={(e) => setOverride(["fccr", "springing", "trigger_floor"], e.target.value)} />
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
