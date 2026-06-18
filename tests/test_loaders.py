"""Loaders must produce traceable facts that round-trip through the store."""

from __future__ import annotations

from decimal import Decimal

D = Decimal


def test_fact_count_and_provenance(repo):
    assert repo.count() == 70
    ar = repo.query(dataset="ar_aging", metric="total")
    assert sum(f.value for f in ar) == D("30000000")
    gulf = next(f for f in ar if "Gulf" in f.entity)
    assert gulf.provenance.source_file == "ar_aging.csv"
    assert gulf.provenance.source_locator.startswith("row ")
    assert gulf.attributes["country"] == "AE"
    assert gulf.attributes["credit_insured"] is False


def test_version_tags_coexist(repo):
    """Original and refreshed revenue must both survive as distinct facts."""
    original = repo.get_fact("financials_ttm", "revenue_2025")
    refreshed = repo.get_fact("financials_refreshed", "revenue_2025")
    assert original.value == D("182400000")
    assert refreshed.value == D("181100000")
    assert original.provenance.version_tag == "original"
    assert refreshed.provenance.version_tag == "refreshed_2025-12-15"


def test_trial_balance_sides(repo):
    facts = repo.query(dataset="trial_balance")
    debits = sum(D(f.attributes["debit"]) for f in facts)
    credits = sum(D(f.attributes["credit"]) for f in facts)
    assert debits == credits == D("118500000")
    assert repo.get_fact("trial_balance", "inventory").value == D("20500000")
