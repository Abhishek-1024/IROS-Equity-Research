# Architecture

```
Clients: React (Next.js) research cockpit  |  Admin workbench (same app, gated route)  |  API  |  Alerts
                                    │
                        API Gateway / Auth / Workspace / Entitlements  (agent/src/api)
                                    │
                LangGraph Orchestrator  (agent/src/agents/graph.py + orchestration/stage*.py)
                  Postgres-checkpointed, resumable, human-in-the-loop approval gates
                                    │
        Agent Runtime + Tool Registry + Model Router  (agent/src/agents/{registry,routing,tools}.py)
────────────────────────────────────────────────────────────────────────────────────────
 Acquisition service | Document intelligence | Transcription | Search
 Fact store | Evidence store | Time-series DB | Object storage (S3/MinIO)
 Company memory | Event/knowledge graph | Vector (pgvector) + keyword (OpenSearch) indexes
 Financial model service | Valuation service | Portfolio analytics
 Evaluation | Observability (OpenTelemetry) | Audit log | Policy/security layer
────────────────────────────────────────────────────────────────────────────────────────
Deployment: local desktop (docker-compose) → single-tenant server / VPC → managed SaaS
```

## Why LangGraph end-to-end

Every stage of the research lifecycle (Stage 0 mandate interpretation → Stage 12
continuous memory) is a LangGraph subgraph composed into one top-level `StateGraph`.
Specialist agents (**50** — the original blueprint's 36 plus 14 added by a root-cause
gap analysis, see `docs/AGENTS_MASTER_REFERENCE.md`) are themselves LangGraph nodes/
subgraphs, one per file under `agent/src/agents/specialists/<tier>/`, so the same
checkpointing, streaming, retry, and human-approval primitives apply uniformly from the
top-level workflow down to an individual agent's internal reasoning loop. See
`docs/adr/0001-orchestration-langgraph.md`.

## Service boundaries

| Service | Owns |
|---|---|
| Identity (`identity_service.py`) | Issuer/security/period resolution, corporate-action history |
| Acquisition (`acquisition_service/`) | Source discovery, connectors, downloads, versions, licensing policy |
| Document (`document_service/`) | Parsing, OCR, tables, slides, chunks, coordinates, derived artifacts |
| Fact (`fact_service.py`) | Typed facts, metrics, definitions, dimensions, sources, validation status |
| Evidence (`evidence_service.py`) | Claim support, contradiction, authority, confidence, citation rendering |
| Memory (`memory_service/`) | Company timelines, thesis history, management credibility, event graph |
| Model (`model_service/`) | Historicals, drivers, formulas, scenarios, forecasts, diffs, Excel import/export |
| Valuation (`valuation_service/`) | DCF, SOTP, comps, sector-specific valuation |
| Report (`report_service/`) | Templates, cockpit data, PDF/DOCX/PPT/Excel, versioning, publishing |
| Evaluation (`evaluation_service.py`) | Benchmark cases, outcome tracking, regression tests, quality gates |
| Portfolio (`portfolio_service.py`) | Position exposure, factor/thematic read-through |

Each service is called by LangGraph nodes — services never call the LLM directly for
arithmetic, reconciliation, or period mapping (deterministic-only, per blueprint
principle #2); only agent nodes call the model router.

## Data flow (one research run)

1. React cockpit submits `POST /v1/research-runs` → FastAPI validates request →
   enqueues a LangGraph run keyed by `research_run_id`.
2. LangGraph executes Stage 0-12 subgraphs, checkpointing state to Postgres after every
   node so the run is resumable after a crash or restart.
3. Node progress/events stream to the frontend over WebSocket
   (`agent/src/api/websocket.py` ↔ `frontend/src/hooks/useRunWebSocket.ts`).
4. Terminal state produces cockpit data + exports via `report_service`; the frontend
   fetches the finished `ResearchRun` via `GET /v1/research-runs/{run_id}`.
