"""Balance sheet loader — one fact per summary line item."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_decimal, provenance, read_rows

DATASET = Dataset.BALANCE_SHEET.value


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, row["metric"], row["line_item"]),
                dataset=DATASET,
                entity=row["line_item"],
                metric=row["metric"],
                value=parse_decimal(
                    row["amount"], where=f"{path.name} row {i}, line {row['line_item']!r}, column 'amount'"
                ),
                attributes={"section": row["section"]},
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
