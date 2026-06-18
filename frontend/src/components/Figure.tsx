import { ProvenanceDialog } from "@/components/ProvenanceDialog";
import { money } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Props {
  value: string | number | null | undefined;
  dataset?: string;
  metric?: string;
  entity?: string;
  className?: string;
}

/** A monetary figure. When a dataset is given, it becomes a clickable
 *  provenance link revealing the source facts behind the number. */
export function Figure({ value, dataset, metric, entity, className }: Props) {
  if (!dataset) {
    return <span className={cn("tnum", className)}>{money(value)}</span>;
  }
  return (
    <ProvenanceDialog
      dataset={dataset}
      metric={metric}
      entity={entity}
      trigger={
        <button
          type="button"
          title="Click for source provenance"
          className={cn(
            "tnum cursor-pointer underline decoration-dotted decoration-muted-foreground/50 underline-offset-4 hover:text-primary hover:decoration-primary",
            className,
          )}
        >
          {money(value)}
        </button>
      }
    />
  );
}
