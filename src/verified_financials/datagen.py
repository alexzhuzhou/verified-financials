"""Synthetic dataset generator for a McLane-like food distributor.

Reproducible (seeded) and calibrated so the planted problems land on exact
target numbers. Every total is asserted before the CSVs are written, so a
miscalibration fails loudly rather than silently breaking the demo.

Planted problems (see the build plan):
  1. balance_sheet A/R (30.2M) != sum of ar_aging detail (30.0M)        -> $200K gap
  2. balance_sheet inventory (20.0M) != trial_balance inventory (20.5M) -> $500K gap
  3. revenue 2025 differs across files (182.4M vs 181.1M)               -> version conflict
  4. Lone Star Grocery Group is 22% of gross A/R (over 15% cap)         -> concentration excess
  5. Gulf Provisions LLC (UAE, uninsured) 2.0M                          -> foreign-uninsured ineligible
  6. 1.8M of receivables aged 90+ days (scattered)                      -> aged ineligible
  7. McLane Logistics International 1.2M                                -> intercompany ineligible
  8. 3.0M obsolete / slow-moving inventory                              -> inventory ineligible
"""

from __future__ import annotations

import csv
import random
from decimal import Decimal
from pathlib import Path

from .config.loader import load_config

# Five operating segments of the distributor.
SEG_FOODSERVICE = "Foodservice Distribution"
SEG_CONVENIENCE = "Convenience / C-Store"
SEG_GROCERY = "Grocery Wholesale"
SEG_COLDCHAIN = "Cold Chain / Frozen"
SEG_LOGISTICS = "Logistics & Freight"

D = Decimal
CENT = Decimal("0.01")


def _d(x) -> Decimal:
    return Decimal(str(x))


# --------------------------------------------------------------------------- #
# A/R aging
# --------------------------------------------------------------------------- #
# Special, named customers that each trigger a specific eligibility rule.
# (customer, segment, country, credit_insured, affiliate, total_millions)
_SPECIAL_CUSTOMERS = [
    ("Lone Star Grocery Group", SEG_GROCERY, "US", True, False, "6.6"),       # concentration
    ("Gulf Provisions LLC - UAE", SEG_FOODSERVICE, "AE", False, False, "2.0"),  # foreign uninsured
    ("Manila Foods Dist.", SEG_FOODSERVICE, "PH", True, False, "1.5"),        # foreign INSURED (stays eligible)
    ("McLane Logistics International", SEG_LOGISTICS, "US", True, True, "1.2"),  # intercompany
]

# Ordinary domestic customers (US, insured, non-affiliate). Totals sum to 18.7M.
# (customer, segment, total_millions, ninety_plus_millions)
_FILLER_CUSTOMERS = [
    ("Sysco Regional Kitchens", SEG_FOODSERVICE, "2.4", "0.0"),
    ("US Foods Northeast", SEG_FOODSERVICE, "2.1", "0.0"),
    ("QuickStop C-Stores", SEG_CONVENIENCE, "1.9", "0.4"),
    ("Circle Pantry Markets", SEG_CONVENIENCE, "1.6", "0.0"),
    ("Heartland Grocers Co-op", SEG_GROCERY, "2.2", "0.5"),
    ("Prairie Fresh Markets", SEG_GROCERY, "1.3", "0.0"),
    ("Polar Cold Storage Foods", SEG_COLDCHAIN, "1.7", "0.35"),
    ("Arctic Line Frozen", SEG_COLDCHAIN, "1.1", "0.0"),
    ("Interstate Freight Partners", SEG_LOGISTICS, "1.4", "0.3"),
    ("Gateway Distribution Co", SEG_LOGISTICS, "2.0", "0.0"),
    ("Bayou Foodservice Supply", SEG_FOODSERVICE, "0.7", "0.25"),
    ("Summit Convenience Group", SEG_CONVENIENCE, "0.3", "0.0"),
]

_M = Decimal("1000000")


def _days_past_due(c30, c60, c90, c90p) -> int:
    """Representative days-past-due from the oldest bucket carrying a balance."""
    if c90p > 0:
        return 96 + int(c90p) % 40
    if c90 > 0:
        return 70
    if c60 > 0:
        return 45
    if c30 > 0:
        return 18
    return 0


