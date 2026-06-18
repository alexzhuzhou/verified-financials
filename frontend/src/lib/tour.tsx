import type { ReactNode } from "react";

import { Term } from "@/components/Term";
import type { Overrides } from "@/lib/types";

export interface TourStep {
  /** Route the tour navigates to for this step. */
  route: string;
  /** Scenario to set (explicit each step so the walk-through is deterministic). */
  scenario: "baseline" | "stress";
  /** Optional what-if to apply (cleared otherwise). Unused today; kept for future beats. */
  overrides?: Overrides;
  /** Optional element id to scroll to + ring. Best-effort — a no-op if absent. */
  highlight?: string;
  title: string;
  body: ReactNode;
}

/**
 * A product walk-through that explains what the application does on each screen —
 * verification, the borrowing-base engine, the live certificate, and covenant
 * monitoring — using the demo's (synthetic, golden-locked) figures as illustration.
 */
export const TOUR: TourStep[] = [
  {
    route: "/app",
    scenario: "baseline",
    highlight: "tour-kpis",
    title: "What this tool does",
    body: (
      <>
        Verified Financials takes a borrower's raw financials and answers three questions
        a lender cares about: can we trust the data, how much can they borrow, and are they
        on-side with their covenant? This Overview is the at-a-glance summary — every figure
        is computed from the underlying files (this demo runs on synthetic data). Let's walk
        through each capability.
      </>
    ),
  },
  {
    route: "/app/verification",
    scenario: "baseline",
    highlight: "tour-verification-summary",
    title: "Tie-out & verification",
    body: (
      <>
        First, the app cross-checks every number across the source files and flags anything
        that doesn't reconcile — here it surfaced three discrepancies. Every figure carries
        its <Term name="provenance">provenance</Term>, so any value can be traced straight
        back to the file it came from.
      </>
    ),
  },
  {
    route: "/app/borrowing-base",
    scenario: "baseline",
    highlight: "tour-waterfall",
    title: "The borrowing-base engine",
    body: (
      <>
        Next it applies the facility's eligibility rules — aged, foreign, and intercompany
        exclusions, concentration caps, and advance rates — to calculate how much can
        actually be borrowed. The <Term name="borrowing base">borrowing base</Term> waterfall
        shows every step from gross collateral down to availability.
      </>
    ),
  },
  {
    route: "/app/borrowing-base",
    scenario: "baseline",
    highlight: "tour-certificate-actions",
    title: "A bank-ready certificate, live",
    body: (
      <>
        From those figures the app produces the borrowing-base certificate a lender expects —
        one click to download. And it's fully live: change any rule in the What-if panel and
        the certificate recomputes instantly, with no spreadsheets to rebuild.
      </>
    ),
  },
  {
    route: "/app/fccr",
    scenario: "baseline",
    highlight: "tour-fccr-trend",
    title: "Covenant monitoring",
    body: (
      <>
        The app tracks the <Term name="FCCR">fixed-charge coverage ratio</Term> against the{" "}
        <Term name="covenant">covenant</Term> the loan requires, quarter over quarter, and
        raises an early warning as headroom thins — here it's compliant at 1.20x, but the
        trend is sliding.
      </>
    ),
  },
  {
    route: "/app/fccr",
    scenario: "stress",
    highlight: "tour-fccr-trend",
    title: "Scenario stress-testing",
    body: (
      <>
        Finally, you can stress the assumptions to see trouble before it arrives. Switching to
        the downturn scenario, coverage falls to a <strong>0.89x breach</strong> — the app
        flags the sprung covenant and the <strong>$1.9M</strong> equity cure it would take to
        restore compliance. That's the early warning paying off.
      </>
    ),
  },
];
