"""The synthetic data must hit every calibration number exactly."""

from __future__ import annotations

import csv
from decimal import Decimal

D = Decimal


def _read(data_dir, name):
    with (data_dir / name).open() as fh:
        return list(csv.DictReader(fh))


def test_ar_aging_totals(data_dir):
    rows = _read(data_dir, "ar_aging.csv")
    assert sum(D(r["total"]) for r in rows) == D("30000000")
    assert sum(D(r["90_plus"]) for r in rows) == D("1800000")
    for r in rows:  # buckets sum to total per row
        s = sum(D(r[b]) for b in ("current", "1_30", "31_60", "61_90", "90_plus"))
        assert s == D(r["total"]), r["customer"]


def test_ar_special_customers(data_dir):
    rows = {r["customer"]: r for r in _read(data_dir, "ar_aging.csv")}
    lone = rows["Lone Star Grocery Group"]
    assert D(lone["total"]) == D("6600000") and lone["country"] == "US" and lone["affiliate"] == "false"
    gulf = rows["Gulf Provisions LLC - UAE"]
    assert D(gulf["total"]) == D("2000000") and gulf["country"] == "AE" and gulf["credit_insured"] == "false"
    manila = rows["Manila Foods Dist."]
    assert manila["country"] == "PH" and manila["credit_insured"] == "true"  # foreign INSURED
    mclane = rows["McLane Logistics International"]
    assert D(mclane["total"]) == D("1200000") and mclane["affiliate"] == "true"


def test_disjoint_ineligibles(data_dir):
    """The categorical exclusions must sit on disjoint customers -> base 25.0M."""
    rows = _read(data_dir, "ar_aging.csv")
    base = D("0")
    for r in rows:
        total = D(r["total"])
        ineligible = D(r["90_plus"])
        if r["country"] != "US" and r["credit_insured"] == "false":
            ineligible = total
        if r["affiliate"] == "true":
            ineligible = total
        base += total - min(ineligible, total)
    assert base == D("25000000")


def test_inventory_totals(data_dir):
    rows = _read(data_dir, "inventory.csv")
    assert sum(D(r["value"]) for r in rows) == D("20000000")
    assert sum(D(r["value"]) for r in rows if r["obsolete"] == "true") == D("3000000")


def test_trial_balance_and_bs(data_dir):
    tb = _read(data_dir, "trial_balance.csv")
    assert sum(D(r["debit"]) for r in tb) == sum(D(r["credit"]) for r in tb)
    assert next(D(r["debit"]) for r in tb if r["metric"] == "inventory") == D("20500000")

    bs = {r["metric"]: D(r["amount"]) for r in _read(data_dir, "balance_sheet.csv")}
    assert bs["accounts_receivable"] == D("30200000")
    assert bs["inventory"] == D("20000000")
    assert bs["total_assets"] == bs["total_liabilities_equity"]


def test_revenue_version_conflict(data_dir):
    ttm = {r["metric"]: D(r["value"]) for r in _read(data_dir, "financials_ttm.csv") if r["metric"] != "fccr_history"}
    refreshed = {r["metric"]: D(r["value"]) for r in _read(data_dir, "financials_2025_refreshed.csv")}
    assert ttm["revenue_2025"] == D("182400000")
    assert refreshed["revenue_2025"] == D("181100000")
    assert ttm["revenue_2025"] - refreshed["revenue_2025"] == D("1300000")


def test_reproducible(tmp_path, config):
    from verified_financials import datagen

    a = tmp_path / "a"
    b = tmp_path / "b"
    datagen.generate(data_dir=a, seed=config.settings.random_seed)
    datagen.generate(data_dir=b, seed=config.settings.random_seed)
    assert (a / "ar_aging.csv").read_text() == (b / "ar_aging.csv").read_text()
