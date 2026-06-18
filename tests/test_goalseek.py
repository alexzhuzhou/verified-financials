"""Goal-seek — reverse-solve a single lever for a target excess availability."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from verified_financials import datagen
from verified_financials.api.app import app
from verified_financials.pipeline import _read_path, goal_seek

client = TestClient(app)

_AR_PATH = ["borrowing_base", "accounts_receivable", "advance_rate"]


def _baseline_setup(config):
    """Generate baseline data and return (base_config, data_dir)."""
    datagen.generate(data_dir=config.settings.data_dir, seed=config.settings.random_seed)
    return config, config.settings.data_dir


def test_modest_target_above_current_is_reachable(config):
    base, data_dir = _baseline_setup(config)
    current = _read_path(base, _AR_PATH)

    base_excess = Decimal(goal_seek(base, data_dir, "ar_advance_rate", current)["baseline_excess"])
    # Ask for a target comfortably above the current excess (but below the cap).
    target = base_excess + Decimal("500000")

    res = goal_seek(base, data_dir, "ar_advance_rate", target)
    assert res["reachable"] is True
    solved = Decimal(res["solved_value"])
    # Need a HIGHER advance rate (more collateral) than today to lift excess.
    assert current < solved <= Decimal("1")
    # The solved value actually clears the target.
    assert Decimal(res["achieved_excess"]) >= target
    # Baseline reflects the unsolved current state.
    assert Decimal(res["baseline_value"]) == current
    assert Decimal(res["baseline_excess"]) == base_excess


def test_absurd_target_is_unreachable(config):
    base, data_dir = _baseline_setup(config)
    res = goal_seek(base, data_dir, "ar_advance_rate", Decimal("999999999"))
    assert res["reachable"] is False
    # Clamped to the top of the domain.
    assert Decimal(res["solved_value"]) == Decimal("1")
    # The best we can do is reported as achieved (less than the target).
    assert Decimal(res["achieved_excess"]) < Decimal("999999999")


def test_target_below_current_lowers_the_lever(config):
    base, data_dir = _baseline_setup(config)
    current = _read_path(base, _AR_PATH)
    base_excess = Decimal(goal_seek(base, data_dir, "ar_advance_rate", current)["baseline_excess"])
    # Lowering the target below today's excess should solve to a SMALLER rate.
    res = goal_seek(base, data_dir, "ar_advance_rate", base_excess - Decimal("1000000"))
    assert res["reachable"] is True
    assert Decimal(res["solved_value"]) < current


def test_target_at_or_below_floor_solves_at_zero(config):
    base, data_dir = _baseline_setup(config)
    # f(0) is deeply negative here; any target at/under it is already met at 0.
    res = goal_seek(base, data_dir, "ar_advance_rate", Decimal("-999999999"))
    assert res["reachable"] is True
    assert res["solved_value"] == "0.0000"
    assert Decimal(res["achieved_excess"]) >= Decimal("-999999999")


def test_unknown_lever_raises(config):
    base, data_dir = _baseline_setup(config)
    try:
        goal_seek(base, data_dir, "not_a_lever", Decimal("1"))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for unknown lever")


def test_goal_seek_route_baseline():
    datagen.generate()  # ensure baseline data exists
    resp = client.post(
        "/goal-seek",
        json={"scenario": "baseline", "lever": "ar_advance_rate", "target_value": "6000000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lever"] == "ar_advance_rate"
    assert body["label"] == "A/R advance rate"
    assert body["reachable"] is True
    # Every number serialized as a Decimal string.
    for key in ("target", "solved_value", "achieved_excess", "baseline_value", "baseline_excess"):
        assert isinstance(body[key], str)
    assert Decimal(body["achieved_excess"]) >= Decimal("6000000")


def test_goal_seek_route_honors_config_overrides():
    datagen.generate()
    resp = client.post(
        "/goal-seek",
        json={
            "scenario": "baseline",
            "config_overrides": {
                "borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}
            },
            "lever": "ar_advance_rate",
            "target_value": "1",
        },
    )
    assert resp.status_code == 200
    # The override raised the baseline rate to 0.90 before solving.
    assert Decimal(resp.json()["baseline_value"]) == Decimal("0.90")


def test_goal_seek_route_rejects_unknown_lever():
    datagen.generate()
    resp = client.post(
        "/goal-seek",
        json={"scenario": "baseline", "lever": "bogus", "target_value": "100"},
    )
    assert resp.status_code == 400
