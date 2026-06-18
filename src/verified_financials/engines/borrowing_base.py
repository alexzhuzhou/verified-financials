"""Borrowing base engine — the hero.

Implements the standard ABL waterfall:

  Phase 1  Remove categorical ineligibles (aged buckets, foreign-uninsured,
           intercompany, optional cross-aging) per obligor. Each dollar is
           excluded by at most one reason (we only ever exclude the *remaining*
           balance), so there is no double counting.
  Phase 2  Apply the single-obligor concentration cap against the FIXED
           pre-concentration base (breaks the cap's circularity); exclude only
           the EXCESS above the cap.

Then roll up A/R + inventory availability, subtract reserves, apply the
commitment cap, and net out outstanding loans + L/C exposure.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..config.loader import config_hash
from ..config.schema import Config
from ..models.borrowing_base import (
    AssetClassResult,
    BorrowingBaseCertificate,
    ConcentrationLine,
    IneligibleContribution,
    IneligibleLine,
    NolvLine,
)
from ..models.fact import Fact
from ..store.repository import FactRepository
from .predicate import evaluate

CENT = Decimal("0.01")
ZERO = Decimal("0")


def _money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _dec(v) -> Decimal:
    return Decimal(str(v))


def _predicate_attrs(fact: Fact) -> dict:
    """Attribute view a predicate sees (coerce numeric strings to Decimal)."""
    attrs = dict(fact.attributes)
    attrs["total"] = fact.value
    return attrs


# --------------------------------------------------------------------------- #
# Accounts receivable
# --------------------------------------------------------------------------- #
def _compute_ar(repo: FactRepository, config: Config) -> AssetClassResult:
    ar_cfg = config.borrowing_base.accounts_receivable
    facts = repo.query(dataset="ar_aging", metric="total")
    gross = sum((f.value for f in facts), ZERO)

    # Accumulators keyed by rule id -> contributions
    lines: dict[str, IneligibleLine] = {}
    for rule in ar_cfg.ineligible_rules:
        lines[rule.id] = IneligibleLine(
            rule_id=rule.id, label=rule.label, citation=rule.citation, amount=ZERO
        )
    cross_line: IneligibleLine | None = None
    if ar_cfg.cross_aging.enabled:
        cross_line = IneligibleLine(
            rule_id="ar_cross_aging",
            label="Cross-aged obligors (majority past due)",
            citation=ar_cfg.cross_aging.citation,
            amount=ZERO,
        )

    base_by_customer: dict[str, Decimal] = {}

    for fact in facts:
        total = fact.value
        attrs = _predicate_attrs(fact)
        excluded = ZERO

        for rule in ar_cfg.ineligible_rules:
            remaining = total - excluded
            if remaining <= 0:
                break
            if rule.type == "aged_bucket":
                raw = _dec(attrs.get(rule.bucket_field, "0"))
            elif rule.type == "predicate":
                raw = total if evaluate(rule.predicate, attrs) else ZERO
            else:  # pragma: no cover - schema constrains type
                raw = ZERO
            take = min(raw, remaining)
            if take > 0:
                excluded += take
                lines[rule.id].amount += take
                lines[rule.id].detail.append(
                    IneligibleContribution(entity=fact.entity, amount=take, fact_id=fact.id)
                )

        # Optional cross-aging taint: whole remaining balance if majority past due.
        if cross_line is not None and total > 0:
            past_due = total - _dec(attrs.get("current", "0"))
            if past_due / total > ar_cfg.cross_aging.threshold_pct:
                take = total - excluded
                if take > 0:
                    excluded += take
                    cross_line.amount += take
                    cross_line.detail.append(
                        IneligibleContribution(
                            entity=fact.entity, amount=take, fact_id=fact.id,
                            note="majority of balance past due",
                        )
                    )

        base_by_customer[fact.entity] = total - excluded

    pre_concentration_base = sum(base_by_customer.values(), ZERO)

    # Phase 2: concentration cap against the fixed base.
    cap_pct = ar_cfg.concentration_cap.pct
    cap_basis_value = gross if ar_cfg.concentration_cap.basis == "gross" else pre_concentration_base
    cap_amount = cap_pct * cap_basis_value
    concentration: list[ConcentrationLine] = []
    total_excess = ZERO
    for fact in facts:
        base_c = base_by_customer[fact.entity]
        excess = base_c - cap_amount
        if excess > 0:
            total_excess += excess
            concentration.append(
                ConcentrationLine(
                    customer=fact.entity,
                    balance_in_base=_money(base_c),
                    cap_amount=_money(cap_amount),
                    excess_excluded=_money(excess),
                    pct_of_base=(base_c / pre_concentration_base).quantize(Decimal("0.0001"))
                    if pre_concentration_base
                    else ZERO,
                    pct_of_gross=(fact.value / gross).quantize(Decimal("0.0001"))
                    if gross
                    else ZERO,
                )
            )

    eligible = pre_concentration_base - total_excess
    advance_rate = ar_cfg.advance_rate
    availability = _money(eligible * advance_rate)

    ineligibles = [lines[r.id] for r in ar_cfg.ineligible_rules]
    if cross_line is not None and cross_line.amount > 0:
        ineligibles.append(cross_line)
    # quantize line amounts
    for line in ineligibles:
        line.amount = _money(line.amount)
        for c in line.detail:
            c.amount = _money(c.amount)

    return AssetClassResult(
        asset_class="accounts_receivable",
        gross=_money(gross),
        ineligibles=ineligibles,
        concentration=concentration,
        total_ineligible=_money(gross - eligible),
        eligible=_money(eligible),
        advance_rate=advance_rate,
        availability=availability,
    )


# --------------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------------- #
def _compute_inventory(repo: FactRepository, config: Config) -> AssetClassResult:
    inv_cfg = config.borrowing_base.inventory
    facts = repo.query(dataset="inventory", metric="value")
    gross = sum((f.value for f in facts), ZERO)

    lines: dict[str, IneligibleLine] = {
        rule.id: IneligibleLine(
            rule_id=rule.id, label=rule.label, citation=rule.citation, amount=ZERO
        )
        for rule in inv_cfg.ineligible_rules
    }

    total_excluded = ZERO
    eligible_by_category: dict[str, Decimal] = {}
    for fact in facts:
        value = fact.value
        attrs = _predicate_attrs(fact)
        excluded = ZERO
        for rule in inv_cfg.ineligible_rules:
            remaining = value - excluded
            if remaining <= 0:
                break
            raw = value if (rule.type == "predicate" and evaluate(rule.predicate, attrs)) else ZERO
            take = min(raw, remaining)
            if take > 0:
                excluded += take
                lines[rule.id].amount += take
                lines[rule.id].detail.append(
                    IneligibleContribution(entity=fact.entity, amount=take, fact_id=fact.id)
                )
        total_excluded += excluded
        category = str(attrs.get("category", "Uncategorized"))
        eligible_by_category[category] = eligible_by_category.get(category, ZERO) + (value - excluded)

    eligible = gross - total_excluded
    advance_rate = inv_cfg.advance_rate

    nolv_detail: list[NolvLine] = []
    eligible_nolv_value: Decimal | None = None
    if inv_cfg.valuation == "nolv":
        nolv_total = ZERO
        for category in sorted(eligible_by_category):
            cost = eligible_by_category[category]
            ratio = inv_cfg.nolv_by_category.get(category, Decimal("1"))
            nolv_value = min(cost, ratio * cost)
            nolv_total += nolv_value
            nolv_detail.append(
                NolvLine(
                    category=category,
                    cost=_money(cost),
                    nolv_ratio=ratio,
                    nolv_value=_money(nolv_value),
                )
            )
        eligible_nolv_value = nolv_total
        availability = _money(nolv_total * advance_rate)
    else:
        availability = _money(eligible * advance_rate)

    ineligibles = [lines[r.id] for r in inv_cfg.ineligible_rules]
    for line in ineligibles:
        line.amount = _money(line.amount)
        for c in line.detail:
            c.amount = _money(c.amount)

    return AssetClassResult(
        asset_class="inventory",
        gross=_money(gross),
        ineligibles=ineligibles,
        concentration=[],
        total_ineligible=_money(total_excluded),
        eligible=_money(eligible),
        valuation_basis=inv_cfg.valuation,
        nolv_detail=nolv_detail,
        eligible_nolv_value=_money(eligible_nolv_value) if eligible_nolv_value is not None else None,
        advance_rate=advance_rate,
        availability=availability,
    )


# --------------------------------------------------------------------------- #
# Reserves
# --------------------------------------------------------------------------- #
def _compute_reserves(config: Config, eligible_ar: Decimal) -> tuple[list[dict], Decimal]:
    detail: list[dict] = []
    total = ZERO
    for r in config.borrowing_base.reserves:
        if r.type == "dilution":
            dp = r.dilution_pct or ZERO
            tp = r.threshold_pct or ZERO
            amount = max(ZERO, dp - tp) * eligible_ar
        else:  # fixed | priority_payable | rent
            amount = r.amount
        amount = _money(amount)
        total += amount
        detail.append(
            {
                "id": r.id,
                "label": r.label,
                "type": r.type,
                "amount": str(amount),
                "citation": r.citation,
            }
        )
    return detail, total


# --------------------------------------------------------------------------- #
# Roll-up
# --------------------------------------------------------------------------- #
def compute_borrowing_base(
    repo: FactRepository, config: Config, run_id: str
) -> BorrowingBaseCertificate:
    ar = _compute_ar(repo, config)
    inv = _compute_inventory(repo, config)
    fac = config.facility

    gross_availability = ar.availability + inv.availability
    reserve_detail, reserves_total = _compute_reserves(config, ar.eligible)
    net_after_reserves = gross_availability - reserves_total
    borrowing_base = min(net_after_reserves, fac.commitment)
    binding = "commitment" if fac.commitment < net_after_reserves else "borrowing_base"
    suppressed = max(ZERO, net_after_reserves - fac.commitment)
    excess_availability = borrowing_base - fac.outstanding - fac.lc_exposure

    return BorrowingBaseCertificate(
        run_id=run_id,
        as_of_date=fac.as_of_date,
        borrower=fac.borrower,
        lender=fac.lender,
        agent=fac.agent,
        facility_name=fac.name,
        agreement_reference=fac.agreement_reference,
        config_hash=config_hash(config),
        accounts_receivable=ar,
        inventory=inv,
        gross_availability=_money(gross_availability),
        reserves_total=_money(reserves_total),
        reserve_detail=reserve_detail,
        borrowing_base=_money(borrowing_base),
        commitment=_money(fac.commitment),
        binding_constraint=binding,
        suppressed_availability=_money(suppressed),
        outstanding=_money(fac.outstanding),
        lc_exposure=_money(fac.lc_exposure),
        excess_availability=_money(excess_availability),
    )
