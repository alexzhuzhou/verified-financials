"""The :class:`Fact` — the atomic, provenance-tracked unit of the fact store.

Every figure that flows into an engine is a Fact, and every Fact knows exactly
where it came from (file + locator + as-of date + version). That traceability
is the whole point of "Verified" Financials.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Provenance(BaseModel):
    """Where a figure came from."""

    model_config = ConfigDict(extra="forbid")

    source_file: str                       # e.g. "ar_aging.csv"
    source_locator: str                    # e.g. "row 14" or "row 14, col 90_plus" or "B7"
    as_of_date: date                       # reporting date the figure represents
    loaded_at: datetime                    # ingestion timestamp
    version_tag: str | None = None         # e.g. "original" | "refreshed_2025-12-15"


class Fact(BaseModel):
    """A single traceable figure."""

    model_config = ConfigDict(extra="forbid")

    id: str                                # deterministic: dataset:entity:metric[:version]
    dataset: str                           # see :class:`~.enums.Dataset`
    entity: str | None = None              # customer / item / account; None for summary metrics
    metric: str                            # "total" | "90_plus" | "ebitda" | "inventory" ...
    value: Decimal
    unit: str = "USD"
    attributes: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance

    @staticmethod
    def make_id(
        dataset: str, metric: str, entity: str | None = None, version: str | None = None
    ) -> str:
        parts = [dataset, entity or "_", metric]
        if version:
            parts.append(version)
        return ":".join(parts)
