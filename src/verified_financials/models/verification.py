"""Verification / tie-out result DTOs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FactRef(BaseModel):
    """A resolved side of a tie-out check, carrying full provenance."""

    model_config = ConfigDict(extra="forbid")

    ref: str                                  # the config fact reference, e.g. "ar_aging.total_sum"
    value: Decimal
    source_file: str
    source_locator: str
    as_of_date: date
    version_tag: str | None = None


class Finding(BaseModel):
    """The result of one tie-out check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    label: str
    status: str                               # "pass" | "fail"
    severity: str
    left: FactRef
    right: FactRef
    delta: Decimal                            # left - right
    tolerance_abs: Decimal
    message: str


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    as_of_date: date
    findings: list[Finding] = Field(default_factory=list)
    passed: int
    failed: int
