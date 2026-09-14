
Python 3.12 backend: FastAPI gateway + LangGraph multi-agent research workflow.
See [../docs/architecture.md](../docs/architecture.md) and
[../docs/workflow_state_machine.md](../docs/workflow_state_machine.md).

## Layout

```
src/
├── api/            FastAPI app, routers, WebSocket streaming, auth deps
├── core/           Config, security, observability, error taxonomy
├── domain/         Canonical Pydantic v2 schemas (docs/data_contracts.md)
├── services/       Identity, acquisition, document, fact, evidence, memory,
│                   model, valuation, report, evaluation, portfolio services
├── agents/         LangGraph: top-level graph, per-stage subgraphs, 25 specialist
│                   agents, tools, model router, Postgres checkpointer
├── db/             SQLAlchemy models, session, Alembic migrations
└── cli/            Operator CLI (validate_research_run, etc.)
tests/
├── unit/ contract/ golden/ property/ e2e/
```

## Quick start (local dev)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
uvicorn src.api.main:app --reload
```

## Key commands

```powershell
pytest                                   # run all tests
python -m src.cli.validate_research_run --security AAPL --period latest
python scripts/generate_professional_model.py AAPL --units millions   # live-formula Excel model (see below)
```

### Professional (live-formula) Excel financial model

`scripts/generate_professional_model.py` builds an institutional-grade, fully
live-formula 3-statement + DCF Excel workbook for a real ticker — every
forecast cell is a real Excel formula (never a pasted number), cross-sheet
linked, in millions/billions, with a blue/black/green input/formula/cross-
sheet-link font convention. A 3-stage deterministic pipeline:

1. **Data & Forecast Agent** — the existing `financial_model.build_financial_model`.
2. **Excel Formula-Builder Agent** — `services/market_data/excel_formula_model.py`.
3. **Validator Agent** — `services/market_data/model_formula_validator.py`
   recalculates every formula with a real formula-evaluation engine and
   cross-checks it against Agent 1's own verified ground truth, appending a
   "Formula Audit" sheet to the workbook.

Only supports the generic driver-based archetype (not banks/insurers/REITs/
utilities/capital-markets/mortgage-REITs, which use a structurally different
model — see that module's docstring); fails with a clear message otherwise.