def build_ar_aging(rng: random.Random) -> list[dict]:
    rows: list[dict] = []

    for name, seg, country, insured, affiliate, total_m in _SPECIAL_CUSTOMERS:
        total = _d(total_m) * _M
        rows.append(
            {
                "customer": name,
                "segment": seg,
                "country": country,
                "credit_insured": insured,
                "affiliate": affiliate,
                "days_past_due": 0,
                "current": total,
                "1_30": D("0"),
                "31_60": D("0"),
                "61_90": D("0"),
                "90_plus": D("0"),
                "total": total,
            }
        )

    for name, seg, total_m, ninety_m in _FILLER_CUSTOMERS:
        total_c = int(_d(total_m) * _M * 100)
        ninety_c = int(_d(ninety_m) * _M * 100)
        remaining = total_c - ninety_c
        # Modest past-due tail; keeps each obligor well under any cross-age threshold.
        f_30 = rng.uniform(0.05, 0.12)
        f_60 = rng.uniform(0.02, 0.06)
        f_90 = rng.uniform(0.00, 0.04)
        c_30 = int(remaining * f_30)
        c_60 = int(remaining * f_60)
        c_90 = int(remaining * f_90)
        c_cur = remaining - c_30 - c_60 - c_90
        assert c_cur >= 0, f"negative current bucket for {name}"

        cur = _d(c_cur) / 100
        b30 = _d(c_30) / 100
        b60 = _d(c_60) / 100
        b90 = _d(c_90) / 100
        b90p = _d(ninety_c) / 100
        total = _d(total_c) / 100
        rows.append(
            {
                "customer": name,
                "segment": seg,
                "country": "US",
                "credit_insured": True,
                "affiliate": False,
                "days_past_due": _days_past_due(b30, b60, b90, b90p),
                "current": cur,
                "1_30": b30,
                "31_60": b60,
                "61_90": b90,
                "90_plus": b90p,
                "total": total,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #
# (item, segment, category, value_millions, days_since_last_movement, obsolete)
_INVENTORY_ITEMS = [
    ("Dry Goods Staples", SEG_FOODSERVICE, "Dry Goods", "3.5", 14, False),
    ("Frozen Proteins", SEG_COLDCHAIN, "Frozen", "3.0", 9, False),
    ("Refrigerated Dairy", SEG_GROCERY, "Refrigerated", "2.5", 6, False),
    ("Canned & Packaged Goods", SEG_FOODSERVICE, "Dry Goods", "2.2", 21, False),
    ("Beverages - CSD & Water", SEG_CONVENIENCE, "Beverages", "1.8", 11, False),
    ("Snacks & Confectionery", SEG_CONVENIENCE, "Snacks", "1.4", 17, False),
    ("Paper & Disposables", SEG_LOGISTICS, "Non-Food", "1.1", 33, False),
    ("Cleaning & Janitorial Supplies", SEG_LOGISTICS, "Non-Food", "0.8", 41, False),
    ("Fresh Produce", SEG_GROCERY, "Produce", "0.7", 4, False),
    # Obsolete / slow-moving (sums to 3.0M)
    ("Discontinued Holiday Gift Packs", SEG_GROCERY, "Seasonal", "0.9", 240, True),
    ("Close-Dated Canned Soups", SEG_FOODSERVICE, "Dry Goods", "0.7", 210, True),
    ("Slow-Moving Specialty Sauces", SEG_FOODSERVICE, "Dry Goods", "0.6", 195, True),
    ("Overstock Seasonal Beverages", SEG_CONVENIENCE, "Beverages", "0.5", 220, True),
    ("Damaged Packaging Materials", SEG_LOGISTICS, "Non-Food", "0.3", 300, True),
]


def build_inventory() -> list[dict]:
    rows = []
    for item, seg, cat, val_m, days, obsolete in _INVENTORY_ITEMS:
        rows.append(
            {
                "item": item,
                "segment": seg,
                "category": cat,
                "value": _d(val_m) * _M,
                "days_since_last_movement": days,
                "obsolete": obsolete,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Trial balance & balance sheet
# --------------------------------------------------------------------------- #
# (account, metric, debit_millions, credit_millions). Inventory deliberately 20.5M.
_TRIAL_BALANCE = [
    ("Cash", "cash", "5.0", "0"),
    ("Accounts Receivable", "accounts_receivable", "30.2", "0"),
    ("Inventory", "inventory", "20.5", "0"),  # planted: BS says 20.0M
    ("Prepaid & Other Current Assets", "prepaid_other_current", "3.0", "0"),
    ("Property, Plant & Equipment (net)", "ppe_net", "45.0", "0"),
    ("Goodwill & Intangibles", "goodwill_intangibles", "12.0", "0"),
    ("Other Assets", "other_assets", "2.8", "0"),
    ("Accounts Payable", "accounts_payable", "0", "28.0"),
    ("Accrued Expenses", "accrued_expenses", "0", "6.0"),
    ("Revolving Credit Facility", "revolver", "0", "22.0"),
    ("Current Portion of Long-Term Debt", "current_ltd", "0", "6.0"),
    ("Long-Term Debt", "long_term_debt", "0", "30.0"),
    ("Other Liabilities", "other_liabilities", "0", "4.0"),
    ("Shareholders' Equity", "equity", "0", "22.5"),  # plug so debits == credits
]

# (line_item, metric, section, amount_millions). A/R 30.2M and inventory 20.0M.
_BALANCE_SHEET = [
    ("Cash", "cash", "asset", "5.0"),
    ("Accounts Receivable", "accounts_receivable", "asset", "30.2"),  # planted vs aging 30.0M
    ("Inventory", "inventory", "asset", "20.0"),  # planted vs TB 20.5M
    ("Prepaid & Other Current Assets", "prepaid_other_current", "asset", "3.0"),
    ("Property, Plant & Equipment (net)", "ppe_net", "asset", "45.0"),
    ("Goodwill & Intangibles", "goodwill_intangibles", "asset", "12.0"),
    ("Other Assets", "other_assets", "asset", "2.8"),
    ("Total Assets", "total_assets", "total", "118.0"),
    ("Accounts Payable", "accounts_payable", "liability", "28.0"),
    ("Accrued Expenses", "accrued_expenses", "liability", "6.0"),
    ("Revolving Credit Facility", "revolver", "liability", "22.0"),
    ("Current Portion of Long-Term Debt", "current_ltd", "liability", "6.0"),
    ("Long-Term Debt", "long_term_debt", "liability", "30.0"),
    ("Other Liabilities", "other_liabilities", "liability", "4.0"),
    ("Total Equity", "total_equity", "equity", "22.0"),
    ("Total Liabilities and Equity", "total_liabilities_equity", "total", "118.0"),
]


def build_trial_balance() -> list[dict]:
    return [
        {
            "account": acct,
            "metric": metric,
            "debit": _d(dr) * _M,
            "credit": _d(cr) * _M,
        }
        for acct, metric, dr, cr in _TRIAL_BALANCE
    ]


def build_balance_sheet() -> list[dict]:
    return [
        {"line_item": li, "metric": metric, "section": section, "amount": _d(amt) * _M}
        for li, metric, section, amt in _BALANCE_SHEET
    ]


# --------------------------------------------------------------------------- #
# Financials (FCCR components + trend) and the re-sent / refreshed version
# --------------------------------------------------------------------------- #
# (metric, value, period)
_FINANCIALS_TTM = [
    ("ebitda", "18000000", "TTM-2025Q4"),
    ("unfinanced_capex", "3000000", "TTM-2025Q4"),
    ("cash_taxes", "2000000", "TTM-2025Q4"),
    ("distributions", "1000000", "TTM-2025Q4"),
    ("cash_interest", "4000000", "TTM-2025Q4"),
    ("scheduled_principal", "6000000", "TTM-2025Q4"),
    ("revenue_2025", "182400000", "FY2025"),
    # Prior-quarter FCCR points for the trend (current quarter is computed by the engine).
    ("fccr_history", "1.35", "Q2-2025"),
    ("fccr_history", "1.28", "Q3-2025"),
]

_FINANCIALS_REFRESHED = [
    ("revenue_2025", "181100000", "FY2025"),  # conflicts with 182.4M above
]


def build_financials_ttm() -> list[dict]:
    return [{"metric": m, "value": _d(v), "period": p} for m, v, p in _FINANCIALS_TTM]


def build_financials_refreshed() -> list[dict]:
    return [{"metric": m, "value": _d(v), "period": p} for m, v, p in _FINANCIALS_REFRESHED]


# --------------------------------------------------------------------------- #
# Stress scenario (advanced) — exercises NOLV, reserves, cross-aging, springing,
# equity cure. Verification-clean (figures reconcile); focus is modeling depth.
# --------------------------------------------------------------------------- #
# (name, segment, country, insured, affiliate, total_m, explicit_buckets|None)
_STRESS_SPECIAL = [
    ("BigBox Wholesale Group", SEG_GROCERY, "US", True, False, "6.0", None),  # concentration
    ("Sunset Diners Group", SEG_FOODSERVICE, "US", True, False, "1.5",        # cross-aged 67%
     {"current": "0.5", "1_30": "0", "31_60": "0.5", "61_90": "0.5", "90_plus": "0"}),
    ("Andes Provisions - Chile", SEG_FOODSERVICE, "CL", False, False, "1.5", None),  # foreign uninsured
    ("McLane Logistics International", SEG_LOGISTICS, "US", True, True, "1.0", None),  # intercompany
    ("Manila Foods Dist.", SEG_FOODSERVICE, "PH", True, False, "1.0", None),  # foreign INSURED (eligible)
]

_STRESS_FILLER = [
    ("Regional Grocers Alliance", SEG_GROCERY, "2.5", "0.3"),
    ("QuickServe Foodservice", SEG_FOODSERVICE, "2.0", "0.2"),
    ("Coastal Convenience", SEG_CONVENIENCE, "1.8", "0.2"),
    ("Mountain Cold Foods", SEG_COLDCHAIN, "1.7", "0.3"),
    ("Valley Fresh Distributors", SEG_GROCERY, "1.5", "0.0"),
    ("Metro Pantry Group", SEG_CONVENIENCE, "1.3", "0.0"),
    ("Harbor Snacks Co", SEG_CONVENIENCE, "1.2", "0.0"),
    ("Prairie Provisions", SEG_FOODSERVICE, "1.0", "0.0"),
    ("Delta Freight Foods", SEG_LOGISTICS, "1.0", "0.0"),
]


def _filler_ar_row(rng, name, seg, total_m, ninety_m, country="US", insured=True, affiliate=False):
    total_c = int(_d(total_m) * _M * 100)
    ninety_c = int(_d(ninety_m) * _M * 100)
    remaining = total_c - ninety_c
    c_30 = int(remaining * rng.uniform(0.05, 0.12))
    c_60 = int(remaining * rng.uniform(0.02, 0.06))
    c_90 = int(remaining * rng.uniform(0.00, 0.04))
    c_cur = remaining - c_30 - c_60 - c_90
    assert c_cur >= 0, f"negative current bucket for {name}"
    cur, b30, b60, b90 = _d(c_cur) / 100, _d(c_30) / 100, _d(c_60) / 100, _d(c_90) / 100
    b90p, total = _d(ninety_c) / 100, _d(total_c) / 100
    return {
        "customer": name, "segment": seg, "country": country,
        "credit_insured": insured, "affiliate": affiliate,
        "days_past_due": _days_past_due(b30, b60, b90, b90p),
        "current": cur, "1_30": b30, "31_60": b60, "61_90": b90, "90_plus": b90p, "total": total,
    }


def build_stress_ar_aging(rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    for name, seg, country, insured, affiliate, total_m, buckets in _STRESS_SPECIAL:
        total = _d(total_m) * _M
        if buckets is None:
            b = {"current": total, "1_30": D("0"), "31_60": D("0"), "61_90": D("0"), "90_plus": D("0")}
        else:
            b = {k: _d(v) * _M for k, v in buckets.items()}
        rows.append({
            "customer": name, "segment": seg, "country": country,
            "credit_insured": insured, "affiliate": affiliate,
            "days_past_due": _days_past_due(b["1_30"], b["31_60"], b["61_90"], b["90_plus"]),
            **b, "total": total,
        })
    for name, seg, total_m, ninety_m in _STRESS_FILLER:
        rows.append(_filler_ar_row(rng, name, seg, total_m, ninety_m))
    return rows


# (item, segment, category, value_m, days_since_last_movement, obsolete)
_STRESS_INVENTORY = [
    ("Dry Goods Staples", SEG_FOODSERVICE, "Dry Goods", "6.0", 16, False),
    ("Frozen Proteins", SEG_COLDCHAIN, "Frozen", "4.0", 10, False),
    ("Refrigerated Dairy", SEG_GROCERY, "Refrigerated", "3.0", 7, False),
    ("Beverages - CSD & Water", SEG_CONVENIENCE, "Beverages", "2.0", 12, False),
    ("Fresh Produce", SEG_GROCERY, "Produce", "1.0", 5, False),
    ("Paper & Disposables", SEG_LOGISTICS, "Non-Food", "1.0", 35, False),
    ("Discontinued Holiday Packs", SEG_GROCERY, "Dry Goods", "1.0", 250, True),  # obsolete
]


def build_stress_inventory() -> list[dict]:
    return [
        {"item": i, "segment": s, "category": c, "value": _d(v) * _M,
         "days_since_last_movement": d, "obsolete": o}
        for i, s, c, v, d, o in _STRESS_INVENTORY
    ]


_STRESS_TRIAL_BALANCE = [
    ("Cash", "cash", "3.0", "0"),
    ("Accounts Receivable", "accounts_receivable", "25.0", "0"),
    ("Inventory", "inventory", "18.0", "0"),
    ("Prepaid & Other Current Assets", "prepaid_other_current", "2.0", "0"),
    ("Property, Plant & Equipment (net)", "ppe_net", "40.0", "0"),
    ("Goodwill & Intangibles", "goodwill_intangibles", "10.0", "0"),
    ("Other Assets", "other_assets", "2.0", "0"),
    ("Accounts Payable", "accounts_payable", "0", "24.0"),
    ("Accrued Expenses", "accrued_expenses", "0", "5.0"),
    ("Revolving Credit Facility", "revolver", "0", "18.0"),
    ("Current Portion of Long-Term Debt", "current_ltd", "0", "4.0"),
    ("Long-Term Debt", "long_term_debt", "0", "25.0"),
    ("Other Liabilities", "other_liabilities", "0", "4.0"),
    ("Shareholders' Equity", "equity", "0", "20.0"),
]

_STRESS_BALANCE_SHEET = [
    ("Cash", "cash", "asset", "3.0"),
    ("Accounts Receivable", "accounts_receivable", "asset", "25.0"),
    ("Inventory", "inventory", "asset", "18.0"),
    ("Prepaid & Other Current Assets", "prepaid_other_current", "asset", "2.0"),
    ("Property, Plant & Equipment (net)", "ppe_net", "asset", "40.0"),
    ("Goodwill & Intangibles", "goodwill_intangibles", "asset", "10.0"),
    ("Other Assets", "other_assets", "asset", "2.0"),
    ("Total Assets", "total_assets", "total", "100.0"),
    ("Accounts Payable", "accounts_payable", "liability", "24.0"),
    ("Accrued Expenses", "accrued_expenses", "liability", "5.0"),
    ("Revolving Credit Facility", "revolver", "liability", "18.0"),
    ("Current Portion of Long-Term Debt", "current_ltd", "liability", "4.0"),
    ("Long-Term Debt", "long_term_debt", "liability", "25.0"),
    ("Other Liabilities", "other_liabilities", "liability", "4.0"),
    ("Total Equity", "total_equity", "equity", "20.0"),
    ("Total Liabilities and Equity", "total_liabilities_equity", "total", "100.0"),
]

_STRESS_FINANCIALS_TTM = [
    ("ebitda", "14000000", "TTM-2025Q4"),
    ("unfinanced_capex", "3000000", "TTM-2025Q4"),
    ("cash_taxes", "2000000", "TTM-2025Q4"),
    ("distributions", "1000000", "TTM-2025Q4"),
    ("cash_interest", "5000000", "TTM-2025Q4"),
    ("scheduled_principal", "4000000", "TTM-2025Q4"),
    ("revenue_2025", "150000000", "FY2025"),
    ("fccr_history", "1.15", "Q2-2025"),
    ("fccr_history", "1.02", "Q3-2025"),
]

_STRESS_FINANCIALS_REFRESHED = [
    ("revenue_2025", "150000000", "FY2025"),  # agrees -> verification passes
]


def build_stress_trial_balance() -> list[dict]:
    return [{"account": a, "metric": m, "debit": _d(dr) * _M, "credit": _d(cr) * _M}
            for a, m, dr, cr in _STRESS_TRIAL_BALANCE]


def build_stress_balance_sheet() -> list[dict]:
    return [{"line_item": li, "metric": m, "section": s, "amount": _d(amt) * _M}
            for li, m, s, amt in _STRESS_BALANCE_SHEET]


def build_stress_financials_ttm() -> list[dict]:
    return [{"metric": m, "value": _d(v), "period": p} for m, v, p in _STRESS_FINANCIALS_TTM]


def build_stress_financials_refreshed() -> list[dict]:
    return [{"metric": m, "value": _d(v), "period": p} for m, v, p in _STRESS_FINANCIALS_REFRESHED]


def _assert_calibration_stress(ar, inv, tb, bs) -> None:
    ar_total = sum((r["total"] for r in ar), D("0"))
    assert ar_total == D("25000000"), f"stress A/R total {ar_total} != 25.0M"
    assert sum((r["90_plus"] for r in ar), D("0")) == D("1000000"), "stress 90+ != 1.0M"
    for r in ar:
        s = r["current"] + r["1_30"] + r["31_60"] + r["61_90"] + r["90_plus"]
        assert s == r["total"], f"buckets for {r['customer']} sum {s} != {r['total']}"
    # categorical incl cross-aging, disjoint -> base 20.0M
    base = D("0")
    for r in ar:
        total = r["total"]
        ineligible = r["90_plus"]
        if r["country"] != "US" and not r["credit_insured"]:
            ineligible = total
        if r["affiliate"]:
            ineligible = total
        past_due = total - r["current"]
        if total > 0 and past_due / total > D("0.50"):
            ineligible = total
        base += total - min(ineligible, total)
    assert base == D("20000000"), f"stress pre-concentration base {base} != 20.0M"

    assert sum((r["value"] for r in inv), D("0")) == D("18000000"), "stress inventory != 18.0M"
    assert sum((r["value"] for r in inv if r["obsolete"]), D("0")) == D("1000000"), "stress obsolete != 1.0M"

    assert sum((r["debit"] for r in tb), D("0")) == sum((r["credit"] for r in tb), D("0")), "stress TB unbalanced"
    assert next(r["debit"] for r in tb if r["metric"] == "inventory") == D("18000000")
    assert next(r["amount"] for r in bs if r["metric"] == "inventory") == D("18000000")
    assert next(r["amount"] for r in bs if r["metric"] == "accounts_receivable") == D("25000000")
    ta = next(r["amount"] for r in bs if r["metric"] == "total_assets")
    tle = next(r["amount"] for r in bs if r["metric"] == "total_liabilities_equity")
    assert ta == tle, f"stress BS does not balance: {ta} != {tle}"


# --------------------------------------------------------------------------- #
# Calibration assertions
# --------------------------------------------------------------------------- #
def _assert_calibration(ar, inv, tb, bs) -> None:
    ar_total = sum((r["total"] for r in ar), D("0"))
    assert ar_total == D("30000000"), f"A/R total {ar_total} != 30.0M"

    ninety = sum((r["90_plus"] for r in ar), D("0"))
    assert ninety == D("1800000"), f"90+ total {ninety} != 1.8M"

    # bucket integrity per row
    for r in ar:
        s = r["current"] + r["1_30"] + r["31_60"] + r["61_90"] + r["90_plus"]
        assert s == r["total"], f"buckets for {r['customer']} sum {s} != total {r['total']}"

    # the categorical exclusions must sit on disjoint customers -> base == 25.0M
    base = D("0")
    for r in ar:
        ineligible = r["90_plus"]
        if r["country"] != "US" and not r["credit_insured"]:
            ineligible = r["total"]
        if r["affiliate"]:
            ineligible = r["total"]
        base += r["total"] - min(ineligible, r["total"])
    assert base == D("25000000"), f"pre-concentration base {base} != 25.0M"

    inv_total = sum((r["value"] for r in inv), D("0"))
    assert inv_total == D("20000000"), f"inventory total {inv_total} != 20.0M"
    obsolete = sum((r["value"] for r in inv if r["obsolete"]), D("0"))
    assert obsolete == D("3000000"), f"obsolete {obsolete} != 3.0M"

    tb_dr = sum((r["debit"] for r in tb), D("0"))
    tb_cr = sum((r["credit"] for r in tb), D("0"))
    assert tb_dr == tb_cr, f"trial balance debits {tb_dr} != credits {tb_cr}"
    tb_inv = next(r["debit"] for r in tb if r["metric"] == "inventory")
    assert tb_inv == D("20500000"), f"TB inventory {tb_inv} != 20.5M"

    bs_ar = next(r["amount"] for r in bs if r["metric"] == "accounts_receivable")
    bs_inv = next(r["amount"] for r in bs if r["metric"] == "inventory")
    assert bs_ar == D("30200000"), f"BS A/R {bs_ar} != 30.2M"
    assert bs_inv == D("20000000"), f"BS inventory {bs_inv} != 20.0M"
    ta = next(r["amount"] for r in bs if r["metric"] == "total_assets")
    tle = next(r["amount"] for r in bs if r["metric"] == "total_liabilities_equity")
    assert ta == tle, f"BS does not balance: assets {ta} != liab+equity {tle}"


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row[k]) for k in fieldnames})


def _fmt(v):
    if isinstance(v, Decimal):
        # normalize to a clean string: integers without trailing .0, else 2dp
        if v == v.to_integral_value():
            return str(int(v))
        return str(v.quantize(CENT))
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def generate(
    data_dir: str | Path | None = None,
    seed: int | None = None,
    scenario: str = "baseline",
) -> dict[str, Path]:
    """Generate all six CSVs for a scenario, assert calibration, return paths."""
    config = load_config("config_advanced.yaml") if scenario == "stress" else load_config()
    out_dir = Path(data_dir) if data_dir is not None else Path(config.settings.data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed if seed is not None else config.settings.random_seed)

    if scenario == "stress":
        ar = build_stress_ar_aging(rng)
        inv = build_stress_inventory()
        tb = build_stress_trial_balance()
        bs = build_stress_balance_sheet()
        ttm = build_stress_financials_ttm()
        refreshed = build_stress_financials_refreshed()
        _assert_calibration_stress(ar, inv, tb, bs)
    else:
        ar = build_ar_aging(rng)
        inv = build_inventory()
        tb = build_trial_balance()
        bs = build_balance_sheet()
        ttm = build_financials_ttm()
        refreshed = build_financials_refreshed()
        _assert_calibration(ar, inv, tb, bs)

    paths = {
        "ar_aging": out_dir / "ar_aging.csv",
        "inventory": out_dir / "inventory.csv",
        "trial_balance": out_dir / "trial_balance.csv",
        "balance_sheet": out_dir / "balance_sheet.csv",
        "financials_ttm": out_dir / "financials_ttm.csv",
        "financials_2025_refreshed": out_dir / "financials_2025_refreshed.csv",
    }

    _write_csv(
        paths["ar_aging"],
        ["customer", "segment", "country", "credit_insured", "affiliate",
         "days_past_due", "current", "1_30", "31_60", "61_90", "90_plus", "total"],
        ar,
    )
    _write_csv(
        paths["inventory"],
        ["item", "segment", "category", "value", "days_since_last_movement", "obsolete"],
        inv,
    )
    _write_csv(paths["trial_balance"], ["account", "metric", "debit", "credit"], tb)
    _write_csv(paths["balance_sheet"], ["line_item", "metric", "section", "amount"], bs)
    _write_csv(paths["financials_ttm"], ["metric", "value", "period"], ttm)
    _write_csv(paths["financials_2025_refreshed"], ["metric", "value", "period"], refreshed)

    return paths


if __name__ == "__main__":
    written = generate()
    for name, path in written.items():
        print(f"wrote {name:28} -> {path}")
