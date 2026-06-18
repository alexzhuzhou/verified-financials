import { Badge } from "@/components/ui/badge";
import type { FccrReport } from "@/lib/types";

export function fccrStatus(r: FccrReport): { label: string; variant: "ok" | "warn" | "bad" } {
  if (r.springing_enabled && !r.covenant_active) return { label: "Not tested", variant: "ok" };
  if (!r.in_compliance) return { label: "Breach", variant: "bad" };
  if (r.early_warning) return { label: "Watch", variant: "warn" };
  return { label: "In compliance", variant: "ok" };
}

export function FccrStatusBadge({ report }: { report: FccrReport }) {
  const s = fccrStatus(report);
  return <Badge variant={s.variant}>{s.label}</Badge>;
}
