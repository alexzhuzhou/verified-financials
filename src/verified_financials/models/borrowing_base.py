"""Borrowing base result DTOs — the structure of the certificate."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IneligibleContribution(BaseModel):
    """One obligor/item's contribution to an ineligible line."""

    model_config = ConfigDict(extra="forbid")

    entity: str
    amount: Decimal
    fact_id: str
    note: str = ""


class IneligibleLine(BaseModel):
    """A single ineligible category (e.g. 'foreign uninsured') with its detail."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    label: str
    citation: str
    amount: Decimal                                  # total excluded under this rule
    detail: list[IneligibleContribution] = Field(default_factory=list)


class ConcentrationLine(BaseModel):
    """A single obligor over the concentration cap (excess-only exclusion)."""

    model_config = ConfigDict(extra="forbid")

    customer: str
    balance_in_base: Decimal                         # balance surviving categorical ineligibles
    cap_amount: Decimal                              # cap_pct * base
    excess_excluded: Decimal
    pct_of_base: Decimal                             # informational
    pct_of_gross: Decimal                            # the headline "22%" figure


class NolvLine(BaseModel):
    """Per-category NOLV (net orderly liquidation value) haircut detail."""

    model_config = ConfigDict(extra="forbid")

    category: str
    cost: Decimal
    nolv_ratio: Decimal                              # NOLV-to-cost ratio
    nolv_value: Decimal                              # min(cost, nolv_ratio * cost)


class AssetClassResult(BaseModel):
    """One collateral class (A/R or inventory) through the waterfall."""

    model_config = ConfigDict(extra="forbid")

    asset_class: str                                 # "accounts_receivable" | "inventory"
    gross: Decimal
    ineligibles: list[IneligibleLine] = Field(default_factory=list)
    concentration: list[ConcentrationLine] = Field(default_factory=list)
    total_ineligible: Decimal
    eligible: Decimal                                # eligible amount at cost
    valuation_basis: str = "cost"                    # "cost" | "nolv"
    nolv_detail: list[NolvLine] = Field(default_factory=list)
    eligible_nolv_value: Decimal | None = None       # NOLV-adjusted base (nolv mode only)
    advance_rate: Decimal
    availability: Decimal                            # (eligible or NOLV value) * advance_rate


class BorrowingBaseCertificate(BaseModel):
    """The bank-ready certificate."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    as_of_date: date
    borrower: str
    lender: str
    agent: str
    facility_name: str
    agreement_reference: str
    certificate_no: int = 1
    config_hash: str

    accounts_receivable: AssetClassResult
    inventory: AssetClassResult

    gross_availability: Decimal                      # AR avail + inventory avail
    reserves_total: Decimal
    reserve_detail: list[dict] = Field(default_factory=list)
    borrowing_base: Decimal                          # min(gross_availability - reserves, commitment)
    commitment: Decimal
    binding_constraint: str                          # "borrowing_base" | "commitment"
    suppressed_availability: Decimal                 # max(0, (gross_avail - reserves) - commitment)
    outstanding: Decimal
    lc_exposure: Decimal
    excess_availability: Decimal                     # borrowing_base - outstanding - lc_exposure
