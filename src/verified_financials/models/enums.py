"""Shared enums / literal types."""

from __future__ import annotations

from enum import Enum


class Dataset(str, Enum):
    TRIAL_BALANCE = "trial_balance"
    BALANCE_SHEET = "balance_sheet"
    AR_AGING = "ar_aging"
    INVENTORY = "inventory"
    FINANCIALS_TTM = "financials_ttm"
    FINANCIALS_REFRESHED = "financials_refreshed"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
