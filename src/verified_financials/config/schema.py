"""Typed schema for ``config.yaml`` — the loan-agreement-as-config.

Every rate, cap, threshold, and rule the engines apply is validated here so a
malformed agreement fails fast and loudly rather than silently mis-computing a
borrowing base.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------- #
# Facility
# --------------------------------------------------------------------------- #
class FacilityConfig(_Frozen):
    borrower: str
    lender: str
    agent: str
    agreement_reference: str
    name: str
    commitment: Decimal
    outstanding: Decimal
    lc_exposure: Decimal = Decimal("0")
    currency: str = "USD"
    as_of_date: date


# --------------------------------------------------------------------------- #
# Borrowing base
# --------------------------------------------------------------------------- #
class IneligibleRule(_Frozen):
    id: str
    label: str
    type: Literal["aged_bucket", "predicate"]
    citation: str
    bucket_field: str | None = None          # required when type == aged_bucket
    predicate: str | None = None             # required when type == predicate


class CrossAgingConfig(_Frozen):
    enabled: bool = False
    threshold_pct: Decimal = Decimal("0.50")
    citation: str = ""


class ConcentrationCapConfig(_Frozen):
    pct: Decimal
    basis: Literal["post_categorical", "gross"] = "post_categorical"
    citation: str = ""


class ReserveConfig(_Frozen):
    id: str
    label: str
    type: Literal["fixed", "dilution", "priority_payable", "rent"] = "fixed"
    amount: Decimal = Decimal("0")          # fixed / priority_payable / rent
    dilution_pct: Decimal | None = None     # dilution only
    threshold_pct: Decimal | None = None    # dilution only
    citation: str = ""


class AccountsReceivableConfig(_Frozen):
    advance_rate: Decimal
    ineligible_rules: list[IneligibleRule] = Field(default_factory=list)
    cross_aging: CrossAgingConfig = Field(default_factory=CrossAgingConfig)
    concentration_cap: ConcentrationCapConfig


class InventoryConfig(_Frozen):
    advance_rate: Decimal                    # % of cost (cost mode) or % of NOLV (nolv mode)
    ineligible_rules: list[IneligibleRule] = Field(default_factory=list)
    valuation: Literal["cost", "nolv"] = "cost"
    # NOLV-to-cost ratio per inventory category (nolv mode only)
    nolv_by_category: dict[str, Decimal] = Field(default_factory=dict)


class BorrowingBaseConfig(_Frozen):
    accounts_receivable: AccountsReceivableConfig
    inventory: InventoryConfig
    reserves: list[ReserveConfig] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# FCCR
# --------------------------------------------------------------------------- #
class FccrFormulaSide(_Frozen):
    add: list[str] = Field(default_factory=list)
    subtract: list[str] = Field(default_factory=list)


class FccrEarlyWarningConfig(_Frozen):
    headroom_pct_warn: Decimal = Decimal("0.15")
    declining_quarters_warn: int = 2


class SpringingConfig(_Frozen):
    """FCCR is tested only when excess availability falls below the trigger."""

    enabled: bool = False
    trigger_pct: Decimal = Decimal("0")      # of commitment
    trigger_floor: Decimal = Decimal("0")    # dollar floor; trigger = max(pct*commitment, floor)
    citation: str = ""


class EquityCureConfig(_Frozen):
    enabled: bool = False
    max_per_year: int = 0
    max_lifetime: int = 0
    cures_used: int = 0
    citation: str = ""


class FccrConfig(_Frozen):
    covenant_threshold: Decimal
    numerator: FccrFormulaSide
    denominator: FccrFormulaSide
    early_warning: FccrEarlyWarningConfig = Field(default_factory=FccrEarlyWarningConfig)
    springing: SpringingConfig = Field(default_factory=SpringingConfig)
    equity_cure: EquityCureConfig = Field(default_factory=EquityCureConfig)


# --------------------------------------------------------------------------- #
# Cash flow (13-week direct forecast)
# --------------------------------------------------------------------------- #
class CashFlowConfig(_Frozen):
    """Parameters for the bottom-up 13-week cash-flow forecast.

    The ledger of cash events drives the amounts; this config controls the
    horizon, the opening balance, the floor that flags a liquidity squeeze, and
    the timing engine (how the behavioral lag is applied / overridden).
    """

    anchor_date: date                          # W1 Monday — the forecast start
    horizon_weeks: int = 13
    opening_cash: Decimal                       # bank cash at the start of W1
    cash_floor: Decimal = Decimal("0")          # flag any week closing below this
    timing_method: Literal["behavioral", "contractual"] = "behavioral"  # primary edge
    lag_fallback_min_samples: int = 5           # party lag used only with >= this many paid samples
    # Event types that bypass the lag engine entirely (post on their stated date).
    fixed_cost_types: list[str] = Field(
        default_factory=lambda: [
            "Payroll", "Rent", "Tax", "Insurance", "Intercompany", "Debt Service", "Revolver",
        ]
    )
    global_lag_shift_days: Decimal = Decimal("0")   # what-if: shift every behavioral lag by N days


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
Severity = Literal["info", "low", "medium", "high", "critical"]


class VerificationCheck(_Frozen):
    id: str
    label: str
    left: str                                 # fact reference, e.g. "balance_sheet.inventory"
    right: str
    tolerance_abs: Decimal
    severity: Severity = "high"


class VerificationConfig(_Frozen):
    default_tolerance_abs: Decimal = Decimal("1000")
    checks: list[VerificationCheck] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Settings + root
# --------------------------------------------------------------------------- #
class SettingsConfig(_Frozen):
    database_path: str = "./vfin.db"
    data_dir: str = "./data"
    artifacts_dir: str = "./artifacts"
    random_seed: int = 42


class Config(_Frozen):
    facility: FacilityConfig
    borrowing_base: BorrowingBaseConfig
    fccr: FccrConfig
    cash_flow: CashFlowConfig
    verification: VerificationConfig
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
