"""Load and validate ``config.yaml`` into a typed :class:`Config`.

A ``config_hash`` (sha256 of the resolved config) is computed so every pipeline
run records exactly which rule-set produced its numbers — provenance for the
rules themselves, not just the data.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml

from .schema import Config

# Repo root = three levels up from this file (.../src/verified_financials/config/loader.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = _REPO_ROOT / "config.yaml"


def load_config(path: str | Path | None = None) -> Config:
    """Parse and validate the YAML config file into a :class:`Config`."""
    if path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = _REPO_ROOT / config_path  # resolve relative to repo root
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)


@lru_cache(maxsize=8)
def get_config(path: str | None = None) -> Config:
    """Cached config accessor for the API / CLI hot paths."""
    return load_config(path)


def config_hash(config: Config) -> str:
    """Stable sha256 of the resolved config (Decimals/dates as strings)."""
    payload = config.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
