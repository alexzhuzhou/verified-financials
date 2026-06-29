"""Timing-engine mechanics: week placement, fixed-cost bypass, roll-forward, what-if."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from verified_financials import datagen
from verified_financials.config.loader import load_config
from verified_financials.engines.cash_flow import compute_cash_flow
from verified_financials.loaders import cash_events, paid_history
from verified_financials.store.db import connect, init_schema
from verified_financials.store.repository import FactRepository

D = Decimal


def _repo(tmp_path, cfg, scenario="baseline"):
    datagen.generate(data_dir=tmp_path, seed=cfg.settings.random_seed, scenario=scenario)
    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    loaded = datetime.now()
    as_of = cfg.facility.as_of_date
    repo.add_many(cash_events.load(tmp_path / "cash_events.csv", as_of, loaded))
    repo.add_many(paid_history.load(tmp_path / "paid_history.csv", as_of, loaded))
    return repo


def test_roll_forward_is_consistent(tmp_path):
    cfg = load_config()
    f = compute_cash_flow(_repo(tmp_path, cfg), cfg, "test")
    assert f.positions[0].opening == f.opening_cash
    prev_close = None
    for p in f.positions:
        assert p.net == p.total_receipts + p.total_disbursements
        assert p.closing == p.opening + p.net
        if prev_close is not None:
            assert p.opening == prev_close
        prev_close = p.closing
    # totals tie to the weekly positions
    assert f.kpis.total_receipts == sum((p.total_receipts for p in f.positions), D("0"))
    assert f.kpis.total_disbursements == sum((p.total_disbursements for p in f.positions), D("0"))


def test_fixed_costs_bypass_the_lag_engine(tmp_path):
    cfg = load_config()
    f = compute_cash_flow(_repo(tmp_path, cfg), cfg, "test")
    payroll = [li for li in f.ledger if li.type == "Payroll"]
    assert payroll, "expected payroll events"
    for li in payroll:
        assert li.lag_basis == "FIXED"
        assert li.lag_days == D("0.0")
        assert li.expected_date == li.settle_date     # posts on its stated date
    # Payroll lands every 2 weeks at $900k -> $6.3M over the horizon (baseline)
    payroll_row = next(r for r in f.outflow_rows if r.category == "Payroll")
    assert payroll_row.period_total == D("-6300000.00")


def test_manual_and_aging_classification(tmp_path):
    cfg = load_config()
    f = compute_cash_flow(_repo(tmp_path, cfg), cfg, "test")
    manual = [li for li in f.ledger if li.type.startswith("Manual")]
    assert manual and all(li.lag_basis == "MANUAL" for li in manual)
    aging = [li for li in f.ledger if li.type == "Aging AR"]
    assert aging and all(li.week == 1 for li in aging)   # past-dues pulled into week 1


def test_behavioral_lag_uses_party_or_segment(tmp_path):
    cfg = load_config()
    f = compute_cash_flow(_repo(tmp_path, cfg), cfg, "test")
    lag_driven = [li for li in f.ledger if li.lag_basis in ("PARTY", "SEGMENT")]
    assert lag_driven, "expected lag-driven AR/AP events"
    # Domestic Trading lag is 5 days in the demo sample
    dom = [li for li in lag_driven if li.segment == "Domestic Trading"]
    assert dom and all(li.lag_days == D("5.0") for li in dom)


def test_actuals_and_variance(tmp_path):
    """Variance = actual − forecast for closed weeks; None beyond; cumulative to date."""
    cfg = load_config()
    f = compute_cash_flow(_repo(tmp_path, cfg), cfg, "test")
    closed = [p for p in f.positions if p.variance_closing is not None]
    assert len(closed) == f.actuals_through_week == 3
    for p in closed:
        assert p.actual_closing is not None
        assert p.variance_closing == p.actual_closing - p.closing
    # weeks past the closed window carry no actuals
    assert all(p.actual_closing is None for p in f.positions[f.actuals_through_week:])
    assert f.variance_to_date == closed[-1].variance_closing


def test_whatif_cash_floor_override_flags_more_weeks(tmp_path):
    """Raising the floor turns previously-fine weeks into breaches."""
    cfg = load_config()
    repo = _repo(tmp_path, cfg)
    base = compute_cash_flow(repo, cfg, "test")
    assert base.kpis.weeks_below_floor == 0
    raised = cfg.model_copy(update={"cash_flow": cfg.cash_flow.model_copy(update={"cash_floor": D("2000000")})})
    bumped = compute_cash_flow(repo, raised, "test")
    assert bumped.kpis.weeks_below_floor == 1   # only week 1 ($1.56M) dips under $2.0M


def test_whatif_global_lag_shift_delays_cash(tmp_path):
    """A positive lag shift delays receipts, lowering the near-term trough."""
    cfg = load_config()
    repo = _repo(tmp_path, cfg)
    base = compute_cash_flow(repo, cfg, "test")
    slower = cfg.model_copy(
        update={"cash_flow": cfg.cash_flow.model_copy(update={"global_lag_shift_days": D("10")})}
    )
    shifted = compute_cash_flow(repo, slower, "test")
    assert shifted.kpis.min_closing < base.kpis.min_closing
