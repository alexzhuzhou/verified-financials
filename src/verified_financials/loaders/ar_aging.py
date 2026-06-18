"""A/R aging loader — one ``total`` fact per customer, carrying the aging
buckets and eligibility attributes the borrowing-base engine needs."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_bool, parse_decimal, parse_int, provenance, read_rows

DATASET = Dataset.AR_AGING.value
_BUCKETS = ["current", "1_30", "31_60", "61_90", "90_plus"]


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):  # header is row 1
        customer = row["customer"]
        where = f"{path.name} row {i}, customer {customer!r}"
        # bucket amounts stored as canonical strings so behaviour is identical
        # before and after the JSON round-trip through SQLite.
        buckets = {b: str(parse_decimal(row[b], where=f"{where}, column '{b}'")) for b in _BUCKETS}
        attributes = {
            "segment": row["segment"],
            "country": row["country"],
            "credit_insured": parse_bool(row["credit_insured"]),
            "is_affiliate": parse_bool(row["affiliate"]),
            "days_past_due": parse_int(row["days_past_due"], where=f"{where}, column 'days_past_due'"),
            **buckets,
        }
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, "total", customer),
                dataset=DATASET,
                entity=customer,
                metric="total",
                value=parse_decimal(row["total"], where=f"{where}, column 'total'"),
                attributes=attributes,
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
