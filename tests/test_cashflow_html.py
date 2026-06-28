"""Live, downloadable cash-flow forecast (POST /compute/cashflow + .html)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from verified_financials.api.app import app

client = TestClient(app)


def test_cashflow_json_baseline():
    resp = client.post("/compute/cashflow", json={"scenario": "baseline", "config_overrides": {}})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["available"] is True
    f = body["forecast"]
    assert len(f["positions"]) == 13
    assert f["kpis"]["weeks_below_floor"] == 0


def test_cashflow_json_unavailable_for_upload():
    resp = client.post("/compute/cashflow", json={"upload_id": "missing", "config_overrides": {}})
    assert resp.status_code == 200, resp.text
    assert resp.json()["available"] is False


def test_cashflow_html_stress_shows_alert():
    resp = client.post("/compute/cashflow.html", json={"scenario": "stress", "config_overrides": {}})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    html = resp.text
    assert "13-Week Cash Flow Forecast" in html
    assert "Red Lion Advisory" in html              # bank-ready letterhead
    assert "LIQUIDITY ALERT" in html                # stress breaches the floor


def test_cashflow_html_reflects_override():
    """Raising the cash floor must flip the baseline into an alert state."""
    resp = client.post(
        "/compute/cashflow.html",
        json={"scenario": "baseline", "config_overrides": {"cash_flow": {"cash_floor": "2000000"}}},
    )
    assert resp.status_code == 200, resp.text
    assert "LIQUIDITY ALERT" in resp.text
