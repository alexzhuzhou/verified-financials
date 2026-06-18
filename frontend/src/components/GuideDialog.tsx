import { PlayCircle } from "lucide-react";
import type { ReactNode } from "react";

import wordmark from "@/assets/brand/wordmark.png";
import { Term } from "@/components/Term";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface Capability {
  step: string;
  title: string;
  body: ReactNode;
}

const CAPABILITIES: Capability[] = [
  {
    step: "01",
    title: "Verification",
    body: (
      <>
        We cross-check the client's numbers across every file they sent and flag
        anything that doesn't reconcile, so you know the data is trustworthy before
        you lend against it. Each figure keeps its{" "}
        <Term name="provenance">provenance</Term> — a trail back to its source.
      </>
    ),
  },
  {
    step: "02",
    title: "Borrowing base",
    body: (
      <>
        We apply the facility's eligibility rules to work out how much the client can
        actually borrow — the certificate and the{" "}
        <Term name="borrowing base">borrowing base</Term> waterfall that turns raw
        collateral into <Term name="excess availability">available</Term> credit.
      </>
    ),
  },
  {
    step: "03",
    title: "FCCR covenant",
    body: (
      <>
        We track the trailing-twelve-month{" "}
        <Term name="FCCR">coverage ratio</Term> against the{" "}
        <Term name="covenant">covenant</Term> the loan requires, with early warning
        well before the client risks a breach.
      </>
    ),
  },
];

const HOW_TO: ReactNode[] = [
  <>Switch scenarios from the selector in the top-right corner.</>,
  <>
    Edit any rule in the <span className="font-medium text-foreground">What-if</span>{" "}
    panel and watch every figure recompute live.
  </>,
  <>Click any underlined number to see exactly where it came from.</>,
  <>
    Bring your own data — upload CSVs from{" "}
    <span className="font-medium text-foreground">Upload Data</span>.
  </>,
];

/**
 * A warm first-visit welcome guide that teaches a non-finance user what the app
 * does (verification, borrowing base, FCCR covenant) and how to drive it. Shown on
 * first load and reopenable from a help button; the parent owns the open state.
 */
export function GuideDialog({ open, onOpenChange }: Props) {
  const startTour = useAppStore((s) => s.startTour);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] gap-0 overflow-y-auto p-0">
        <DialogHeader className="space-y-2 px-6 pb-5 pt-6">
          <img src={wordmark} alt="Red Lion Advisory" className="mb-1 h-7 w-auto" />
          <DialogTitle className="text-2xl">Welcome to Verified Financials</DialogTitle>
          <DialogDescription className="leading-relaxed">
            From a boutique advisor's lens: can we trust the data, how much can they
            borrow, and are they healthy enough to keep the loan?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 border-t bg-muted/40 px-6 py-5">
          {CAPABILITIES.map((cap) => (
            <div
              key={cap.step}
              className="flex gap-4 rounded-lg border bg-card p-4 shadow-sm"
            >
              <span className="tnum select-none font-serif text-sm font-semibold text-primary">
                {cap.step}
              </span>
              <div className="space-y-1">
                <h3 className="font-serif text-base font-semibold leading-tight">
                  {cap.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {cap.body}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-3 border-t px-6 py-5">
          <h3 className="font-serif text-base font-semibold">How to use it</h3>
          <ul className="space-y-2.5">
            {HOW_TO.map((item, i) => (
              <li key={i} className="flex gap-3 text-sm leading-relaxed">
                <span
                  className={cn(
                    "tnum mt-0.5 flex h-5 w-5 flex-none items-center justify-center",
                    "rounded-full bg-primary/10 text-xs font-semibold text-primary",
                  )}
                >
                  {i + 1}
                </span>
                <span className="text-muted-foreground">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex justify-end gap-2 border-t bg-muted/40 px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Explore on my own
          </Button>
          <Button onClick={startTour}>
            <PlayCircle className="h-4 w-4" /> Start the guided tour
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
