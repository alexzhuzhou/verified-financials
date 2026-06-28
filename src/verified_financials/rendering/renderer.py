"""Jinja2 rendering of the engine DTOs into styled, print-to-PDF HTML."""

from __future__ import annotations

import base64
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape


def _brand_logo_data_uri() -> str:
    """The Red Lion wordmark as an inline data URI so rendered/printed/downloaded
    HTML is self-contained (no external image fetch)."""
    path = Path(__file__).parent / "assets" / "wordmark.png"
    try:
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
    except OSError:
        return ""


def _money(value, dp: int = 2) -> str:
    if value in (None, ""):
        return "—"
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.{dp}f}"


def _ratio(value) -> str:
    try:
        return f"{Decimal(str(value)):.2f}x"
    except (InvalidOperation, ValueError):
        return str(value)


def _pct(value, dp: int = 1) -> str:
    try:
        return f"{Decimal(str(value)) * 100:.{dp}f}%"
    except (InvalidOperation, ValueError):
        return str(value)


def _build_env() -> Environment:
    env = Environment(
        loader=PackageLoader("verified_financials.rendering", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["money"] = _money
    env.filters["ratio"] = _ratio
    env.filters["pct"] = _pct
    env.globals["brand_logo"] = _brand_logo_data_uri()
    return env


_ENV = _build_env()


def render_certificate(cert: dict) -> str:
    return _ENV.get_template("borrowing_base_certificate.html").render(c=cert)


def render_verification(report: dict) -> str:
    return _ENV.get_template("verification_report.html").render(r=report)


def render_fccr(report: dict) -> str:
    # precompute trend bar widths (max ratio -> 100%) for a print-friendly chart
    trend = report.get("trend", [])
    ratios = [Decimal(str(p["fccr"])) for p in trend] or [Decimal("1")]
    hi = max(ratios) * Decimal("1.05")
    bars = []
    for p in trend:
        r = Decimal(str(p["fccr"]))
        bars.append({"quarter": p["quarter"], "fccr": p["fccr"], "pct": float(r / hi * 100)})
    covenant = Decimal(str(report["covenant"]))
    cov_pct = float(covenant / hi * 100)
    return _ENV.get_template("fccr_report.html").render(r=report, bars=bars, cov_pct=cov_pct)


def render_cashflow(forecast: dict) -> str:
    # precompute closing-cash bar widths (handles negative closings via a shared
    # baseline) and the floor marker, for a print-friendly chart.
    positions = forecast.get("positions", [])
    floor = Decimal(str(forecast["cash_floor"]))
    closings = [Decimal(str(p["closing"])) for p in positions] or [Decimal("0")]
    lo = min(closings + [floor, Decimal("0")])
    hi = max(closings + [floor]) or Decimal("1")
    span = (hi - lo) or Decimal("1")
    bars = [
        {
            "week": p["week"],
            "week_start": p["week_start"],
            "closing": p["closing"],
            "pct": float((Decimal(str(p["closing"])) - lo) / span * 100),
            "below": p["below_floor"],
        }
        for p in positions
    ]
    floor_pct = float((floor - lo) / span * 100)
    return _ENV.get_template("cashflow_forecast.html").render(
        cf=forecast, bars=bars, floor_pct=floor_pct
    )
