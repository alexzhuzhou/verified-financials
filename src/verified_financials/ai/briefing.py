"""Executive briefing + ask-the-data, grounded in the computed DTOs.

`build_context` distills the engine results into a compact JSON the model can
reason over; the system prompts force it to answer ONLY from those figures.
Everything degrades to a deterministic, no-LLM fallback when no key is set.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from ..pipeline import PipelineResult
from . import llm

SYSTEM_BRIEFING = (
    "You are a credit analyst at Red Lion Advisory writing for a lending client. "
    "You are given the computed results of a borrowing-base and covenant analysis as JSON. "
    "Use ONLY the figures in that JSON — never invent or estimate numbers. Cite the exact "
    "dollar amounts and ratios. Be concise and concrete. Output Markdown."
)

SYSTEM_QA = (
    "You are a credit analyst at Red Lion Advisory. You are given the computed results of a "
    "borrowing-base and covenant analysis as JSON, then a question. Answer using ONLY the figures "
    "in that JSON — never invent numbers. If the answer is not derivable from the data, say so "
    "plainly. Be concise and cite the relevant figures."
)


def _money(s) -> str:
    try:
        n = float(s)
    except (TypeError, ValueError):
        return str(s)
    return f"{'-' if n < 0 else ''}${abs(n):,.0f}"


# --------------------------------------------------------------------------- #
# Grounding context
# --------------------------------------------------------------------------- #
def build_context(result: PipelineResult, sensitivity: list | None = None) -> dict:
    """Compact, authoritative JSON of the headline numbers for the model to ground on."""
    v, c, f = result.verification, result.certificate, result.fccr
    ar, inv = c.accounts_receivable, c.inventory
    return {
        "borrower": c.borrower,
        "as_of": str(c.as_of_date),
        "facility": {"commitment": str(c.commitment), "outstanding": str(c.outstanding)},
        "verification": {
            "passed": v.passed,
            "failed": v.failed,
            "exceptions": [
                {
                    "check": fnd.label,
                    "left": str(fnd.left.value),
                    "right": str(fnd.right.value),
                    "delta": str(fnd.delta),
                    "severity": fnd.severity,
                    "left_source": f"{fnd.left.source_file} {fnd.left.source_locator}",
                    "right_source": f"{fnd.right.source_file} {fnd.right.source_locator}",
                }
                for fnd in v.findings
                if fnd.status == "fail"
            ],
        },
        "borrowing_base": {
            "gross_availability": str(c.gross_availability),
            "borrowing_base": str(c.borrowing_base),
            "excess_availability": str(c.excess_availability),
            "binding_constraint": c.binding_constraint,
            "reserves_total": str(c.reserves_total),
            "accounts_receivable": {
                "gross": str(ar.gross),
                "eligible": str(ar.eligible),
                "advance_rate": str(ar.advance_rate),
                "availability": str(ar.availability),
                "ineligibles": [{"label": line.label, "amount": str(line.amount)} for line in ar.ineligibles],
                "concentration": [
                    {"customer": cl.customer, "excess_excluded": str(cl.excess_excluded)} for cl in ar.concentration
                ],
            },
            "inventory": {
                "gross": str(inv.gross),
                "eligible": str(inv.eligible),
                "valuation_basis": inv.valuation_basis,
                "advance_rate": str(inv.advance_rate),
                "availability": str(inv.availability),
            },
        },
        "fccr": {
            "fccr": str(f.fccr),
            "covenant": str(f.covenant),
            "in_compliance": f.in_compliance,
            "headroom_abs": str(f.headroom_abs),
            "headroom_pct": str(f.headroom_pct),
            "ebitda_cushion": str(f.ebitda_cushion),
            "numerator": str(f.numerator),
            "denominator": str(f.denominator),
            "trend": [{"quarter": p.quarter, "fccr": str(p.fccr)} for p in f.trend],
            "early_warning": f.early_warning,
            "warning_reasons": f.warning_reasons,
            "springing_enabled": f.springing_enabled,
            "covenant_active": f.covenant_active,
            "equity_cure_needed": str(f.equity_cure_needed),
        },
        "sensitivity": sensitivity or [],
    }


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def generate_briefing(context: dict) -> tuple[str, str]:
    """Return (markdown, generated_by) where generated_by is 'ai' or 'fallback'."""
    if llm.is_enabled():
        try:
            text = llm.chat(
                [
                    {"role": "system", "content": SYSTEM_BRIEFING},
                    {
                        "role": "user",
                        "content": (
                            "Computed analysis (JSON):\n"
                            + json.dumps(context, indent=2)
                            + "\n\nWrite a ~200-word executive briefing in Markdown with three short sections: "
                            "**Data trust** (the verification exceptions), **Borrowing capacity** (the borrowing "
                            "base and how much room remains), and **Covenant health** (the FCCR vs covenant, the "
                            "trend, and any early warning). Cite the dollar figures and ratios."
                        ),
                    },
                ]
            )
            if text.strip():
                return text, "ai"
        except Exception:  # network/key/model issues → never break the demo
            pass
    return _fallback_briefing(context), "fallback"


def answer_question_stream(context: dict, question: str) -> Iterator[str]:
    if not llm.is_enabled():
        yield (
            "AI Q&A is unavailable because no OPENAI_API_KEY is configured. Set the key (and "
            "optionally OPENAI_MODEL) to enable it — the executive briefing above still works without it."
        )
        return
    try:
        yield from llm.chat_stream(
            [
                {"role": "system", "content": SYSTEM_QA},
                {
                    "role": "user",
                    "content": (
                        "Computed analysis (JSON):\n"
                        + json.dumps(context, indent=2)
                        + f"\n\nQuestion: {question}"
                    ),
                },
            ]
        )
    except Exception as exc:  # surface gracefully mid-stream
        yield f"\n\n_[AI request failed: {exc}. Check the API key/model and try again.]_"


def _fallback_briefing(ctx: dict) -> str:
    """Deterministic memo from the numbers — no LLM, always available."""
    bb, f, v, fac = ctx["borrowing_base"], ctx["fccr"], ctx["verification"], ctx["facility"]
    out: list[str] = [
        f"## Executive Briefing — {ctx['borrower']}",
        f"*As of {ctx['as_of']}. Rule-generated summary — set `OPENAI_API_KEY` for the AI-written version.*",
        "",
        "### Data trust",
    ]
    if v["failed"]:
        out.append(
            f"**{v['failed']} reconciliation exception(s)** across the submitted files "
            f"({v['passed']} checks passed) — resolve before relying on the figures:"
        )
        for e in v["exceptions"]:
            out.append(f"- {e['check']}: {_money(e['left'])} vs {_money(e['right'])} (Δ {_money(e['delta'])}).")
    else:
        out.append(f"All {v['passed']} tie-out checks passed — the figures reconcile across files.")

    out += [
        "",
        "### Borrowing capacity",
        f"After eligibility rules, the borrowing base is **{_money(bb['borrowing_base'])}** against a "
        f"{_money(fac['commitment'])} revolver; with {_money(fac['outstanding'])} drawn, "
        f"**{_money(bb['excess_availability'])}** of availability remains "
        f"(binding constraint: {bb['binding_constraint'].replace('_', ' ')}).",
        "",
        "### Covenant health",
    ]
    status = "in compliance" if f["in_compliance"] else "in breach"
    out.append(
        f"FCCR (TTM) is **{f['fccr']}x** versus the {f['covenant']}x covenant — {status}, with "
        f"{_money(f['ebitda_cushion'])} of EBITDA cushion before a breach."
    )
    if f["early_warning"]:
        out.append("Early warning: " + "; ".join(f["warning_reasons"]) + ".")
    try:
        cure = float(f["equity_cure_needed"])
    except (TypeError, ValueError):
        cure = 0.0
    if not f["in_compliance"] and cure > 0:
        out.append(f"An equity cure of **{_money(f['equity_cure_needed'])}** would restore compliance.")
    return "\n".join(out)
