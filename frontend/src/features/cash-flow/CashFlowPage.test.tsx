import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CashFlowPage } from "./CashFlowPage";

const { fixture } = vi.hoisted(() => {
  const cell = (week: number, forecast: string) => ({ week, forecast, contractual: forecast });
  return {
    fixture: {
      run_id: "test",
      available: true,
      forecast: {
        run_id: "test",
        borrower: "Test Distribution Co",
        as_of_date: "2025-12-31",
        anchor_date: "2026-01-05",
        horizon_weeks: 2,
        opening_cash: "1500000",
        cash_floor: "1000000",
        timing_method: "behavioral",
        inflow_rows: [
          {
            category: "Domestic Trading",
            segment: "Domestic Trading",
            kind: "inflow",
            weeks: [cell(1, "800000"), cell(2, "900000")],
            period_total: "1700000",
            period_total_contractual: "1700000",
          },
        ],
        outflow_rows: [
          {
            category: "Payroll",
            segment: "Treasury / Overhead",
            kind: "outflow",
            weeks: [cell(1, "-950000"), cell(2, "-1450000")],
            period_total: "-2400000",
            period_total_contractual: "-2400000",
          },
        ],
        positions: [
          {
            week: 1, week_start: "2026-01-05", total_receipts: "800000",
            total_disbursements: "-950000", net: "-150000", opening: "1500000",
            closing: "1350000", closing_contractual: "1350000", below_floor: false,
          },
          {
            week: 2, week_start: "2026-01-12", total_receipts: "900000",
            total_disbursements: "-1450000", net: "-550000", opening: "1350000",
            closing: "800000", closing_contractual: "1350000", below_floor: true,
          },
        ],
        kpis: {
          min_closing: "800000", min_closing_week: 2, total_receipts: "1700000",
          total_disbursements: "-2400000", net_cash_flow: "-700000", avg_weekly_net: "-350000",
          weeks_below_floor: 1, exception_count: 1,
        },
        kpis_contractual: {
          min_closing: "1350000", min_closing_week: 1, total_receipts: "1700000",
          total_disbursements: "-2400000", net_cash_flow: "-700000", avg_weekly_net: "-350000",
          weeks_below_floor: 0, exception_count: 1,
        },
        exceptions: [
          {
            row_id: "CF0001", type: "Net AP", party: "Reynolds Consumer Products",
            segment: "Domestic Trading", amount: "-300000", reason_code: "Dispute",
            suggested_action: "Escalate to controller", settle_date: "2026-01-10",
          },
        ],
        segment_lags: [
          { segment: "Domestic Trading", avg_lag_days: "5.00", std_dev_days: "0.80", sample_count: 18 },
        ],
        ledger: [
          {
            row_id: "CF0001", po_so: "AP-0001", type: "Net AP", party: "Reynolds Consumer Products",
            segment: "Domestic Trading", category: "Payroll", kind: "outflow", amount: "-300000",
            settle_date: "2026-01-10", expected_date: "2026-01-15", lag_days: "5.0",
            lag_basis: "SEGMENT", week: 1,
          },
        ],
      },
    },
  };
});

vi.mock("@/hooks/queries", () => ({
  useCashFlow: () => ({ data: fixture, isLoading: false, isError: false, error: null, refetch: () => {} }),
}));
// Recharts' ResponsiveContainer needs layout; stub the chart so jsdom stays clean.
vi.mock("@/features/cash-flow/ClosingCashChart", () => ({ ClosingCashChart: () => null }));

describe("CashFlowPage", () => {
  it("renders the forecast header, liquidity alert, KPIs, grid, and exceptions", () => {
    render(<CashFlowPage />);

    expect(screen.getByRole("heading", { name: /13-week cash flow forecast/i })).toBeInTheDocument();
    expect(screen.getByText(/liquidity alert/i)).toBeInTheDocument();
    expect(screen.getByText(/weeks below floor/i)).toBeInTheDocument();
    // grid rows + exceptions register
    expect(screen.getAllByText(/domestic trading/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/payroll/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/dispute/i)).toBeInTheDocument();
    expect(screen.getByText(/escalate to controller/i)).toBeInTheDocument();
  });
});
