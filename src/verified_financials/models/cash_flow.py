"""13-week cash-flow forecast result DTOs.

The forecast is built bottom-up from a ledger of individual cash events. Each
event is placed in a week by the timing engine (contractual vs behavioral), then
stacked into a weekly waterfall of receipts and disbursements that rolls opening
cash to closing cash. Every figure traces back to the ledger rows behind it.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LedgerLine(BaseModel):
    """One cash event, timed — the audit trail behind every grid cell."""

    model_config = ConfigDict(extra="forbid")

    row_id: str
    po_so: str                                 # source-document reference (e.g. AR-0001)
    type: str                                  # Net AR, Net AP, Payroll, ...
    party: str                                 # customer / vendor / "—"
    segment: str
    category: str                              # the waterfall row it lands in
    kind: str                                  # "inflow" | "outflow"
    amount: Decimal                            # signed (+ in / − out)
    settle_date: date                          # contractual due date
    expected_date: date                        # behavioral (settle + lag)
    lag_days: Decimal
    lag_basis: str                             # PARTY | SEGMENT | PORTFOLIO | FIXED | MANUAL
    week: int                                  # behavioral week (1..horizon; 0 if out of horizon)


class WeeklyCell(BaseModel):
    """A single (category, week) amount under both timing edges."""

    model_config = ConfigDict(extra="forbid")

    week: int
    forecast: Decimal                          # behavioral (primary) amount
    contractual: Decimal                       # contractual edge amount


class CategoryRow(BaseModel):
    """One waterfall row (a segment's receipts, a fixed cost, etc.) across weeks."""

    model_config = ConfigDict(extra="forbid")

    category: str
    segment: str
    kind: str                                  # "inflow" | "outflow"
    weeks: list[WeeklyCell] = Field(default_factory=list)
    period_total: Decimal                      # behavioral sum across the horizon
    period_total_contractual: Decimal


class WeekPosition(BaseModel):
    """The cash position for one week — the bottom of the waterfall block."""

    model_config = ConfigDict(extra="forbid")

    week: int
    week_start: date
    total_receipts: Decimal
    total_disbursements: Decimal               # negative
    net: Decimal
    opening: Decimal
    closing: Decimal
    closing_contractual: Decimal               # the band's optimistic edge
    below_floor: bool
    actual_closing: Decimal | None = None      # reported actual (closed weeks only)
    variance_closing: Decimal | None = None    # actual − forecast (closed weeks only)


class CashFlowKpis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_closing: Decimal
    min_closing_week: int
    total_receipts: Decimal
    total_disbursements: Decimal
    net_cash_flow: Decimal
    avg_weekly_net: Decimal
    weeks_below_floor: int
    exception_count: int


class CashFlowException(BaseModel):
    """A ledger row that needs a human decision before the forecast can trust it."""

    model_config = ConfigDict(extra="forbid")

    row_id: str
    type: str
    party: str
    segment: str
    amount: Decimal
    reason_code: str
    suggested_action: str
    settle_date: date


class SegmentLag(BaseModel):
    """Observed payment behavior for a segment (drives the behavioral edge)."""

    model_config = ConfigDict(extra="forbid")

    segment: str
    avg_lag_days: Decimal
    std_dev_days: Decimal
    sample_count: int


class CashFlowForecast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    borrower: str
    as_of_date: date
    anchor_date: date
    horizon_weeks: int
    opening_cash: Decimal
    cash_floor: Decimal
    timing_method: str

    inflow_rows: list[CategoryRow] = Field(default_factory=list)
    outflow_rows: list[CategoryRow] = Field(default_factory=list)
    positions: list[WeekPosition] = Field(default_factory=list)

    kpis: CashFlowKpis                          # behavioral (primary)
    kpis_contractual: CashFlowKpis              # the band's optimistic edge

    actuals_through_week: int = 0               # how many weeks have reported actuals
    variance_to_date: Decimal = Decimal("0")    # actual − forecast closing at the last closed week

    exceptions: list[CashFlowException] = Field(default_factory=list)
    segment_lags: list[SegmentLag] = Field(default_factory=list)
    ledger: list[LedgerLine] = Field(default_factory=list)
