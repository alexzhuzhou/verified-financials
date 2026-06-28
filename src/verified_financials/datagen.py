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
from datetime import date, timedelta
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
# Cash-flow ledger (13-week direct forecast)
# --------------------------------------------------------------------------- #
# The cash model uses McLane-style operating segments (distinct from the five
# borrowing-base segments above). Each segment has an observed average payment
# lag (days late) that the timing engine applies to size the behavioral edge.
CF_SEGMENTS = ["Domestic Trading", "International Trading", "3PL", "Warehouse", "MHS", "Transportation"]
SEGMENT_LAG = {
    "Domestic Trading": 5, "International Trading": 7, "3PL": 10,
    "Warehouse": 6, "MHS": 4, "Transportation": 4,
}
CF_INFLOW_WEIGHTS = {
    "Domestic Trading": "0.34", "International Trading": "0.20", "3PL": "0.14",
    "Warehouse": "0.12", "MHS": "0.12", "Transportation": "0.08",
}
CF_AP_WEIGHTS = {
    "Domestic Trading": "0.50", "International Trading": "0.25", "MHS": "0.13", "Transportation": "0.12",
}
CF_TERMS = {
    "Domestic Trading": "Net 30", "International Trading": "Net 45", "3PL": "Net 30",
    "Warehouse": "Net 30", "MHS": "Net 20", "Transportation": "Net 15",
}
CF_CUSTOMERS = {
    "Domestic Trading": ["Sysco Regional Kitchens", "US Foods Northeast", "Gateway Distribution Co"],
    "International Trading": ["Pacific Rim Importers", "Andes Provisions SA", "Gulf Maritime Supply"],
    "3PL": ["Reynolds 3PL Logistics", "Coastal Fulfillment Partners"],
    "Warehouse": ["Heartland Warehouse Co", "Prairie Storage LLC"],
    "MHS": ["Three Square Food Bank", "Community Hunger Relief"],
    "Transportation": ["Interstate Freight Partners", "Delta Freight Foods"],
}
CF_VENDORS = {
    "Domestic Trading": ["Reynolds Consumer Products", "Del Monte Foods"],
    "International Trading": ["Pacific Trading Co", "Global Provisions Ltd"],
    "MHS": ["FoodSource Wholesale"],
    "Transportation": ["FleetFuel Services"],
}
REASON_ACTION = {
    "Credit Memo": "Review",
    "Dispute": "Escalate to controller",
    "Over 90 Days": "Move to collections / write-down review",
    "Unlinked Deposit": "Apply to AR or refund",
    "Unlinked Prepay": "Match to AP or recover",
}

# Per-scenario weekly receipts (R) and accounts-payable (AP) in $thousands, plus
# the fixed-cost schedule (type, [weeks], $thousands). Calibrated so baseline
# stays above the floor while stress breaches it in the near term then recovers.
_CF_PLAN = {
    "baseline": {
        "R":  [2200, 2400, 2600, 2500, 2700, 2800, 2600, 2900, 3000, 2800, 3100, 3000, 3300],
        "AP": [1500, 1600, 1500, 1700, 1600, 1500, 1700, 1600, 1500, 1700, 1600, 1500, 1700],
        "fixed": [
            ("Payroll", [1, 3, 5, 7, 9, 11, 13], "900"),
            ("Rent", [1, 5, 9, 13], "160"),
            ("Insurance", [1, 5, 9, 13], "80"),
            ("Tax", [4, 11], "550"),
            ("Debt Service", [5, 13], "350"),
            ("Intercompany", [3, 8], "200"),
            ("Revolver", [7], "500"),            # paydown on the line in a healthy week
        ],
    },
    "stress": {
        "R":  [2200, 2300, 2400, 2500, 2700, 2800, 2900, 3000, 3000, 3100, 3200, 3200, 3300],
        "AP": [1500, 1500, 1500, 1600, 1500, 1600, 1500, 1600, 1500, 1600, 1500, 1600, 1500],
        "fixed": [
            ("Payroll", [1, 3, 5, 7, 9, 11, 13], "950"),
            ("Rent", [1, 5, 9, 13], "180"),
            ("Insurance", [1, 5, 9, 13], "90"),
            ("Tax", [3], "900"),
            ("Debt Service", [3], "1200"),
            ("Intercompany", [4, 8], "200"),
        ],
    },
}


