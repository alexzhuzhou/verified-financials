"""The borrowing base waterfall must land on the exact calibrated figures."""

from __future__ import annotations

from decimal import Decimal

from verified_financials.engines.borrowing_base import compute_borrowing_base

D = Decimal


def _cert(repo, config):
    return compute_borrowing_base(repo, config, "test")


def test_ar_waterfall(repo, config):
    ar = _cert(repo, config).accounts_receivable
    assert ar.gross == D("30000000.00")
    by_rule = {line.rule_id: line.amount for line in ar.ineligibles}
    assert by_rule["ar_aged_90_plus"] == D("1800000.00")
    assert by_rule["ar_foreign_uninsured"] == D("2000000.00")
    assert by_rule["ar_intercompany"] == D("1200000.00")
    assert ar.eligible == D("22150000.00")
    assert ar.availability == D("18827500.00")


def test_concentration_excess_only(repo, config):
    ar = _cert(repo, config).accounts_receivable
    assert len(ar.concentration) == 1
    cl = ar.concentration[0]
    assert cl.customer == "Lone Star Grocery Group"
    assert cl.cap_amount == D("3750000.00")
    assert cl.excess_excluded == D("2850000.00")  # 6.6M - 15% * 25.0M base
    assert cl.pct_of_gross == D("0.2200")


def test_foreign_insured_stays_eligible(repo, config):
    """Manila is foreign but credit-insured -> must NOT be excluded."""
    ar = _cert(repo, config).accounts_receivable
    excluded_entities = {
        c.entity for line in ar.ineligibles for c in line.detail
    }
    assert "Manila Foods Dist." not in excluded_entities


def test_no_double_counting(repo, config):
    """Total A/R excluded == gross - eligible, and no obligor is excluded twice over."""
    ar = _cert(repo, config).accounts_receivable
    categorical = sum((line.amount for line in ar.ineligibles), D("0"))
    concentration = sum((c.excess_excluded for c in ar.concentration), D("0"))
    assert categorical + concentration == ar.gross - ar.eligible


def test_inventory_and_rollup(repo, config):
    cert = _cert(repo, config)
    inv = cert.inventory
    assert inv.gross == D("20000000.00")
    assert inv.ineligibles[0].amount == D("3000000.00")
    assert inv.eligible == D("17000000.00")
    assert inv.availability == D("8500000.00")

    assert cert.gross_availability == D("27327500.00")
    assert cert.borrowing_base == D("27327500.00")
    assert cert.binding_constraint == "borrowing_base"
    assert cert.excess_availability == D("5327500.00")


def test_gross_concentration_basis(repo, config):
    """Flipping the cap basis to 'gross' changes only the concentration math."""
    cfg = config.model_copy(deep=True)
    cap = cfg.borrowing_base.accounts_receivable.concentration_cap.model_copy(
        update={"basis": "gross"}
    )
    ar_cfg = cfg.borrowing_base.accounts_receivable.model_copy(update={"concentration_cap": cap})
    bb = cfg.borrowing_base.model_copy(update={"accounts_receivable": ar_cfg})
    cfg = cfg.model_copy(update={"borrowing_base": bb})

    ar = compute_borrowing_base(repo, cfg, "test").accounts_receivable
    assert ar.concentration[0].cap_amount == D("4500000.00")  # 15% * 30.0M gross
    assert ar.eligible == D("22900000.00")
    assert ar.availability == D("19465000.00")
