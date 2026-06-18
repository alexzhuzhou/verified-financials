"""SQLite connection management + schema DDL.

SQLite is a real, transactional relational store and is the right call for a
portable demo. All SQL is confined to this package (see :mod:`repository`) so
swapping in Postgres later means implementing one new repository class.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id             TEXT PRIMARY KEY,
    dataset        TEXT NOT NULL,
    entity         TEXT,
    metric         TEXT NOT NULL,
    value          TEXT NOT NULL,          -- Decimal serialized as string (lossless)
    unit           TEXT NOT NULL DEFAULT 'USD',
    attributes     TEXT NOT NULL DEFAULT '{}',  -- JSON
    source_file    TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    as_of_date     TEXT NOT NULL,
    loaded_at      TEXT NOT NULL,
    version_tag    TEXT
);
CREATE INDEX IF NOT EXISTS idx_facts_dataset_metric ON facts(dataset, metric);
CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    as_of_date  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    run_id  TEXT NOT NULL REFERENCES runs(run_id),
    engine  TEXT NOT NULL,
    payload TEXT NOT NULL,                 -- full DTO JSON
    summary TEXT NOT NULL,                 -- small headline JSON
    PRIMARY KEY (run_id, engine)
);

CREATE TABLE IF NOT EXISTS findings (
    run_id      TEXT NOT NULL REFERENCES runs(run_id),
    check_id    TEXT NOT NULL,
    status      TEXT NOT NULL,
    severity    TEXT NOT NULL,
    left_value  TEXT,
    right_value TEXT,
    delta       TEXT,
    payload     TEXT NOT NULL,
    PRIMARY KEY (run_id, check_id)
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a connection with dict-like rows and FK enforcement."""
    conn = sqlite3.connect(str(database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
