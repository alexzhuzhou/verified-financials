"""Verification must catch the three planted problems and pass the integrity checks."""

from __future__ import annotations

from decimal import Decimal

from verified_financials.engines.verification import run_verification

D = Decimal


def _by_id(repo, config):
    report = run_verification(repo, config, "test")
    return {f.check_id: f for f in report.findings}, report


def test_planted_exceptions(repo, config):
    findings, report = _by_id(repo, config)
    assert report.failed == 3 and report.passed == 2

    assert findings["ar_bs_vs_aging"].status == "fail"
    assert findings["ar_bs_vs_aging"].delta == D("200000")

    assert findings["inv_bs_vs_tb"].status == "fail"
    assert findings["inv_bs_vs_tb"].delta == D("-500000")

    rev = findings["revenue_version_conflict"]
    assert rev.status == "fail"
    assert rev.delta == D("1300000")
    assert rev.left.version_tag == "original"
    assert rev.right.version_tag == "refreshed_2025-12-15"


def test_integrity_checks_pass(repo, config):
    findings, _ = _by_id(repo, config)
    assert findings["tb_balances"].status == "pass"
    assert findings["bs_balances"].status == "pass"


def test_findings_carry_provenance(repo, config):
    findings, _ = _by_id(repo, config)
    f = findings["ar_bs_vs_aging"]
    assert f.left.source_file == "balance_sheet.csv"
    assert "sum of" in f.right.source_locator
