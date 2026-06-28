"""Pipeline orchestrator — the single code path shared by the CLI and the API.

ingest CSVs -> fact store -> run the three engines -> persist results ->
optionally render HTML + JSON artifacts.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .config.loader import config_hash, load_config
from .config.schema import Config
from .engines.borrowing_base import compute_borrowing_base
from .engines.cash_flow import compute_cash_flow
from .engines.fccr import compute_fccr
from .engines.verification import run_verification
from .loaders.base import load_all
from .models.borrowing_base import BorrowingBaseCertificate
from .models.cash_flow import CashFlowForecast
from .models.fccr import FccrReport
from .models.verification import VerificationReport
from .rendering import renderer
from .store.db import connect, init_schema
from .store.repository import FactRepository, ResultRepository


@dataclass
class PipelineResult:
    run_id: str
    config: Config
    verification: VerificationReport
    certificate: BorrowingBaseCertificate
    fccr: FccrReport
    fact_count: int
    artifacts: dict[str, str] = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "fact_count": self.fact_count,
            "verification": {
                "passed": self.verification.passed,
                "failed": self.verification.failed,
            },
            "borrowing_base": {
                "gross_availability": str(self.certificate.gross_availability),
                "borrowing_base": str(self.certificate.borrowing_base),
                "excess_availability": str(self.certificate.excess_availability),
            },
            "fccr": {
                "fccr": str(self.fccr.fccr),
                "covenant": str(self.fccr.covenant),
                "in_compliance": self.fccr.in_compliance,
                "early_warning": self.fccr.early_warning,
            },
        }


def new_run_id() -> str:
    return f"run-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


# Named scenarios -> the config file that drives them (its settings carry data_dir, etc.)
SCENARIOS: dict[str, str | None] = {
    "baseline": None,                  # default config.yaml
    "stress": "config_advanced.yaml",
}


def load_scenario(scenario: str) -> Config:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario} (choose from {list(SCENARIOS)})")
    return load_config(SCENARIOS[scenario])


def _deep_merge(base: dict, overrides: dict) -> dict:
    out = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def compute_with_overrides(
    overrides: dict | None,
    base_config: Config | None = None,
    data_dir: str | Path | None = None,
    run_id: str | None = None,
) -> PipelineResult:
    """Recompute with config overrides deep-merged onto a base config, WITHOUT
    persisting or rendering. This is the foundation of the live what-if UI."""
    base_config = base_config or load_config()
    merged = _deep_merge(base_config.model_dump(mode="json"), overrides or {})
    config = Config.model_validate(merged)
    run_id = run_id or new_run_id()

    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    fact_count = ingest(repo, config, data_dir)
    verification, certificate, fccr = run_engines(repo, config, run_id)
    conn.close()
    return PipelineResult(
        run_id=run_id,
        config=config,
        verification=verification,
        certificate=certificate,
        fccr=fccr,
        fact_count=fact_count,
    )


# --------------------------------------------------------------------------- #
# Cash flow — its own data path (the cash-event ledger + paid-history sample),
# parallel to the borrowing-base engines above. Kept separate so a borrowing-base
# compute never requires a cash ledger (and the upload path stays unaffected).
# --------------------------------------------------------------------------- #
def ingest_cash(repo: FactRepository, config: Config, data_dir: str | Path | None = None) -> int:
    """Load the cash-event ledger + paid-history sample into the fact store."""
    from .loaders import cash_events, paid_history

    data_dir = Path(data_dir or config.settings.data_dir)
    loaded_at = datetime.now()
    as_of = config.facility.as_of_date
    facts = cash_events.load(data_dir / "cash_events.csv", as_of, loaded_at)
    facts += paid_history.load(data_dir / "paid_history.csv", as_of, loaded_at)
    return repo.add_many(facts)


def compute_cashflow_with_overrides(
    overrides: dict | None,
    base_config: Config | None = None,
    data_dir: str | Path | None = None,
    run_id: str | None = None,
) -> CashFlowForecast:
    """Recompute the 13-week cash-flow forecast with config overrides deep-merged
    onto a base config — the live what-if path, no persistence (mirrors
    ``compute_with_overrides`` but on the cash-event data path)."""
    base_config = base_config or load_config()
    merged = _deep_merge(base_config.model_dump(mode="json"), overrides or {})
    config = Config.model_validate(merged)
    run_id = run_id or new_run_id()

    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    ingest_cash(repo, config, data_dir)
    forecast = compute_cash_flow(repo, config, run_id)
    conn.close()
    return forecast


# --------------------------------------------------------------------------- #
# Sensitivity analysis — vary one lever at a time, report headline impact.
# --------------------------------------------------------------------------- #
# Levers covering the rules that move forward-looking availability most. Each
# bumps the named value at ``path`` by a relative ``delta_pct`` in its ADVERSE
# direction: rates/caps DOWN (less collateral), the covenant threshold UP
# (stricter test). ``kind`` is metadata for the UI ("rate" vs "amount").
DEFAULT_LEVERS: list[dict] = [
    {
        "id": "ar_advance_rate",
        "label": "A/R advance rate",
        "path": ["borrowing_base", "accounts_receivable", "advance_rate"],
        "kind": "rate",
    },
    {
        "id": "inventory_advance_rate",
        "label": "Inventory advance rate",
        "path": ["borrowing_base", "inventory", "advance_rate"],
        "kind": "rate",
    },
    {
        "id": "concentration_cap_pct",
        "label": "Concentration cap %",
        "path": ["borrowing_base", "accounts_receivable", "concentration_cap", "pct"],
        "kind": "rate",
    },
    {
        "id": "fccr_covenant_threshold",
        "label": "FCCR covenant threshold",
        "path": ["fccr", "covenant_threshold"],
        "kind": "rate",
    },
]

# Levers where the adverse move is an INCREASE (stricter covenant), not a cut.
_UP_LEVERS = {"fccr_covenant_threshold"}


def _read_path(config: Config, path: list[str]) -> Decimal:
    """Read the (Decimal) value at a dotted config path."""
    node: object = config
    for key in path:
        node = getattr(node, key)
    return Decimal(str(node))


def _nest(path: list[str], value: object) -> dict:
    """Build a nested override dict {path[0]: {... : value}}."""
    out: object = value
    for key in reversed(path):
        out = {key: out}
    return out  # type: ignore[return-value]


def sensitivity(
    base_config: Config,
    data_dir: str | Path | None,
    levers: list[dict],
    delta_pct: Decimal | float = 0.1,
) -> list[dict]:
    """One-at-a-time sensitivity on the headline outputs.

    For each lever, apply a relative ``delta_pct`` bump to the value at its
    config ``path`` (DOWN for rates/caps, UP for the covenant threshold), then
    recompute and record the deltas vs the baseline for excess availability,
    borrowing base, and FCCR. Results are sorted by absolute impact on excess
    availability, descending — the order a tornado chart wants.
    """
    delta = Decimal(str(delta_pct))
    levers = levers if levers is not None else DEFAULT_LEVERS

    base = compute_with_overrides({}, base_config=base_config, data_dir=data_dir)
    base_excess = base.certificate.excess_availability
    base_bb = base.certificate.borrowing_base
    base_fccr = base.fccr.fccr

    rows: list[dict] = []
    for lever in levers:
        path = lever["path"]
        current = _read_path(base_config, path)
        direction = Decimal("1") + delta if lever["id"] in _UP_LEVERS else Decimal("1") - delta
        bumped = current * direction
        overrides = _nest(path, str(bumped))

        result = compute_with_overrides(overrides, base_config=base_config, data_dir=data_dir)
        new_excess = result.certificate.excess_availability
        new_bb = result.certificate.borrowing_base
        new_fccr = result.fccr.fccr

        rows.append(
            {
                "id": lever["id"],
                "label": lever["label"],
                "baseline_excess": str(base_excess),
                "new_excess": str(new_excess),
                "delta_excess": str(new_excess - base_excess),
                "baseline_bb": str(base_bb),
                "new_bb": str(new_bb),
                "delta_bb": str(new_bb - base_bb),
                "baseline_fccr": str(base_fccr),
                "new_fccr": str(new_fccr),
                "delta_fccr": str(new_fccr - base_fccr),
            }
        )

    rows.sort(key=lambda r: abs(Decimal(r["delta_excess"])), reverse=True)
    return rows


# --------------------------------------------------------------------------- #
# Goal-seek — reverse-solve a single lever for a target excess availability.
# --------------------------------------------------------------------------- #
# The goal-seekable levers and a friendly label, keyed by id. Paths reuse the
# same config locations as DEFAULT_LEVERS so the forward and reverse solvers
# stay in lock-step.
_GOAL_SEEK_LEVERS: dict[str, dict] = {
    "ar_advance_rate": {
        "label": "A/R advance rate",
        "path": ["borrowing_base", "accounts_receivable", "advance_rate"],
    },
    "inventory_advance_rate": {
        "label": "Inventory advance rate",
        "path": ["borrowing_base", "inventory", "advance_rate"],
    },
    "concentration_cap_pct": {
        "label": "Concentration cap %",
        "path": ["borrowing_base", "accounts_receivable", "concentration_cap", "pct"],
    },
}


def goal_seek(
    base_config: Config,
    data_dir: str | Path | None,
    lever: str,
    target_value: Decimal,
) -> dict:
    """Reverse-solve a single lever for a target excess availability.

    ``lever`` must be one of the rate/pct levers in ``_GOAL_SEEK_LEVERS``; its
    domain is [0, 1]. Excess availability is (weakly) monotone non-decreasing in
    each of these levers — it rises as we advance more against collateral, then
    plateaus once the commitment binds. We binary-search for the SMALLEST lever
    value x in [0, 1] with ``f(x) >= target``.
    """
    spec = _GOAL_SEEK_LEVERS.get(lever)
    if spec is None:
        raise ValueError(
            f"unknown lever: {lever} (choose from {list(_GOAL_SEEK_LEVERS)})"
        )
    path = spec["path"]
    label = spec["label"]

    def f(x: Decimal) -> Decimal:
        overrides = _nest(path, str(x))
        result = compute_with_overrides(overrides, base_config=base_config, data_dir=data_dir)
        return Decimal(str(result.certificate.excess_availability))

    target = Decimal(str(target_value))

    baseline_value = _read_path(base_config, path)
    baseline_excess = f(baseline_value)

    floor = Decimal("0")
    ceil = Decimal("1")
    f_floor = f(floor)
    f_ceil = f(ceil)

    quant = Decimal("0.0001")

    if target <= f_floor:
        # Already met at (or below) the floor — nothing to free up.
        solved = floor
        achieved = f_floor
        reachable = True
        message = (
            f"Target {_money(target)} is already met at the floor; "
            f"{label} can go as low as 0.00%."
        )
    elif target > f_ceil:
        # Even maxing the lever falls short.
        solved = ceil
        achieved = f_ceil
        reachable = False
        message = (
            f"Target {_money(target)} is not reachable; the most you can free up "
            f"is {_money(achieved)} at 100.00%."
        )
    else:
        lo, hi = floor, ceil
        for _ in range(40):
            mid = (lo + hi) / Decimal("2")
            if f(mid) >= target:
                hi = mid
            else:
                lo = mid
        solved = hi.quantize(quant)
        achieved = f(solved)
        reachable = True
        message = (
            f"Set {label} to {_pct(solved)} to reach "
            f"{_money(target)} of excess availability."
        )

    return {
        "lever": lever,
        "label": label,
        "target": str(target),
        "reachable": reachable,
        "solved_value": str(solved.quantize(quant)),
        "achieved_excess": str(achieved),
        "baseline_value": str(baseline_value),
        "baseline_excess": str(baseline_excess),
        "message": message,
    }


def _money(x: Decimal) -> str:
    return f"${x:,.2f}"


def _pct(x: Decimal) -> str:
    return f"{x * 100:.2f}%"


def ingest(repo: FactRepository, config: Config, data_dir: str | Path | None = None) -> int:
    data_dir = Path(data_dir or config.settings.data_dir)
    facts = load_all(data_dir, config.facility.as_of_date)
    return repo.add_many(facts)


def run_engines(
    repo: FactRepository, config: Config, run_id: str
) -> tuple[VerificationReport, BorrowingBaseCertificate, FccrReport]:
    verification = run_verification(repo, config, run_id)
    certificate = compute_borrowing_base(repo, config, run_id)
    # springing covenant needs the borrowing-base excess availability
    fccr = compute_fccr(repo, config, run_id, excess_availability=certificate.excess_availability)
    return verification, certificate, fccr


def _persist(
    conn: sqlite3.Connection,
    run_id: str,
    config: Config,
    verification: VerificationReport,
    certificate: BorrowingBaseCertificate,
    fccr: FccrReport,
) -> None:
    results = ResultRepository(conn)
    results.create_run(
        run_id, datetime.now().isoformat(), config_hash(config), config.facility.as_of_date
    )
    v = verification.model_dump(mode="json")
    c = certificate.model_dump(mode="json")
    f = fccr.model_dump(mode="json")
    results.save_result(run_id, "verification", v, {"passed": verification.passed, "failed": verification.failed})
    results.save_result(run_id, "borrowing_base", c, {"borrowing_base": str(certificate.borrowing_base)})
    results.save_result(run_id, "fccr", f, {"fccr": str(fccr.fccr), "in_compliance": fccr.in_compliance})
    results.save_findings(run_id, v["findings"])


def _render_artifacts(
    artifacts_dir: Path,
    verification: VerificationReport,
    certificate: BorrowingBaseCertificate,
    fccr: FccrReport,
) -> dict[str, str]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    v = verification.model_dump(mode="json")
    c = certificate.model_dump(mode="json")
    f = fccr.model_dump(mode="json")

    files = {
        "verification_report.json": json.dumps(v, indent=2),
        "verification_report.html": renderer.render_verification(v),
        "borrowing_base_certificate.json": json.dumps(c, indent=2),
        "borrowing_base_certificate.html": renderer.render_certificate(c),
        "fccr_report.json": json.dumps(f, indent=2),
        "fccr_report.html": renderer.render_fccr(f),
    }
    written: dict[str, str] = {}
    for name, content in files.items():
        path = artifacts_dir / name
        path.write_text(content, encoding="utf-8")
        written[name] = str(path)
    return written


def run_pipeline(
    config: Config | None = None,
    data_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    run_id: str | None = None,
    render: bool = True,
    artifacts_dir: str | Path | None = None,
) -> PipelineResult:
    """Ingest, run all engines, persist, and (optionally) render artifacts."""
    config = config or load_config()
    run_id = run_id or new_run_id()
    db_path = db_path if db_path is not None else config.settings.database_path

    conn = connect(db_path)
    init_schema(conn)
    repo = FactRepository(conn)
    fact_count = ingest(repo, config, data_dir)

    verification, certificate, fccr = run_engines(repo, config, run_id)
    _persist(conn, run_id, config, verification, certificate, fccr)

    artifacts: dict[str, str] = {}
    if render:
        out = Path(artifacts_dir or config.settings.artifacts_dir)
        artifacts = _render_artifacts(out, verification, certificate, fccr)
        # cash-flow forecast (its own data path; skip quietly if no cash ledger)
        try:
            forecast = compute_cashflow_with_overrides(
                {}, base_config=config, data_dir=data_dir, run_id=run_id
            )
            cf_json = forecast.model_dump(mode="json")
            (out / "cash_flow_forecast.json").write_text(json.dumps(cf_json, indent=2), encoding="utf-8")
            (out / "cash_flow_forecast.html").write_text(renderer.render_cashflow(cf_json), encoding="utf-8")
            artifacts["cash_flow_forecast.json"] = str(out / "cash_flow_forecast.json")
            artifacts["cash_flow_forecast.html"] = str(out / "cash_flow_forecast.html")
        except FileNotFoundError:
            pass

    conn.close()
    return PipelineResult(
        run_id=run_id,
        config=config,
        verification=verification,
        certificate=certificate,
        fccr=fccr,
        fact_count=fact_count,
        artifacts=artifacts,
    )
