"""Financials loaders — TTM components + trend, and the re-sent ("refreshed")
version whose revenue deliberately conflicts with the original."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..models.enums import Dataset
from ..models.fact import Fact
from .base import parse_decimal, provenance, read_rows

TTM = Dataset.FINANCIALS_TTM.value
REFRESHED = Dataset.FINANCIALS_REFRESHED.value

ORIGINAL_VERSION = "original"
REFRESHED_VERSION = "refreshed_2025-12-15"


def load_ttm(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):
        metric = row["metric"]
        period = row["period"]
        value = parse_decimal(row["value"], where=f"{path.name} row {i}, metric {metric!r}, column 'value'")
        prov = provenance(path.name, f"row {i}", as_of, loaded_at, ORIGINAL_VERSION)
        if metric == "fccr_history":
            facts.append(
                Fact(
                    id=Fact.make_id(TTM, "fccr_history", period, ORIGINAL_VERSION),
                    dataset=TTM,
                    entity=period,
                    metric="fccr_history",
                    value=value,
                    unit="ratio",
                    attributes={"period": period},
                    provenance=prov,
                )
            )
        else:
            facts.append(
                Fact(
                    id=Fact.make_id(TTM, metric, None, ORIGINAL_VERSION),
                    dataset=TTM,
                    metric=metric,
                    value=value,
                    attributes={"period": period},
                    provenance=prov,
                )
            )
    return facts


def load_refreshed(path: Path, as_of: date, loaded_at: datetime) -> list[Fact]:
    facts: list[Fact] = []
    for i, row in enumerate(read_rows(path), start=2):
        metric = row["metric"]
        facts.append(
            Fact(
                id=Fact.make_id(REFRESHED, metric, None, REFRESHED_VERSION),
                dataset=REFRESHED,
                metric=metric,
                value=parse_decimal(
                    row["value"], where=f"{path.name} row {i}, metric {metric!r}, column 'value'"
                ),
                attributes={"period": row["period"]},
                provenance=provenance(
                    path.name, f"row {i}", as_of, loaded_at, REFRESHED_VERSION
                ),
            )
        )
    return facts
