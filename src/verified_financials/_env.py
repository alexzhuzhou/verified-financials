"""Load environment variables from a repo-root ``.env`` file, if present.

This is a no-op when ``python-dotenv`` isn't installed or no ``.env`` exists, so
the demo's no-key fallback path (see :mod:`verified_financials.ai.briefing`) is
never affected. Real environment variables always win over ``.env`` values.
"""

from __future__ import annotations

from pathlib import Path

# src/verified_financials/_env.py -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOTENV = _REPO_ROOT / ".env"


def load_env() -> None:
    """Populate ``os.environ`` from ``<repo-root>/.env`` (existing vars take precedence)."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - python-dotenv is a declared dependency
        return
    load_dotenv(_DOTENV, override=False)
