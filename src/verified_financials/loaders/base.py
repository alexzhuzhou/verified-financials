"""Loader helpers and the ``load_all`` orchestrator.

Each loader turns one CSV into a list of :class:`Fact`, attaching provenance
(source file + locator + as-of date + version tag) to every figure.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..models.fact import Fact, Provenance


class DataError(ValueError):
    """A user-facing data problem (bad/garbled value in a source file).

    Subclasses ``ValueError`` so existing ``except ValueError`` sites keep
    catching it; the API maps it to a friendly HTTP 422 with this message.
    """


def parse_decimal(raw: str, *, where: str = "value") -> Decimal:
    """Parse a money/number cell. Empty → 0. Bad input → friendly DataError."""
    try:
        return Decimal((raw or "0").strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DataError(f"{where}: expected a number, got {raw!r}") from exc


def parse_int(raw: str, *, where: str) -> int:
    """Parse a whole-number cell. Bad input → friendly DataError."""
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError) as exc:
        raise DataError(f"{where}: expected a whole number, got {raw!r}") from exc


def parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() in {"true", "1", "yes", "y", "t"}


def read_rows(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def provenance(
    source_file: str,
    locator: str,
    as_of: date,
    loaded_at: datetime,
    version_tag: str | None = None,
) -> Provenance:
    return Provenance(
        source_file=source_file,
        source_locator=locator,
        as_of_date=as_of,
        loaded_at=loaded_at,
        version_tag=version_tag,
    )


def load_all(data_dir: str | Path, as_of: date) -> list[Fact]:
    """Load every dataset in the data directory into a single fact list."""
    from . import ar_aging, balance_sheet, financials, inventory, trial_balance

    data_dir = Path(data_dir)
    loaded_at = datetime.now()
    facts: list[Fact] = []
    facts += ar_aging.load(data_dir / "ar_aging.csv", as_of, loaded_at)
    facts += inventory.load(data_dir / "inventory.csv", as_of, loaded_at)
    facts += trial_balance.load(data_dir / "trial_balance.csv", as_of, loaded_at)
    facts += balance_sheet.load(data_dir / "balance_sheet.csv", as_of, loaded_at)
    facts += financials.load_ttm(data_dir / "financials_ttm.csv", as_of, loaded_at)
    facts += financials.load_refreshed(
        data_dir / "financials_2025_refreshed.csv", as_of, loaded_at
    )
    return facts
