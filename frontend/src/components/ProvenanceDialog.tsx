import { useState, type ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useFacts } from "@/hooks/queries";
import { money } from "@/lib/format";

interface Props {
  dataset: string;
  metric?: string;
  entity?: string;
  trigger: ReactNode;
}

export function ProvenanceDialog({ dataset, metric, entity, trigger }: Props) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useFacts(open ? { dataset, metric, entity } : null);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Source provenance</DialogTitle>
          <DialogDescription>
            {dataset}
            {metric ? `.${metric}` : ""}
            {entity ? ` · ${entity}` : ""} — every figure traces to its source file.
          </DialogDescription>
        </DialogHeader>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Entity</TableHead>
                <TableHead className="text-right">Value</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Version</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).map((f) => (
                <TableRow key={f.id}>
                  <TableCell>{f.entity ?? f.metric}</TableCell>
                  <TableCell className="text-right tnum">
                    {f.unit === "USD" ? money(f.value) : f.value}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {f.provenance.source_file} · {f.provenance.source_locator}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {f.provenance.version_tag ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
              {data && data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-sm text-muted-foreground">
                    No matching facts.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}
