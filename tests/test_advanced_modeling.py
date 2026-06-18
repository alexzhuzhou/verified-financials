"""Phase 2 deeper-modeling features, exercised by the stress scenario."""

from __future__ import annotations

from decimal import Decimal

from verified_financials.engines.borrowing_base import compute_borrowing_base
from verified_financials.engines.fccr import compute_fccr
from verified_financials.engines.verification import run_verification
from verified_financials.pipeline import compute_with_overrides

D = Decimal


def _cert(stress_repo, stress_config):
    return compute_borrowing_base(stress_repo, stress_config, "test")


def test_nolv_inventory(stress_repo, stress_config):
    inv = _cert(stress_repo, stress_config).inventory
    assert inv.valuation_basis == "nolv"
    assert inv.gross == D("18000000.00")
    assert inv.eligible == D("17000000.00")          # at cost, after obsolete
    assert inv.eligible_nolv_value == D("10000000.00")  # NOLV haircut
    assert inv.availability == D("8000000.00")        # 80% of NOLV
    cats = {n.category: n.nolv_value for n in inv.nolv_detail}
    assert cats["Produce"] == D("400000.00")          # 1.0M cost x 40% NOLV


def test_reserves(stress_repo, stress_config):
    cert = _cert(stress_repo, stress_config)
    by_type = {r["type"]: D(r["amount"]) for r in cert.reserve_detail}
    assert by_type["dilution"] == D("850000.00")      # (10%-5%) x 17.0M eligible A/R
    assert by_type["priority_payable"] == D("600000.00")
    assert by_type["rent"] == D("400000.00")
    assert cert.reserves_total == D("1850000.00")


def test_cross_aging_taint(stress_repo, stress_config):
    ar = _cert(stress_repo, stress_config).accounts_receivable
    cross = next(line for line in ar.ineligibles if line.rule_id == "ar_cross_aging")
    assert cross.amount == D("1500000.00")            # Sunset's whole balance
    assert [c.entity for c in cross.detail] == ["Sunset Diners Group"]
    assert ar.eligible == D("17000000.00")


def test_stress_rollup(stress_repo, stress_config):
    cert = _cert(stress_repo, stress_config)
    assert cert.gross_availability == D("21600000.00")
    assert cert.borrowing_base == D("19750000.00")
    assert cert.excess_availability == D("1750000.00")


def test_springing_covenant_active(stress_repo, stress_config):
    cert = _cert(stress_repo, stress_config)
    r = compute_fccr(stress_repo, stress_config, "test", excess_availability=cert.excess_availability)
    assert r.springing_enabled is True
    assert r.springing_trigger == D("3750000.00")     # max(12.5% x 30M, 3.0M floor)
    assert r.covenant_active is True                  # excess 1.75M < trigger 3.75M
    assert r.excess_availability == D("1750000.00")


def test_equity_cure(stress_repo, stress_config):
    cert = _cert(stress_repo, stress_config)
    r = compute_fccr(stress_repo, stress_config, "test", excess_availability=cert.excess_availability)
    assert r.fccr == D("0.89")
    assert r.in_compliance is False
    assert r.equity_cure_needed == D("1900000.00")    # 1.10 x 9.0M - 8.0M
    assert r.cures_remaining_year == 2
    assert r.cures_remaining_lifetime == 5


def test_stress_verification_clean(stress_repo, stress_config):
    report = run_verification(stress_repo, stress_config, "test")
    assert report.failed == 0 and report.passed == 5


def test_compute_with_overrides(config, data_dir):
    """The what-if path: bump the A/R advance rate and watch availability move."""
    base = compute_with_overrides({}, base_config=config, data_dir=data_dir)
    bumped = compute_with_overrides(
        {"borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}},
        base_config=config,
        data_dir=data_dir,
    )
    assert base.certificate.accounts_receivable.availability == D("18827500.00")
    assert bumped.certificate.accounts_receivable.availability == D("19935000.00")  # 22.15M x 90%
