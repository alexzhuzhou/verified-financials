"""Golden snapshot tests — lock the entire certificate / reports line by line.

Run with VFIN_UPDATE_GOLDEN=1 to (re)write the snapshots after an intended
change; otherwise any drift in the math or rules fails here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from verified_financials.engines.borrowing_base import compute_borrowing_base
from verified_financials.engines.fccr import compute_fccr
from verified_financials.engines.verification import run_verification

GOLDEN = Path(__file__).parent / "golden"
RUN_ID = "GOLDEN"


def _canonical(dto) -> str:
    return json.dumps(dto.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"


def _check(name: str, dto):
    path = GOLDEN / f"{name}.json"
    actual = _canonical(dto)
    if os.environ.get("VFIN_UPDATE_GOLDEN"):
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"updated golden {name}")
    assert path.exists(), f"missing golden {path}; run with VFIN_UPDATE_GOLDEN=1"
    assert actual == path.read_text(encoding="utf-8")


def test_golden_verification(repo, config):
    _check("verification_report", run_verification(repo, config, RUN_ID))


def test_golden_borrowing_base(repo, config):
    _check("borrowing_base_certificate", compute_borrowing_base(repo, config, RUN_ID))


def test_golden_fccr(repo, config):
    _check("fccr_report", compute_fccr(repo, config, RUN_ID))


def test_golden_stress_borrowing_base(stress_repo, stress_config):
    _check("stress_borrowing_base_certificate", compute_borrowing_base(stress_repo, stress_config, RUN_ID))


def test_golden_stress_fccr(stress_repo, stress_config):
    cert = compute_borrowing_base(stress_repo, stress_config, RUN_ID)
    _check(
        "stress_fccr_report",
        compute_fccr(stress_repo, stress_config, RUN_ID, excess_availability=cert.excess_availability),
    )
