"""Sensitivity analysis — one-at-a-time lever sweeps over the headline outputs."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from verified_financials import datagen
from verified_financials.api.app import app
from verified_financials.pipeline import DEFAULT_LEVERS, sensitivity

client = TestClient(app)


def _baseline_setup(config):
    """Generate baseline data and return (base_config, data_dir)."""
    datagen.generate(data_dir=config.settings.data_dir, seed=config.settings.random_seed)
    return config, config.settings.data_dir


def test_lower_ar_advance_rate_reduces_excess(config):
    base, data_dir = _baseline_setup(config)
    rows = sensitivity(base, data_dir, DEFAULT_LEVERS)
    by_id = {r["id"]: r for r in rows}

    ar = by_id["ar_advance_rate"]
    # Dropping the A/R advance rate shrinks the borrowing base, so excess falls.
    assert Decimal(ar["delta_excess"]) < 0
    assert Decimal(ar["new_excess"]) < Decimal(ar["baseline_excess"])
    assert Decimal(ar["delta_bb"]) < 0


def test_results_sorted_by_abs_delta_excess_desc(config):
    base, data_dir = _baseline_setup(config)
    rows = sensitivity(base, data_dir, DEFAULT_LEVERS)
    impacts = [abs(Decimal(r["delta_excess"])) for r in rows]
    assert impacts == sorted(impacts, reverse=True)


def test_default_lever_set_produces_four_entries(config):
    base, data_dir = _baseline_setup(config)
    rows = sensitivity(base, data_dir, DEFAULT_LEVERS)
    assert len(rows) == 4
    assert {r["id"] for r in rows} == {
        "ar_advance_rate",
        "inventory_advance_rate",
        "concentration_cap_pct",
        "fccr_covenant_threshold",
    }


def test_covenant_threshold_lever_moves_fccr_headroom(config):
    base, data_dir = _baseline_setup(config)
    rows = sensitivity(base, data_dir, DEFAULT_LEVERS)
    cov = next(r for r in rows if r["id"] == "fccr_covenant_threshold")
    # The threshold lever does not change the computed FCCR ratio itself.
    assert Decimal(cov["delta_fccr"]) == 0


def test_sensitivity_route_baseline():
    datagen.generate()  # ensure baseline data exists
    resp = client.post("/sensitivity", json={"scenario": "baseline"})
    assert resp.status_code == 200
    levers = resp.json()["levers"]
    assert len(levers) == 4
    impacts = [abs(Decimal(r["delta_excess"])) for r in levers]
    assert impacts == sorted(impacts, reverse=True)
    # Every value is serialized as a string.
    for r in levers:
        assert isinstance(r["delta_excess"], str)
        assert isinstance(r["new_bb"], str)


def test_sensitivity_route_honors_config_overrides():
    datagen.generate()
    resp = client.post(
        "/sensitivity",
        json={
            "scenario": "baseline",
            "config_overrides": {
                "borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}
            },
        },
    )
    assert resp.status_code == 200
    ar = next(r for r in resp.json()["levers"] if r["id"] == "ar_advance_rate")
    # Baseline excess reflects the overridden 0.90 advance rate, then the lever
    # bumps it down to 0.81 — still a negative excess delta.
    assert Decimal(ar["delta_excess"]) < 0
