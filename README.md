# Verified Financials

A demo platform built for **Red Lion Advisory** to show a client — a ~$180M
family-owned food-distribution business ("McLane-like", five operating
segments, a new bank revolver). It proves three capabilities on synthetic but
realistic data:

1. **Verification / tie-out** — ingest messy financials and flag where the
   numbers don't reconcile, tracing every figure to its source file.
2. **Borrowing base → certificate** (the centerpiece) — apply the facility's
   eligibility rules automatically and produce a bank-ready Borrowing Base
   Certificate.
3. **FCCR covenant monitor** — compute the trailing-twelve-month Fixed Charge
   Coverage Ratio, compare it to the covenant, and raise an early warning
   *before* a breach.

Every figure is stored as a **Fact with provenance** (source file + location +
as-of date + version), and every rule lives in **`config.yaml`** — the "loan
agreement as config" — so the tool visibly adapts to any credit agreement.

## The demo in one breath

The company *looks* like it has ~$30M A/R + ~$20M inventory ($50M of
collateral) against a $40M revolver. After eligibility rules:

| | |
|---|---|
| Eligible A/R | **$22.15M** (× 85% → $18.83M) |
| Eligible inventory | **$17.00M** (× 50% → $8.50M) |
| **Borrowing base** | **$27.33M** |
| Less $22.0M outstanding → **excess availability** | **$5.33M** |
| **FCCR (TTM)** | **1.20x** vs **1.10x** covenant — compliant but *trending down* (1.35 → 1.28 → 1.20), ~$1.0M EBITDA cushion |

And three reconciliation exceptions surface up front: a **$200K** A/R gap, a
**$500K** inventory gap, and a **$1.3M** revenue conflict between two versions
of the same file.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

vfin run-all                 # baseline demo → artifacts/  ($27.33M / $5.33M / 1.20x)
vfin run-all --scenario stress   # stress demo → artifacts_stress/ (NOLV, reserves, breach, cure)
open artifacts/borrowing_base_certificate.html   # → Print → Save as PDF for the bank
```

Individual engines (add `--scenario stress` for the advanced case):

```bash
vfin generate-data           # write the synthetic CSVs to ./data
vfin verify                  # tie-out exceptions
vfin borrowing-base          # certificate summary
vfin fccr                    # covenant + early warning
```

Run the API:

```bash
uvicorn verified_financials.api.app:app --reload
# open http://127.0.0.1:8000/docs  (Swagger UI)
```

Key endpoints: `POST /compute` (live what-if — `{scenario, config_overrides}` →
recompute, no persist), `POST /briefing` + `POST /ask` (AI advisor — see below),
`GET /scenarios`, `GET /config?scenario=`,
`GET /facts?scenario=&dataset=&metric=` (provenance), `POST /pipeline/run`,
`GET /runs/{id}/{borrowing-base,verification,fccr}[.html]`.

### AI advisor briefing (OpenAI)

The **Advisor Briefing** page writes a plain-English executive memo from the live
numbers and answers free-text questions about them (streamed), grounded so it
only cites the computed figures. Set a key to enable it.

The recommended way is a `.env` file (auto-loaded by both `uvicorn` and `vfin`;
git-ignored so the key never gets committed):

```bash
cp .env.example .env       # then edit .env:  OPENAI_API_KEY=sk-...
                           # optional in .env:  OPENAI_MODEL=gpt-4o  (default gpt-4o-mini)
```

Or export it in your shell for a one-off session:

```bash
export OPENAI_API_KEY=sk-...        # optional: OPENAI_MODEL=gpt-4o  (default gpt-4o-mini)
```

**No key? It still works** — the briefing falls back to a deterministic,
rule-generated memo (no network), and Q&A shows a "set a key" message. All
LLM access is isolated in `ai/llm.py`, so swapping providers is one file.

## Frontend (interactive web app)

React + Vite + TypeScript + shadcn/ui over the API: an overview dashboard,
verification exceptions, the borrowing-base certificate, and the FCCR trend —
with a **baseline⇄stress switcher**, a **comprehensive live what-if panel**
(edit any rule or facility term → instant recompute across all views), and
**provenance drill-down** (click a figure → its source facts).

**Bring your own data** (the *Upload Data* page): download the six CSV
templates, fill them in, upload → the app validates the schema and runs all
three engines on *your* data (no YAML editing). Uploading the baseline CSVs
reproduces the baseline numbers. (Lightweight: fixed-schema CSVs, no fuzzy
column-mapping yet.)

```bash
# dev (two servers)
uvicorn verified_financials.api.app:app --reload      # :8000
cd frontend && npm install && npm run dev             # :5173
#   the dev server reads frontend/.env for VITE_API_BASE (the API URL);
#   it's committed already — cp frontend/.env.example frontend/.env if missing.

