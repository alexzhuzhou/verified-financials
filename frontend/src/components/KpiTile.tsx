import * as React from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type KpiStatus = "ok" | "warn" | "bad" | "neutral";

export interface KpiTileProps {
  label: React.ReactNode; // string, or a <Term> for a teachable label
  value: React.ReactNode; // caller passes e.g. <AnimatedNumber value={...}/> or text
  sublabel?: React.ReactNode;
  status?: KpiStatus;
  delta?: React.ReactNode; // optional change indicator line (e.g. "+$1.1M vs filed")
  icon?: React.ReactNode;
  className?: string;
}

const ACCENT_VAR: Record<Exclude<KpiStatus, "neutral">, string> = {
  ok: "var(--ok)",
  warn: "var(--warn)",
  bad: "var(--bad)",
};

const DOT_CLASS: Record<KpiStatus, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  bad: "bg-bad",
  neutral: "bg-muted-foreground/40",
};

/**
 * Infer the directional tone of a delta when it is plain text.
 * "+..." => positive (green), "-..." => negative (red), otherwise muted.
 */
function deltaTone(delta: React.ReactNode): "up" | "down" | "flat" {
  if (typeof delta === "string" || typeof delta === "number") {
    const s = String(delta).trim();
    if (s.startsWith("+")) return "up";
    if (s.startsWith("-") || s.startsWith("−")) return "down";
  }
  return "flat";
}

export function KpiTile({
  label,
  value,
  sublabel,
  status = "neutral",
  delta,
  icon,
  className,
}: KpiTileProps) {
  const isNeutral = status === "neutral";
  const tone = deltaTone(delta);

  return (
    <Card
      className={cn(
        "relative overflow-hidden border-l-4 p-5 transition-shadow hover:shadow-md",
        isNeutral && "border-l-muted",
        className,
      )}
      style={
        isNeutral
          ? undefined
          : { borderLeftColor: `hsl(${ACCENT_VAR[status]})` }
      }
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {icon ? (
            <span className="text-muted-foreground [&_svg]:size-4">{icon}</span>
          ) : null}
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
        </div>
        <span
          className={cn("mt-1 size-2 shrink-0 rounded-full", DOT_CLASS[status])}
          aria-hidden
        />
      </div>

      <div className="mt-3 text-3xl font-serif font-semibold leading-tight tnum text-card-foreground">
        {value}
      </div>

      {sublabel ? (
        <div className="mt-1.5 text-xs text-muted-foreground">{sublabel}</div>
      ) : null}

      {delta != null && delta !== "" ? (
        <div
          className={cn(
            "mt-3 text-xs font-medium tnum",
            tone === "up" && "text-ok",
            tone === "down" && "text-bad",
            tone === "flat" && "text-muted-foreground",
          )}
        >
          {delta}
        </div>
      ) : null}
    </Card>
  );
}
