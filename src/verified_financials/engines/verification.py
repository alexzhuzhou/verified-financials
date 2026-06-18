"""Verification / tie-out engine.

Runs every check in ``config.verification.checks``. A check names two fact
references (e.g. ``balance_sheet.inventory`` and ``trial_balance.inventory``);
the engine resolves both — including aggregate references like
``ar_aging.total_sum`` — compares them within tolerance, and emits a Finding
carrying BOTH sides' provenance so a reviewer can see exactly which figures
disagree and where they came from.
"""

from __future__ import annotations

from decimal import Decimal

from ..config.schema import Config
from ..models.verification import FactRef, Finding, VerificationReport
from ..store.repository import FactRepository

ZERO = Decimal("0")


def _fmt_money(v: Decimal) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"


# --------------------------------------------------------------------------- #
# Aggregate references
# --------------------------------------------------------------------------- #
def _agg_ar_total_sum(repo: FactRepository) -> FactRef:
    facts = repo.query(dataset="ar_aging", metric="total")
    total = sum((f.value for f in facts), ZERO)
    p = facts[0].provenance
    return FactRef(
        ref="ar_aging.total_sum",
        value=total,
        source_file=p.source_file,
        source_locator=f"sum of {len(facts)} customer rows",
        as_of_date=p.as_of_date,
    )


def _agg_tb_side(repo: FactRepository, side: str, ref: str) -> FactRef:
    facts = repo.query(dataset="trial_balance")
    total = sum((Decimal(f.attributes[side]) for f in facts), ZERO)
    p = facts[0].provenance
    return FactRef(
        ref=ref,
        value=total,
        source_file=p.source_file,
        source_locator=f"sum of {side} column ({len(facts)} accounts)",
        as_of_date=p.as_of_date,
    )


_AGGREGATES = {
    "ar_aging.total_sum": _agg_ar_total_sum,
    "trial_balance.total_debits": lambda r: _agg_tb_side(r, "debit", "trial_balance.total_debits"),
    "trial_balance.total_credits": lambda r: _agg_tb_side(r, "credit", "trial_balance.total_credits"),
}


def resolve(repo: FactRepository, ref: str) -> FactRef:
    if ref in _AGGREGATES:
        return _AGGREGATES[ref](repo)
    dataset, _, metric = ref.partition(".")
    fact = repo.get_fact(dataset, metric)
    if fact is None:
        raise KeyError(f"could not resolve fact reference: {ref}")
    p = fact.provenance
    return FactRef(
        ref=ref,
        value=fact.value,
        source_file=p.source_file,
        source_locator=p.source_locator,
        as_of_date=p.as_of_date,
        version_tag=p.version_tag,
    )


def run_verification(repo: FactRepository, config: Config, run_id: str) -> VerificationReport:
    findings: list[Finding] = []
    for check in config.verification.checks:
        left = resolve(repo, check.left)
        right = resolve(repo, check.right)
        delta = left.value - right.value
        failed = abs(delta) > check.tolerance_abs
        if failed:
            extra = ""
            if left.version_tag and right.version_tag and left.version_tag != right.version_tag:
                extra = f" — '{left.version_tag}' vs '{right.version_tag}'"
            message = (
                f"{_fmt_money(abs(delta))} discrepancy: "
                f"{check.left} = {_fmt_money(left.value)} vs "
                f"{check.right} = {_fmt_money(right.value)}{extra}"
            )
        else:
            message = f"Ties out within tolerance (Δ {_fmt_money(delta)})"
        findings.append(
            Finding(
                check_id=check.id,
                label=check.label,
                status="fail" if failed else "pass",
                severity=check.severity,
                left=left,
                right=right,
                delta=delta,
                tolerance_abs=check.tolerance_abs,
                message=message,
            )
        )

    passed = sum(1 for f in findings if f.status == "pass")
    return VerificationReport(
        run_id=run_id,
        as_of_date=config.facility.as_of_date,
        findings=findings,
        passed=passed,
        failed=len(findings) - passed,
    )