# one-URL demo (FastAPI serves the built SPA)
cd frontend && npm run build
uvicorn verified_financials.api.app:app               # open http://127.0.0.1:8000/
```

`npm run gen:types` regenerates `src/lib/types.ts` from the live OpenAPI schema.

## The planted problems (and which feature catches each)

| # | Planted issue | Caught by |
|---|---|---|
| 1 | BS A/R $30.2M ≠ aging detail $30.0M | Verification |
| 2 | BS inventory $20.0M ≠ trial balance $20.5M | Verification |
| 3 | 2025 revenue $182.4M vs re-sent $181.1M | Verification (version conflict) |
| 4 | Lone Star Grocery Group = 22% of A/R (> 15% cap) | Borrowing base (excess excluded) |
| 5 | Gulf Provisions LLC (UAE, uninsured) $2.0M | Borrowing base (foreign-uninsured) |
| 6 | $1.8M receivables aged 90+ days | Borrowing base (aged) |
| 7 | McLane Logistics International $1.2M | Borrowing base (intercompany) |
| 8 | $3.0M obsolete / slow-moving inventory | Borrowing base (inventory) |
| 9 | FCCR thin & trending toward covenant | FCCR (early warning) |

> Manila Foods Dist. is foreign **but credit-insured**, so it correctly *stays*
> eligible — proof the engine applies the real exception, not a blunt rule.

## Architecture

```
config.yaml                 the loan agreement as config (rates, caps, rules, checks)
src/verified_financials/
  config/    validate config.yaml -> typed Config (+ config hash for run provenance)
  models/    Fact (provenance) + result DTOs (pydantic, JSON-serializable)
  store/     SQLite schema + repository (the DAL; Postgres swap = one new class)
  loaders/   CSV -> Facts with provenance + version tags
  engines/   verification · borrowing_base (the waterfall) · fccr
  rendering/ Jinja2 + print CSS -> bank-styled HTML (print-to-PDF)
  pipeline.py  orchestrator shared by CLI + API
  api/       FastAPI service (DTOs as response models -> OpenAPI for the UI)
  cli.py     `vfin` commands
scripts/generate_data.py    reproducible, seeded synthetic data
tests/                      pins every demo number; golden snapshots lock the DTOs
```

**Borrowing base waterfall.** Categorical ineligibles (aged 90+, foreign-
uninsured, intercompany) are removed first to form a fixed pre-concentration
base ($25.0M); the 15% single-obligor cap is then measured against that base,
excluding only the **excess** above the cap (standard ABL convention). The cap
basis is configurable (`post_categorical` vs `gross`). Money is `Decimal`
end-to-end so the numbers are exact and the golden snapshots are deterministic.

## Deeper modeling (the `stress` scenario)

The same engines, driven by `config_advanced.yaml` on a distressed dataset
(`data_stress/`), turn on five real-world ABL/covenant mechanics — all
config-driven, all defaulting to a no-op so the baseline is untouched:

| Feature | What it does | Stress result |
|---|---|---|
| **NOLV inventory valuation** | per-category liquidation haircut: `min(cost, NOLV%×cost) × advance` | $18.0M cost → $10.0M NOLV → **$8.0M** avail |
| **Reserves** | dilution `(dilution%−threshold)×eligible AR` + priority-payable + rent | **$1.85M** subtracted at roll-up |
| **Cross-aging taint** | whole obligor ineligible when majority past due | Sunset Diners **$1.5M** tainted |
| **Springing covenant** | FCCR tested only when excess avail < `max(%×commitment, floor)` | trigger $3.75M > avail $1.75M → **ACTIVE** |
| **Equity cure** | `max(0, covenant×denominator − numerator)` to restore compliance | **$1.9M** cures the 0.89x breach |

Stress headline: borrowing base **$19.75M**, excess availability **$1.75M**,
FCCR **0.89x → BREACH**. Run `vfin run-all --scenario stress`.

## Tests

```bash
pytest -q                         # 41 tests: data calibration, engines, advanced modeling, golden, API
VFIN_UPDATE_GOLDEN=1 pytest tests/test_pipeline_golden.py   # refresh snapshots after an intended change
```

## Deferred / future

- Multi-audience (bank / board / family-office) report views, auth, persisted
  what-if sessions, server-side PDF, per-segment analytics.

*Synthetic data only — for demonstration.*
