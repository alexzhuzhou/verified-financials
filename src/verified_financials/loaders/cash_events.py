"""Cash-event ledger loader — one Fact per cash event.

Each row of ``cash_events.csv`` is a single cash movement (a receivable, a
payable, a payroll run, a debt-service installment, …). The cash-flow engine
times each one into a forecast week and stacks them into the weekly waterfall.
The amount is the metric; the timing/classification fields ride in attributes.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_bool, parse_decimal, provenance, read_rows

DATASET = Dataset.CASH_EVENTS.value

COLUMNS = [
    "row_id", "po_so", "type", "party", "segment", "gross_amount",
    "doc_date", "due_date", "terms",
    "exception_flag", "exception_reason", "suggested_action",
]


def load(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):  # header is row 1
        row_id = row["row_id"]
        where = f"{path.name} row {i}, event {row_id!r}"
        attributes = {
            "po_so": row.get("po_so", ""),
            "type": row["type"],
            "party": row["party"],
            "segment": row["segment"],
            "doc_date": row["doc_date"],
            "due_date": row["due_date"],
            "terms": row.get("terms", ""),
            "exception_flag": parse_bool(row.get("exception_flag", "")),
            "exception_reason": row.get("exception_reason", ""),
            "suggested_action": row.get("suggested_action", ""),
        }
        facts.append(
            Fact(
                id=Fact.make_id(DATASET, "amount", row_id),
                dataset=DATASET,
                entity=row_id,
                metric="amount",
                value=parse_decimal(row["gross_amount"], where=f"{where}, column 'gross_amount'"),
                attributes=attributes,
                provenance=provenance(path.name, f"row {i}", as_of, loaded_at),
            )
        )
    return facts
