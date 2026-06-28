"""13-week cash-flow forecast engine.

Builds a direct, bottom-up forecast from the cash-event ledger:

  1. derive the average days-late lag per party / segment / portfolio from the
     paid-history sample (the timing engine's calibration);
  2. place each cash event in a forecast week under two edges — *contractual*
     (cash on the settle date) and *behavioral* (settle date + the lag) — with
     fixed costs and manual entries bypassing the lag engine;
  3. stack the events into a weekly waterfall of receipts and disbursements,
     rolling opening cash to closing cash; and
  4. summarize the trough, the weeks below floor, and the open exceptions.

Every figure traces back to the ledger rows behind it (returned as the audit
trail) so the forecast is auditable end to end.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from ..config.schema import Config
from ..models.cash_flow import (
    CashFlowException,
    CashFlowForecast,
    CashFlowKpis,
    CategoryRow,
    LedgerLine,
    SegmentLag,
    WeeklyCell,
    WeekPosition,
)
from ..store.repository import FactRepository

ZERO = Decimal("0")
CENT = Decimal("0.01")
DAY = Decimal("1")

# Preferred display order; unknown segments fall back to alphabetical after these.
_SEGMENT_ORDER = [
    "Domestic Trading", "International Trading", "3PL", "Warehouse", "MHS",
    "Transportation", "Treasury / Overhead",
]


def _round_days(lag: Decimal) -> int:
    return int(lag.to_integral_value(rounding=ROUND_HALF_UP))


def _mean(values: list[Decimal]) -> Decimal:
    return (sum(values, ZERO) / Decimal(len(values))) if values else ZERO


def _std(values: list[Decimal], mean: Decimal) -> Decimal:
    if len(values) < 2:
        return ZERO
    var = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(len(values))
    return Decimal(str(float(var) ** 0.5))


def _week_of(d: date, anchor: date, horizon: int) -> int:
    """1-based forecast week, or 0 if the date falls outside the horizon."""
    offset = (d - anchor).days
    if offset < 0:
        return 1
    w = offset // 7 + 1
    return w if 1 <= w <= horizon else 0


def _cat_sort_key(category: str, kind: str, fixed_types: list[str]):
    if category in _SEGMENT_ORDER:
        return (0, _SEGMENT_ORDER.index(category), category)
    if category in fixed_types:
        return (1, fixed_types.index(category), category)
    if category == "Manual Forecast":
        return (2, 0, category)
    return (3, 0, category)


def compute_cash_flow(repo: FactRepository, config: Config, run_id: str) -> CashFlowForecast:
    cf = config.cash_flow
    anchor = cf.anchor_date
    horizon = cf.horizon_weeks
    floor = cf.cash_floor
    fixed_types = list(cf.fixed_cost_types)
    shift = cf.global_lag_shift_days

    # --- 1. lag table from the paid-history sample ---
    history = repo.query(dataset="paid_history", metric="days_late")
    by_party: dict[str, list[Decimal]] = {}
    by_segment: dict[str, list[Decimal]] = {}
    for fct in history:
        by_party.setdefault(fct.entity or "", []).append(fct.value)
        by_segment.setdefault(fct.attributes.get("segment", ""), []).append(fct.value)
    all_lags = [f.value for f in history]
    portfolio_lag = _mean(all_lags)
    party_mean = {p: _mean(v) for p, v in by_party.items()}
    segment_mean = {s: _mean(v) for s, v in by_segment.items()}

    def lag_for(party: str, segment: str) -> tuple[Decimal, str]:
        if len(by_party.get(party, [])) >= cf.lag_fallback_min_samples:
            return party_mean[party], "PARTY"
        if by_segment.get(segment):
            return segment_mean[segment], "SEGMENT"
        return portfolio_lag, "PORTFOLIO"

    # --- 2. place each event under both edges ---
    events = repo.query(dataset="cash_events", metric="amount")
    ledger: list[LedgerLine] = []
    exceptions: list[CashFlowException] = []

    # aggregates: cat_key -> {"row": meta, "fc": {week: amt}, "ct": {week: amt}}
    rows: dict[tuple[str, str], dict] = {}
    # weekly position accumulators (behavioral + contractual)
    fc_recv = [ZERO] * (horizon + 1)
    fc_disb = [ZERO] * (horizon + 1)
    ct_recv = [ZERO] * (horizon + 1)
    ct_disb = [ZERO] * (horizon + 1)

    for fct in events:
        a = fct.attributes
        typ = a.get("type", "")
        party = a.get("party", "—")
        segment = a.get("segment", "")
        amount = fct.value
        kind = "inflow" if amount > 0 else "outflow"
        due = date.fromisoformat(a["due_date"])

        if typ in fixed_types:
            lag, basis = ZERO, "FIXED"
            c_date = b_date = due
            category = typ
        elif typ.startswith("Manual"):
            lag, basis = ZERO, "MANUAL"
            c_date = b_date = due
            category = "Manual Forecast"
        else:
            lag, basis = lag_for(party, segment)
            lag = lag + shift
            lag_days = _round_days(lag)
            # Contractual edge = the settle date, clamped into the forecast window
            # (cash can't be collected before week 1). Behavioral = settle + the lag.
            # Already-overdue "Aging" items follow the McLane rule: clamp the settle to
            # the anchor BEFORE adding the lag (max(anchor, due) + lag), pulling
            # past-dues into an early week; normal items are simply due + lag.
            c_date = max(anchor, due)
            b_date = (c_date if typ.startswith("Aging") else due) + timedelta(days=lag_days)
            category = segment

        b_week = _week_of(b_date, anchor, horizon)
        c_week = _week_of(c_date, anchor, horizon)

        ledger.append(LedgerLine(
            row_id=fct.entity or fct.id, po_so=a.get("po_so", ""),
            type=typ, party=party, segment=segment,
            category=category, kind=kind, amount=amount.quantize(CENT),
            settle_date=due, expected_date=b_date,
            lag_days=lag.quantize(Decimal("0.1")), lag_basis=basis, week=b_week,
        ))

        if a.get("exception_flag"):
            exceptions.append(CashFlowException(
                row_id=fct.entity or fct.id, type=typ, party=party, segment=segment,
                amount=amount.quantize(CENT), reason_code=a.get("exception_reason", ""),
                suggested_action=a.get("suggested_action", ""), settle_date=due,
            ))

        key = (kind, category)
        bucket = rows.setdefault(key, {"kind": kind, "category": category, "segment": segment,
                                       "fc": {}, "ct": {}})
        if b_week:
            bucket["fc"][b_week] = bucket["fc"].get(b_week, ZERO) + amount
            (fc_recv if kind == "inflow" else fc_disb)[b_week] += amount
        if c_week:
            bucket["ct"][c_week] = bucket["ct"].get(c_week, ZERO) + amount
            (ct_recv if kind == "inflow" else ct_disb)[c_week] += amount

    # --- 3. category rows ---
    def make_rows(kind: str) -> list[CategoryRow]:
        out = []
        for (k, _cat), b in rows.items():
            if k != kind:
                continue
            weeks = [
                WeeklyCell(
                    week=w,
                    forecast=b["fc"].get(w, ZERO).quantize(CENT),
                    contractual=b["ct"].get(w, ZERO).quantize(CENT),
                )
                for w in range(1, horizon + 1)
            ]
            out.append(CategoryRow(
                category=b["category"], segment=b["segment"], kind=kind, weeks=weeks,
                period_total=sum(b["fc"].values(), ZERO).quantize(CENT),
                period_total_contractual=sum(b["ct"].values(), ZERO).quantize(CENT),
            ))
        out.sort(key=lambda r: _cat_sort_key(r.category, kind, fixed_types))
        return out

    inflow_rows = make_rows("inflow")
    outflow_rows = make_rows("outflow")

    # --- 4. weekly positions + roll-forward (both edges) ---
    positions: list[WeekPosition] = []
    fc_open = ct_open = cf.opening_cash
    for w in range(1, horizon + 1):
        fc_net = fc_recv[w] + fc_disb[w]
        fc_close = fc_open + fc_net
        ct_close = ct_open + ct_recv[w] + ct_disb[w]
        positions.append(WeekPosition(
            week=w, week_start=anchor + timedelta(days=7 * (w - 1)),
            total_receipts=fc_recv[w].quantize(CENT),
            total_disbursements=fc_disb[w].quantize(CENT),
            net=fc_net.quantize(CENT),
            opening=fc_open.quantize(CENT),
            closing=fc_close.quantize(CENT),
            closing_contractual=ct_close.quantize(CENT),
            below_floor=fc_close < floor,
        ))
        fc_open, ct_open = fc_close, ct_close

    # --- 5. KPIs (behavioral primary + contractual edge) ---
    def kpis(closings: list[Decimal], recv: list[Decimal], disb: list[Decimal]) -> CashFlowKpis:
        lo = min(closings)
        tr = sum(recv[1:], ZERO)
        td = sum(disb[1:], ZERO)
        net = tr + td
        return CashFlowKpis(
            min_closing=lo.quantize(CENT),
            min_closing_week=closings.index(lo) + 1,
            total_receipts=tr.quantize(CENT),
            total_disbursements=td.quantize(CENT),
            net_cash_flow=net.quantize(CENT),
            avg_weekly_net=(net / Decimal(horizon)).quantize(CENT),
            weeks_below_floor=sum(1 for c in closings if c < floor),
            exception_count=len(exceptions),
        )

    fc_closings = [p.closing for p in positions]
    ct_closings = [p.closing_contractual for p in positions]
    kpis_fc = kpis(fc_closings, fc_recv, fc_disb)
    kpis_ct = kpis(ct_closings, ct_recv, ct_disb)

    # --- 6. segment lag table (display) ---
    segment_lags = [
        SegmentLag(
            segment=seg,
            avg_lag_days=segment_mean[seg].quantize(Decimal("0.01")),
            std_dev_days=_std(by_segment[seg], segment_mean[seg]).quantize(Decimal("0.01")),
            sample_count=len(by_segment[seg]),
        )
        for seg in sorted(by_segment, key=lambda s: _cat_sort_key(s, "inflow", fixed_types))
    ]

    return CashFlowForecast(
        run_id=run_id,
        borrower=config.facility.borrower,
        as_of_date=config.facility.as_of_date,
        anchor_date=anchor,
        horizon_weeks=horizon,
        opening_cash=cf.opening_cash.quantize(CENT),
        cash_floor=floor.quantize(CENT),
        timing_method=cf.timing_method,
        inflow_rows=inflow_rows,
        outflow_rows=outflow_rows,
        positions=positions,
        kpis=kpis_fc,
        kpis_contractual=kpis_ct,
        exceptions=exceptions,
        segment_lags=segment_lags,
        ledger=ledger,
    )
