"""Data-access layer. Engines and the pipeline talk only to these classes.

All SQL lives here. A future ``PostgresRepository`` would implement the same
methods over a ``numeric``/``jsonb`` schema with no engine changes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..models.fact import Fact, Provenance


def _fact_to_row(fact: Fact) -> tuple:
    return (
        fact.id,
        fact.dataset,
        fact.entity,
        fact.metric,
        str(fact.value),
        fact.unit,
        json.dumps(fact.attributes, sort_keys=True, default=str),
        fact.provenance.source_file,
        fact.provenance.source_locator,
        fact.provenance.as_of_date.isoformat(),
        fact.provenance.loaded_at.isoformat(),
        fact.provenance.version_tag,
    )


def _row_to_fact(row: sqlite3.Row) -> Fact:
    return Fact(
        id=row["id"],
        dataset=row["dataset"],
        entity=row["entity"],
        metric=row["metric"],
        value=Decimal(row["value"]),
        unit=row["unit"],
        attributes=json.loads(row["attributes"]),
        provenance=Provenance(
            source_file=row["source_file"],
            source_locator=row["source_locator"],
            as_of_date=date.fromisoformat(row["as_of_date"]),
            loaded_at=datetime.fromisoformat(row["loaded_at"]),
            version_tag=row["version_tag"],
        ),
    )


class FactRepository:
    """Read/write access to the provenance-tracked fact store."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_many(self, facts: list[Fact]) -> int:
        rows = [_fact_to_row(f) for f in facts]
        self._conn.executemany(
            """
            INSERT INTO facts
                (id, dataset, entity, metric, value, unit, attributes,
                 source_file, source_locator, as_of_date, loaded_at, version_tag)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                value=excluded.value, unit=excluded.unit, attributes=excluded.attributes,
                source_file=excluded.source_file, source_locator=excluded.source_locator,
                as_of_date=excluded.as_of_date, loaded_at=excluded.loaded_at,
                version_tag=excluded.version_tag
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def query(
        self,
        dataset: str | None = None,
        metric: str | None = None,
        entity: str | None = None,
    ) -> list[Fact]:
        clauses, params = [], []
        if dataset is not None:
            clauses.append("dataset = ?")
            params.append(dataset)
        if metric is not None:
            clauses.append("metric = ?")
            params.append(metric)
        if entity is not None:
            clauses.append("entity = ?")
            params.append(entity)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        # entity/id ordering keeps results deterministic for golden snapshots
        sql = f"SELECT * FROM facts{where} ORDER BY entity IS NOT NULL, entity, id"
        cur = self._conn.execute(sql, params)
        return [_row_to_fact(r) for r in cur.fetchall()]

    def get_fact(
        self, dataset: str, metric: str, version_tag: str | None = None
    ) -> Fact | None:
        if version_tag is None:
            cur = self._conn.execute(
                "SELECT * FROM facts WHERE dataset=? AND metric=? LIMIT 1",
                (dataset, metric),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM facts WHERE dataset=? AND metric=? AND version_tag=? LIMIT 1",
                (dataset, metric, version_tag),
            )
        row = cur.fetchone()
        return _row_to_fact(row) if row else None

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) AS n FROM facts").fetchone()["n"]


class ResultRepository:
    """Persists run metadata, engine results, and verification findings."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_run(self, run_id: str, created_at: str, config_hash: str, as_of: date) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, created_at, config_hash, as_of_date) "
            "VALUES (?,?,?,?)",
            (run_id, created_at, config_hash, as_of.isoformat()),
        )
        self._conn.commit()

    def save_result(self, run_id: str, engine: str, payload: dict, summary: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO results (run_id, engine, payload, summary) VALUES (?,?,?,?)",
            (run_id, engine, json.dumps(payload, default=str), json.dumps(summary, default=str)),
        )
        self._conn.commit()

    def save_findings(self, run_id: str, findings: list[dict]) -> None:
        rows = [
            (
                run_id,
                f["check_id"],
                f["status"],
                f["severity"],
                str(f["left"]["value"]),
                str(f["right"]["value"]),
                str(f["delta"]),
                json.dumps(f, default=str),
            )
            for f in findings
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO findings "
            "(run_id, check_id, status, severity, left_value, right_value, delta, payload) "
            "VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()

    def get_result(self, run_id: str, engine: str) -> dict | None:
        row = self._conn.execute(
            "SELECT payload FROM results WHERE run_id=? AND engine=?", (run_id, engine)
        ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_runs(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM runs ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
