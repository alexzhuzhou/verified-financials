"""FCCR must resolve to 1.20x, in compliance, with the early warning firing."""

from __future__ import annotations

from decimal import Decimal

from verified_financials.engines.fccr import compute_fccr

D = Decimal


def test_fccr_computation(repo, config):
    r = compute_fccr(repo, config, "test")
    assert r.numerator == D("12000000.00")
    assert r.denominator == D("10000000.00")
    assert r.fccr == D("1.20")
    assert r.covenant == D("1.10")
    assert r.in_compliance is True


def test_headroom_and_cushion(repo, config):
    r = compute_fccr(repo, config, "test")
    assert r.headroom_abs == D("0.10")
    assert r.headroom_pct == D("0.0909")
    assert r.ebitda_cushion == D("1000000.00")


def test_trend_and_early_warning(repo, config):
    r = compute_fccr(repo, config, "test")
    assert [(p.quarter, p.fccr) for p in r.trend] == [
        ("Q2-2025", D("1.35")),
        ("Q3-2025", D("1.28")),
        ("Q4-2025", D("1.20")),
    ]
    assert r.consecutive_declines == 2
    assert r.early_warning is True
    assert len(r.warning_reasons) == 2


def test_no_double_count_taxes(repo, config):
    """Taxes & distributions appear only in the numerator (Convention A)."""
    r = compute_fccr(repo, config, "test")
    placements = {(c.name, c.side) for c in r.components}
    assert ("cash_taxes", "numerator") in placements
    assert ("distributions", "numerator") in placements
    assert ("cash_taxes", "denominator") not in placements
    assert ("distributions", "denominator") not in placements
