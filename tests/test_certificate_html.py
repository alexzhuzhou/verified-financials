"""Live, downloadable borrowing-base certificate (POST /compute/certificate.html)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from verified_financials.api.app import app

client = TestClient(app)


def test_certificate_html_baseline():
    resp = client.post("/compute/certificate.html", json={"scenario": "baseline", "config_overrides": {}})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    html = resp.text
    assert "Borrowing Base Certificate" in html
    assert "Red Lion Advisory" in html            # bank-ready letterhead
    assert "$27,327,500" in html                   # borrowing base
    assert "$5,327,500" in html                    # excess availability
    assert "Responsible Officer" in html           # signature block


def test_certificate_html_reflects_override():
    """Raising the A/R advance rate must change the rendered availability."""
    resp = client.post(
        "/compute/certificate.html",
        json={
            "scenario": "baseline",
            "config_overrides": {"borrowing_base": {"accounts_receivable": {"advance_rate": "0.90"}}},
        },
    )
    assert resp.status_code == 200, resp.text
    # 22,150,000 eligible A/R × 90% = 19,935,000 (vs the 18,827,500 baseline)
    assert "$19,935,000" in resp.text


def test_certificate_html_stress_scenario():
    resp = client.post("/compute/certificate.html", json={"scenario": "stress", "config_overrides": {}})
    assert resp.status_code == 200, resp.text
    assert "$19,750,000" in resp.text              # stress borrowing base
