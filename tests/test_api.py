"""API smoke tests over the FastAPI service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from verified_financials.api.app import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_config_exposes_rules():
    cfg = client.get("/config").json()
    assert cfg["facility"]["commitment"] == "40000000"
    assert cfg["borrowing_base"]["accounts_receivable"]["advance_rate"] == "0.85"


def test_pipeline_run_and_fetch():
    resp = client.post("/pipeline/run", params={"generate": "true"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    bb = client.get(f"/runs/{run_id}/borrowing-base")
    assert bb.status_code == 200
    assert bb.json()["excess_availability"] == "5327500.00"

    fccr = client.get(f"/runs/{run_id}/fccr")
    assert fccr.json()["fccr"] == "1.20"
    assert fccr.json()["early_warning"] is True

    ver = client.get(f"/runs/{run_id}/verification")
    assert ver.json()["failed"] == 3

    html = client.get(f"/runs/{run_id}/borrowing-base.html")
    assert "text/html" in html.headers["content-type"]
    assert "Borrowing Base Certificate" in html.text

    facts = client.get("/facts", params={"scenario": "baseline", "dataset": "ar_aging", "metric": "total"})
    assert len(facts.json()) == 16


def test_unknown_run_404():
    assert client.get("/runs/does-not-exist/fccr").status_code == 404


def test_scenarios():
    ids = {s["id"] for s in client.get("/scenarios").json()}
    assert ids == {"baseline", "stress"}


def test_config_scenario_aware():
    baseline = client.get("/config", params={"scenario": "baseline"}).json()
    stress = client.get("/config", params={"scenario": "stress"}).json()
    assert baseline["fccr"]["springing"]["enabled"] is False
    assert stress["fccr"]["springing"]["enabled"] is True
    assert stress["borrowing_base"]["inventory"]["valuation"] == "nolv"


def test_facts_scenario_aware():
    facts = client.get("/facts", params={"scenario": "stress", "dataset": "ar_aging", "metric": "total"}).json()
    names = {f["entity"] for f in facts}
    assert "Sunset Diners Group" in names  # the cross-aged obligor only exists in stress


def test_compute_stress_breach():
    resp = client.post("/compute", json={"scenario": "stress", "config_overrides": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["fccr"]["fccr"] == "0.89"
    assert body["fccr"]["covenant_active"] is True
    assert body["borrowing_base"]["excess_availability"] == "1750000.00"


def test_compute_what_if():
    from verified_financials import datagen

    datagen.generate()  # ensure baseline data exists
    resp = client.post(
        "/compute",
        json={
            "scenario": "baseline",
            "config_overrides": {
                "borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}
            },
        },
    )
    assert resp.status_code == 200
    ar = resp.json()["borrowing_base"]["accounts_receivable"]
    assert ar["availability"] == "19935000.00"  # 22.15M x 90%

