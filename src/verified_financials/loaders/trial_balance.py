"""Trial balance loader — one fact per account, keeping debit/credit in
attributes so the verification engine can sum each side."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_decimal, provenance, read_rows

DATASET = Dataset.TRIAL_BALANCE.value


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):
        where = f"{path.name} row {i}, account {row['account']!r}"
        debit = parse_decimal(row["debit"], where=f"{where}, column 'debit'")
        credit = parse_decimal(row["credit"], where=f"{where}, column 'credit'")
        side = "debit" if debit != 0 else "credit"
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, row["metric"], row["account"]),
                dataset=DATASET,
                entity=row["account"],
                metric=row["metric"],
                value=debit if debit != 0 else credit,
                attributes={"debit": str(debit), "credit": str(credit), "side": side},
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