def _terms_days(terms: str) -> int:
    parts = terms.split()
    return int(parts[-1]) if len(parts) == 2 and parts[0] == "Net" and parts[-1].isdigit() else 0


def build_paid_history(scenario: str) -> list[dict]:
    """A calibration sample whose per-party AND per-segment mean lag equals the
    segment constant exactly (values spread ±1 day for a realistic std dev)."""
    rows: list[dict] = []
    base = date(2025, 9, 1)
    i = 0
    for seg in CF_SEGMENTS:
        lag = SEGMENT_LAG[seg]
        spread = [lag - 1, lag, lag + 1]
        for party in CF_CUSTOMERS[seg]:
            for k in range(6):  # 6 samples/party -> party lag eligible, mean == lag
                dl = spread[k % 3]
                due = base + timedelta(days=i * 2)
                paid = due + timedelta(days=dl)
                i += 1
                rows.append({
                    "party": party, "segment": seg, "terms": CF_TERMS[seg],
                    "due_date": due.isoformat(), "paid_date": paid.isoformat(),
                })
    return rows


def build_cash_events(config, scenario: str) -> list[dict]:
    """One row per cash event, timed so the behavioral edge lands in the intended
    week (due date back-dated by the segment lag to the Wednesday of that week)."""
    cf = config.cash_flow
    anchor = cf.anchor_date
    plan = _CF_PLAN[scenario]
    R, AP = plan["R"], plan["AP"]
    horizon = len(R)

    events: list[dict] = []
    base_ar: dict[tuple[int, str], dict] = {}
    base_ap: dict[tuple[int, str], dict] = {}
    rid = 0

    def nid() -> str:
        nonlocal rid
        rid += 1
        return f"CF{rid:04d}"

    def wed(w: int) -> date:
        return anchor + timedelta(days=7 * (w - 1) + 2)

    def row(typ, party, seg, amount, due, terms, ref="—"):
        return {
            "row_id": nid(), "po_so": ref, "type": typ, "party": party, "segment": seg,
            "gross_amount": amount,
            "doc_date": (due - timedelta(days=_terms_days(terms))).isoformat(),
            "due_date": due.isoformat(), "terms": terms,
            "exception_flag": False, "exception_reason": "", "suggested_action": "",
        }

    cust_idx = {s: 0 for s in CF_SEGMENTS}
    vend_idx = {s: 0 for s in CF_AP_WEIGHTS}
    ar_seq = ap_seq = 0
    for w in range(1, horizon + 1):
        for seg, wt in CF_INFLOW_WEIGHTS.items():
            amt = (_d(R[w - 1]) * _d("1000") * _d(wt)).quantize(CENT)
            terms = CF_TERMS[seg]
            due = wed(w) - timedelta(days=SEGMENT_LAG[seg])
            party = CF_CUSTOMERS[seg][cust_idx[seg] % len(CF_CUSTOMERS[seg])]
            cust_idx[seg] += 1
            ar_seq += 1
            r = row("Net AR", party, seg, amt, due, terms, ref=f"AR-{ar_seq:04d}")
            events.append(r)
            base_ar[(w, seg)] = r
        for seg, wt in CF_AP_WEIGHTS.items():
            amt = (_d(AP[w - 1]) * _d("1000") * _d(wt)).quantize(CENT)
            terms = CF_TERMS[seg]
            due = wed(w) - timedelta(days=SEGMENT_LAG[seg])
            party = CF_VENDORS[seg][vend_idx[seg] % len(CF_VENDORS[seg])]
            vend_idx[seg] += 1
            ap_seq += 1
            r = row("Net AP", party, seg, -amt, due, terms, ref=f"AP-{ap_seq:04d}")
            events.append(r)
            base_ap[(w, seg)] = r
        for typ, weeks, amt_k in plan["fixed"]:
            if w in weeks:
                amt = (_d(amt_k) * _d("1000")).quantize(CENT)
                events.append(row(typ, "—", "Treasury / Overhead", -amt, wed(w), ""))

    # --- type variety (relabels preserve weekly totals; placement unchanged) ---
    aging = base_ar[(1, "Domestic Trading")]
    aging.update(type="Aging AR", due_date=(anchor - timedelta(days=45)).isoformat(),
                 doc_date=(anchor - timedelta(days=75)).isoformat())
    deposit = base_ar[(6, "International Trading")]
    deposit.update(type="Customer Deposit")
    # International Trading is the only segment carrying customer/vendor prepays.
    prepay = base_ap[(9, "International Trading")]
    prepay.update(type="Vendor Prepay")
    manual = base_ar[(7, "Domestic Trading")]
    manual.update(type="Manual Forecast IN", due_date=wed(7).isoformat())

    # --- exceptions register (flags don't change totals) ---
    def flag(r, reason):
        r.update(exception_flag=True, exception_reason=reason, suggested_action=REASON_ACTION[reason])

    flag(aging, "Over 90 Days")
    flag(base_ar[(2, "Domestic Trading")], "Credit Memo")
    flag(base_ap[(3, "International Trading")], "Dispute")
    flag(deposit, "Unlinked Deposit")
    flag(prepay, "Unlinked Prepay")
    if scenario == "stress":
        flag(base_ar[(4, "MHS")], "Credit Memo")
        flag(base_ap[(5, "Domestic Trading")], "Dispute")
        flag(base_ar[(11, "International Trading")], "Over 90 Days")

    return events


