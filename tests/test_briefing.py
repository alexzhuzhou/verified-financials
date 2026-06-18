"""AI briefing + ask-the-data — context builder and the no-key fallback path.

Real OpenAI calls are never made here; the fallback path is forced by clearing
OPENAI_API_KEY, so the suite runs deterministically without a key.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from verified_financials.ai import briefing as ai_briefing
from verified_financials.api.app import app
from verified_financials.pipeline import compute_with_overrides, load_scenario

client = TestClient(app)


def _baseline_result():
    base = load_scenario("baseline")
    return compute_with_overrides({}, base_config=base, data_dir=base.settings.data_dir)


def test_build_context_has_headline_numbers():
    ctx = ai_briefing.build_context(_baseline_result())
    assert ctx["borrowing_base"]["excess_availability"] == "5327500.00"
    assert ctx["fccr"]["fccr"] == "1.20"
    assert ctx["verification"]["failed"] == 3
    assert len(ctx["borrowing_base"]["accounts_receivable"]["ineligibles"]) == 3


def test_fallback_briefing_cites_figures(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    text, generated_by = ai_briefing.generate_briefing(ai_briefing.build_context(_baseline_result()))
    assert generated_by == "fallback"
    assert "$27,327,500" in text          # borrowing base
    assert "$5,327,500" in text           # excess availability
    assert "1.20x" in text                # FCCR


def test_briefing_endpoint_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post("/briefing", json={"scenario": "baseline"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["generated_by"] == "fallback"
    assert "Borrowing capacity" in body["briefing"]


def test_ask_endpoint_fallback_streams_message(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post("/ask", json={"scenario": "baseline", "question": "why is availability low?"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "OPENAI_API_KEY" in resp.text   # the no-key message names the env var
    assert "[DONE]" in resp.text
