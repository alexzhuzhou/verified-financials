"""FCCR covenant result DTOs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FccrComponent(BaseModel):
    """One line item feeding the FCCR, tagged with its placement."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: Decimal
    fact_id: str | None = None
    side: str                                 # "numerator" | "denominator"
    role: str                                 # "add" | "subtract"


class QuarterPoint(BaseModel):
    """A point on the FCCR trend line."""

    model_config = ConfigDict(extra="forbid")

    quarter: str                              # e.g. "Q2-2025"
    fccr: Decimal


class FccrReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    as_of_date: date
    basis: str = "TTM"

    components: list[FccrComponent] = Field(default_factory=list)
    numerator: Decimal                        # FCC-adjusted EBITDA
    denominator: Decimal                      # fixed charges
    fccr: Decimal

    covenant: Decimal
    in_compliance: bool
    headroom_abs: Decimal                     # fccr - covenant (turns)
    headroom_pct: Decimal                     # (fccr - covenant) / covenant
    ebitda_cushion: Decimal                   # numerator - covenant * denominator

    # Springing covenant — tested only when excess availability < trigger.
    springing_enabled: bool = False
    covenant_active: bool = True              # whether the covenant is currently tested
    springing_trigger: Decimal | None = None
    excess_availability: Decimal | None = None

    # Equity cure — equity needed to lift FCCR to exactly the covenant.
    equity_cure_enabled: bool = False
    equity_cure_needed: Decimal = Decimal("0")
    cures_used: int = 0
    cures_remaining_year: int | None = None
    cures_remaining_lifetime: int | None = None

    trend: list[QuarterPoint] = Field(default_factory=list)
    consecutive_declines: int = 0
    early_warning: bool = False
    warning_reasons: list[str] = Field(default_factory=list)
