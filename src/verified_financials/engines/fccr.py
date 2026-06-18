"""FCCR covenant engine.

Computes the trailing-twelve-month Fixed Charge Coverage Ratio from
config-driven components (Convention A: taxes & distributions deducted in the
numerator only), compares it to the covenant, measures headroom, reconstructs
the quarterly trend, and raises an early warning *inside* the cushion — before
a breach, not after.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ..config.schema import Config
from ..models.fccr import FccrComponent, FccrReport, QuarterPoint
from ..store.repository import FactRepository

ZERO = Decimal("0")
CENT = Decimal("0.01")
RATIO_Q = Decimal("0.01")
PCT_Q = Decimal("0.0001")


def _quarter_label(d: date) -> str:
    return f"Q{(d.month - 1) // 3 + 1}-{d.year}"


def _component_value(repo: FactRepository, metric: str) -> tuple[Decimal, str | None]:
    fact = repo.get_fact("financials_ttm", metric)
    if fact is None:
        raise KeyError(f"missing FCCR component: financials_ttm.{metric}")
    return fact.value, fact.id


def compute_fccr(
    repo: FactRepository,
    config: Config,
    run_id: str,
    excess_availability: Decimal | None = None,
) -> FccrReport:
    fc = config.fccr
    components: list[FccrComponent] = []

    def side_total(spec, side_name: str) -> Decimal:
        total = ZERO
        for metric in spec.add:
            val, fid = _component_value(repo, metric)
            components.append(
                FccrComponent(name=metric, value=val, fact_id=fid, side=side_name, role="add")
            )
            total += val
        for metric in spec.subtract:
            val, fid = _component_value(repo, metric)
            components.append(
                FccrComponent(name=metric, value=val, fact_id=fid, side=side_name, role="subtract")
            )
            total -= val
        return total

    numerator = side_total(fc.numerator, "numerator")
    denominator = side_total(fc.denominator, "denominator")
    if denominator == 0:
        raise ZeroDivisionError("FCCR denominator (fixed charges) is zero")

    fccr = (numerator / denominator).quantize(RATIO_Q, rounding=ROUND_HALF_UP)
    covenant = fc.covenant_threshold
    in_compliance = fccr >= covenant
    headroom_abs = (fccr - covenant).quantize(RATIO_Q)
    headroom_pct = ((fccr - covenant) / covenant).quantize(PCT_Q)
    ebitda_cushion = (numerator - covenant * denominator).quantize(CENT, rounding=ROUND_HALF_UP)

    # --- trend: prior quarters from facts + the current computed quarter ---
    history = repo.query(dataset="financials_ttm", metric="fccr_history")
    history.sort(key=lambda f: (f.attributes.get("period", ""), f.entity or ""))
    trend = [QuarterPoint(quarter=f.entity, fccr=f.value) for f in history]
    current_q = _quarter_label(config.facility.as_of_date)
    if not trend or trend[-1].quarter != current_q:
        trend.append(QuarterPoint(quarter=current_q, fccr=fccr))

    consecutive_declines = 0
    for i in range(len(trend) - 1, 0, -1):
        if trend[i].fccr < trend[i - 1].fccr:
            consecutive_declines += 1
        else:
            break

    # --- early warning (fires inside the cushion) ---
    warn_band = covenant * (Decimal("1") + fc.early_warning.headroom_pct_warn)
    reasons: list[str] = []
    if fccr < warn_band:
        reasons.append(
            f"Headroom only {headroom_pct * 100:.1f}% above covenant "
            f"(warning band {fc.early_warning.headroom_pct_warn * 100:.0f}%)"
        )
    if consecutive_declines >= fc.early_warning.declining_quarters_warn:
        series = " → ".join(f"{p.fccr:.2f}x" for p in trend)
        reasons.append(
            f"FCCR declined {consecutive_declines} consecutive quarters ({series})"
        )
    early_warning = bool(reasons)

    # --- springing covenant: tested only when availability < trigger ---
    spr = fc.springing
    springing_trigger: Decimal | None = None
    covenant_active = True
    if spr.enabled:
        springing_trigger = (
            max(spr.trigger_pct * config.facility.commitment, spr.trigger_floor)
        ).quantize(CENT)
        # if availability is unknown, conservatively treat the covenant as active
        covenant_active = excess_availability is None or excess_availability < springing_trigger

    # --- equity cure: equity add-back to lift FCCR to exactly the covenant ---
    ec = fc.equity_cure
    equity_cure_needed = max(ZERO, covenant * denominator - numerator).quantize(CENT)
    cures_remaining_year = (ec.max_per_year - ec.cures_used) if ec.enabled else None
    cures_remaining_lifetime = (ec.max_lifetime - ec.cures_used) if ec.enabled else None

    return FccrReport(
        run_id=run_id,
        as_of_date=config.facility.as_of_date,
        components=components,
        numerator=numerator.quantize(CENT),
        denominator=denominator.quantize(CENT),
        fccr=fccr,
        covenant=covenant,
        in_compliance=in_compliance,
        headroom_abs=headroom_abs,
        headroom_pct=headroom_pct,
        ebitda_cushion=ebitda_cushion,
        springing_enabled=spr.enabled,
        covenant_active=covenant_active,
        springing_trigger=springing_trigger,
        excess_availability=excess_availability.quantize(CENT)
        if (spr.enabled and excess_availability is not None)
        else None,
        equity_cure_enabled=ec.enabled,
        equity_cure_needed=equity_cure_needed,
        cures_used=ec.cures_used,
        cures_remaining_year=cures_remaining_year,
        cures_remaining_lifetime=cures_remaining_lifetime,
        trend=trend,
        consecutive_declines=consecutive_declines,
        early_warning=early_warning,
        warning_reasons=reasons,
    )
