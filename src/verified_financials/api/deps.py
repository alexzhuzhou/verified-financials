"""FastAPI dependencies — config + a read connection to the configured DB."""

from __future__ import annotations

from collections.abc import Iterator

from ..config.loader import load_config
from ..config.schema import Config
from ..store.db import connect, init_schema


def get_config() -> Config:
    return load_config()


def get_conn() -> Iterator:
    config = load_config()
    conn = connect(config.settings.database_path)
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()
