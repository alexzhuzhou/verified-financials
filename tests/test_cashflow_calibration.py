"""The 13-week cash-flow forecast must hit its calibrated demo numbers.

Baseline stays above the floor (0 weeks below); stress breaches it in the near
term then recovers. The engine (which times every event) must reproduce the
no-lag design projection exactly, because the demo lags are exact integers.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from verified_financials import datagen
from verified_financials.config.loader import load_config
from verified_financials.engines.cash_flow import compute_cash_flow
from verified_financials.loaders import cash_events, paid_history
from verified_financials.store.db import connect, init_schema
from verified_financials.store.repository import FactRepository

D = Decimal


def _forecast(tmp_path, cfg, scenario):
    datagen.generate(data_dir=tmp_path, seed=cfg.settings.random_seed, scenario=scenario)
    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    loaded = datetime.now()
    as_of = cfg.facility.as_of_date
    repo.add_many(cash_events.load(tmp_path / "cash_events.csv", as_of, loaded))
    repo.add_many(paid_history.load(tmp_path / "paid_history.csv", as_of, loaded))
    return compute_cash_flow(repo, cfg, "test"), cfg


def test_baseline_calibration(tmp_path):
    f, cfg = _forecast(tmp_path, load_config(), "baseline")
    assert f.kpis.weeks_below_floor == 0
    assert f.kpis.min_closing == D("1560000.00")
    assert f.kpis.min_closing_week == 1
    assert f.kpis.total_receipts == D("35900000.00")
    assert f.kpis.total_disbursements == D("-30660000.00")   # incl. a $500k revolver paydown
    assert f.kpis.net_cash_flow == D("5240000.00")
    assert f.kpis.exception_count == 5
    # engine reproduces the no-lag design projection exactly
    proj = datagen.cash_flow_projection(cfg, "baseline")
    assert [p.closing for p in f.positions] == proj["closings"]


def test_stress_calibration(tmp_path):
    f, cfg = _forecast(tmp_path, load_config("config_advanced.yaml"), "stress")
    assert f.kpis.weeks_below_floor == 4
    assert f.kpis.min_closing == D("-370000.00")
    assert f.kpis.min_closing_week == 3
    assert f.kpis.exception_count == 8
    # the contractual (optimistic) edge breaches less than the behavioral edge
    assert f.kpis_contractual.weeks_below_floor < f.kpis.weeks_below_floor
    proj = datagen.cash_flow_projection(cfg, "stress")
    assert [p.closing for p in f.positions] == proj["closings"]


@pytest.mark.parametrize("scenario,cfgfile", [("baseline", None), ("stress", "config_advanced.yaml")])
def test_horizon_and_segment_lags(tmp_path, scenario, cfgfile):
    cfg = load_config(cfgfile) if cfgfile else load_config()
    f, _ = _forecast(tmp_path, cfg, scenario)
    assert f.horizon_weeks == 13
    assert len(f.positions) == 13
    lags = {s.segment: s.avg_lag_days for s in f.segment_lags}
    assert lags["Domestic Trading"] == D("5.00")
    assert lags["International Trading"] == D("7.00")
    assert lags["3PL"] == D("10.00")
