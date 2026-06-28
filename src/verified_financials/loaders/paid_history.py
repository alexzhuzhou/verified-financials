"""Paid-history loader — the calibration sample for the timing engine.

Each row of ``paid_history.csv`` is a previously-paid invoice: its contractual
due date and the date it actually settled. The cash-flow engine derives the
average days-late lag per party / segment / portfolio from this sample and uses
it to time forward-looking cash events.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_decimal, provenance, read_rows

DATASET = Dataset.PAID_HISTORY.value

COLUMNS = ["party", "segment", "terms", "due_date", "paid_date"]


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):  # header is row 1
        where = f"{path.name} row {i}"
        due = date.fromisoformat(row["due_date"])
        paid = date.fromisoformat(row["paid_date"])
        days_late = (paid - due).days
        attributes = {
            "party": row["party"],
            "segment": row["segment"],
            "terms": row.get("terms", ""),
            "due_date": row["due_date"],
            "paid_date": row["paid_date"],
        }
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, "days_late", f"{row['party']}#{i}"),
                dataset=DATASET,
                entity=row["party"],
                metric="days_late",
                value=parse_decimal(str(days_late), where=f"{where}, days_late"),
                unit="days",
                attributes=attributes,
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
