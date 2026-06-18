"""Validation for user-uploaded CSVs (lightweight: fixed schema, no mapping).

The columns mirror exactly what the per-dataset loaders read, so a valid upload
flows through the existing ingest path unchanged.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .base import DataError, parse_decimal, parse_int, read_rows

# filename -> required columns (a superset is fine; extras are ignored)
EXPECTED_COLUMNS: dict[str, list[str]] = {
    "ar_aging.csv": [
        "customer", "segment", "country", "credit_insured", "affiliate",
        "days_past_due", "current", "1_30", "31_60", "61_90", "90_plus", "total",
    ],
    "inventory.csv": ["item", "segment", "category", "value", "days_since_last_movement", "obsolete"],
    "trial_balance.csv": ["account", "metric", "debit", "credit"],
    "balance_sheet.csv": ["line_item", "metric", "section", "amount"],
    "financials_ttm.csv": ["metric", "value", "period"],
    "financials_2025_refreshed.csv": ["metric", "value", "period"],
}

REQUIRED_FILES = list(EXPECTED_COLUMNS)

# Columns whose cell values must parse — checked row-by-row so bad data is
# caught at UPLOAD time (with a row/column locator) rather than crashing compute.
_NUMERIC_COLUMNS: dict[str, list[str]] = {
    "ar_aging.csv": ["current", "1_30", "31_60", "61_90", "90_plus", "total"],
    "inventory.csv": ["value"],
    "trial_balance.csv": ["debit", "credit"],
    "balance_sheet.csv": ["amount"],
    "financials_ttm.csv": ["value"],
    "financials_2025_refreshed.csv": ["value"],
}
_INT_COLUMNS: dict[str, list[str]] = {
    "ar_aging.csv": ["days_past_due"],
    "inventory.csv": ["days_since_last_movement"],
}

MAX_VALUE_ERRORS = 25


def header_of(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh), [])


def file_errors(filename: str, header: list[str]) -> list[str]:
    """Validation errors for a single file's header (empty list == OK)."""
    expected = EXPECTED_COLUMNS.get(filename)
    if expected is None:
        return [f"{filename}: unexpected file (not one of the {len(REQUIRED_FILES)} datasets)"]
    missing = [c for c in expected if c not in header]
    return [f"{filename}: missing column(s): {', '.join(missing)}"] if missing else []


def value_errors(filename: str, path: Path, *, limit: int = MAX_VALUE_ERRORS) -> list[str]:
    """Per-cell errors for a file's numeric/int columns (header assumed valid)."""
    numeric = _NUMERIC_COLUMNS.get(filename, [])
    ints = _INT_COLUMNS.get(filename, [])
    if not (numeric or ints):
        return []
    errors: list[str] = []
    for i, row in enumerate(read_rows(path), start=2):  # header is row 1
        for col in numeric:
            if col not in row:
                continue
            try:
                parse_decimal(row[col], where=f"{filename} row {i}, column '{col}'")
            except DataError as exc:
                errors.append(str(exc))
        for col in ints:
            if col not in row:
                continue
            try:
                parse_int(row[col], where=f"{filename} row {i}, column '{col}'")
            except DataError as exc:
                errors.append(str(exc))
        if len(errors) >= limit:
            errors = errors[:limit]
            errors.append(f"{filename}: … and more (showing the first {limit} value errors)")
            break
    return errors


def validate_upload(directory: str | Path) -> list[str]:
    """Validate a directory of uploaded CSVs against the fixed schema and cell values."""
    directory = Path(directory)
    errors: list[str] = []
    for filename in REQUIRED_FILES:
        path = directory / filename
        if not path.exists():
            errors.append(f"{filename}: not found")
            continue
        header_errs = file_errors(filename, header_of(path))
        if header_errs:
            errors.extend(header_errs)
            continue  # can't reliably value-check a file with the wrong header
        errors.extend(value_errors(filename, path))
    return errors
