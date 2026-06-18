import type { ReactNode } from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { GLOSSARY } from "@/lib/glossary";
import { cn } from "@/lib/utils";

interface Props {
  name: string;
  children?: ReactNode;
  className?: string;
}

/** Case-insensitive lookup of a glossary definition, returning the matched key too. */
function lookup(name: string): { key: string; definition: string } | null {
  if (GLOSSARY[name]) return { key: name, definition: GLOSSARY[name] };
  const lower = name.toLowerCase();
  for (const key of Object.keys(GLOSSARY)) {
    if (key.toLowerCase() === lower) return { key, definition: GLOSSARY[key] };
  }
  return null;
}

/**
 * A teaching tooltip: renders an inline term with a subtle dotted underline that,
 * on hover or focus, reveals a plain-English definition in a small popover card.
 * If the term isn't in the glossary, the children render as-is with no tooltip.
 */
export function Term({ name, children, className }: Props) {
  const entry = lookup(name);
  const label = children ?? name;

  if (!entry) {
    return <span className={className}>{label}</span>;
  }

  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>
        <span
          tabIndex={0}
          className={cn(
            "cursor-help border-b border-dotted border-muted-foreground/60 outline-none",
            "focus-visible:ring-2 focus-visible:ring-primary/40 rounded-sm",
            className,
          )}
        >
          {label}
        </span>
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side="top"
          align="center"
          sideOffset={6}
          collisionPadding={8}
          className={cn(
            "z-50 max-w-xs rounded-md border bg-card p-3 text-sm text-card-foreground shadow-md",
            "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=delayed-open]:fade-in-0",
          )}
        >
          <p className="mb-1 font-serif font-semibold leading-tight">{entry.key}</p>
          <p className="text-muted-foreground leading-snug">{entry.definition}</p>
          <TooltipPrimitive.Arrow className="fill-card" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