def cash_flow_projection(config, scenario: str) -> dict:
    """The no-lag weekly projection used to calibrate the demo (the engine, which
    times each event, reproduces these closings exactly because lags are exact)."""
    cf = config.cash_flow
    plan = _CF_PLAN[scenario]
    R, AP = plan["R"], plan["AP"]
    horizon = len(R)
    fixed_by_week = [D("0")] * horizon
    for _typ, weeks, amt_k in plan["fixed"]:
        for w in weeks:
            fixed_by_week[w - 1] += _d(amt_k) * _d("1000")

    bal = cf.opening_cash
    closings: list[Decimal] = []
    total_receipts = D("0")
    total_disb = D("0")
    for i in range(horizon):
        rec = _d(R[i]) * _d("1000")
        dis = _d(AP[i]) * _d("1000") + fixed_by_week[i]
        total_receipts += rec
        total_disb += dis
        bal = bal + rec - dis
        closings.append(bal)
    lo = min(closings)
    return {
        "closings": closings,
        "min_closing": lo,
        "min_closing_week": closings.index(lo) + 1,
        "weeks_below_floor": sum(1 for c in closings if c < cf.cash_floor),
        "total_receipts": total_receipts,
        "total_disbursements": -total_disb,
        "opening": cf.opening_cash,
        "floor": cf.cash_floor,
    }


def _assert_cash_flow(config, scenario: str) -> None:
    p = cash_flow_projection(config, scenario)
    if scenario == "stress":
        assert p["weeks_below_floor"] >= 1, f"stress should breach the floor, got {p['weeks_below_floor']}"
        assert p["min_closing"] < p["floor"], f"stress min closing {p['min_closing']} not below floor"
    else:
        assert p["weeks_below_floor"] == 0, f"baseline should stay above floor, got {p['weeks_below_floor']}"
        assert p["min_closing"] > p["floor"], f"baseline min closing {p['min_closing']} not above floor"


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

    cash_events = build_cash_events(config, scenario)
    paid_history = build_paid_history(scenario)
    _assert_cash_flow(config, scenario)

    paths = {
        "ar_aging": out_dir / "ar_aging.csv",
        "inventory": out_dir / "inventory.csv",
        "trial_balance": out_dir / "trial_balance.csv",
        "balance_sheet": out_dir / "balance_sheet.csv",
        "financials_ttm": out_dir / "financials_ttm.csv",
        "financials_2025_refreshed": out_dir / "financials_2025_refreshed.csv",
        "cash_events": out_dir / "cash_events.csv",
        "paid_history": out_dir / "paid_history.csv",
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
    _write_csv(
        paths["cash_events"],
        ["row_id", "po_so", "type", "party", "segment", "gross_amount", "doc_date", "due_date",
         "terms", "exception_flag", "exception_reason", "suggested_action"],
        cash_events,
    )
    _write_csv(
        paths["paid_history"],
        ["party", "segment", "terms", "due_date", "paid_date"],
        paid_history,
    )

    return paths


if __name__ == "__main__":
    written = generate()
    for name, path in written.items():
        print(f"wrote {name:28} -> {path}")
