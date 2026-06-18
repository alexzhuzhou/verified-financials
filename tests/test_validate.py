"""Safe parse helpers + value-level upload validation (demo-hardening)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from verified_financials import datagen
from verified_financials.loaders.base import DataError, parse_decimal, parse_int
from verified_financials.loaders.validate import validate_upload


# --------------------------------------------------------------------------- #
# Parse helpers
# --------------------------------------------------------------------------- #
def test_parse_decimal_valid_and_empty():
    assert parse_decimal("1234.50", where="x") == Decimal("1234.50")
    assert parse_decimal("", where="x") == Decimal("0")  # empty → 0 (unchanged behavior)


def test_parse_int_valid():
    assert parse_int("45", where="x") == 45
    assert parse_int("  7 ", where="x") == 7


def test_parse_decimal_bad_value_raises_friendly():
    with pytest.raises(DataError) as exc:
        parse_decimal("not-a-number", where="inventory.csv row 5, column 'value'")
    msg = str(exc.value)
    assert "inventory.csv row 5, column 'value'" in msg
    assert "not-a-number" in msg


def test_parse_int_bad_value_raises_friendly():
    with pytest.raises(DataError) as exc:
        parse_int("soon", where="ar_aging.csv row 8, column 'days_past_due'")
    msg = str(exc.value)
    assert "whole number" in msg
    assert "soon" in msg


def test_dataerror_is_valueerror():
    # subclassing ValueError keeps existing `except ValueError` sites working
    assert issubclass(DataError, ValueError)


# --------------------------------------------------------------------------- #
# validate_upload — value-level checks
# --------------------------------------------------------------------------- #
def test_validate_upload_clean_baseline(tmp_path):
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    assert validate_upload(tmp_path) == []


def test_validate_upload_bad_int_value(tmp_path):
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    ar = tmp_path / "ar_aging.csv"
    # append a row with a non-numeric days_past_due (cols match the fixed header)
    ar.write_text(ar.read_text() + "BadCo,Foodservice,US,false,false,soon,0,0,0,0,0,0\n")
    errors = validate_upload(tmp_path)
    assert any(
        "ar_aging.csv" in e and "days_past_due" in e and "whole number" in e for e in errors
    ), errors


def test_validate_upload_bad_decimal_value(tmp_path):
    datagen.generate(data_dir=tmp_path, scenario="baseline")
    inv = tmp_path / "inventory.csv"
    inv.write_text(inv.read_text() + "BadItem,Grocery,Dry,abc,10,false\n")
    errors = validate_upload(tmp_path)
    assert any("inventory.csv" in e and "value" in e and "abc" in e for e in errors), errors
