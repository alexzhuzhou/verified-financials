"""Inventory loader — one ``value`` fact per item with eligibility attributes."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_bool, parse_decimal, parse_int, provenance, read_rows

DATASET = Dataset.INVENTORY.value


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):
        item = row["item"]
        where = f"{path.name} row {i}, item {item!r}"
        attributes = {
            "segment": row["segment"],
            "category": row["category"],
            "obsolete": parse_bool(row["obsolete"]),
            "days_since_last_movement": parse_int(
                row["days_since_last_movement"], where=f"{where}, column 'days_since_last_movement'"
            ),
        }
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, "value", item),
                dataset=DATASET,
                entity=item,
                metric="value",
                value=parse_decimal(row["value"], where=f"{where}, column 'value'"),
                attributes=attributes,
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
