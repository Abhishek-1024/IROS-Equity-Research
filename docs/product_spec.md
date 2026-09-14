# Product Spec — Build Roadmap (React + LangGraph)

This condenses the master blueprint's 6 phases / 9 sub-prompts into **5 build steps**,
each scoped to be handed to a coding agent as one self-contained prompt (see the
"Hand-off prompts" section). All steps build on the scaffold already created in
`agent/` and `frontend/`.

> **For agent-by-agent implementation detail, use
> [docs/AGENTS_MASTER_REFERENCE.md](AGENTS_MASTER_REFERENCE.md) instead of this file.**
> This document groups work into 5 coarse phases; AGENTS_MASTER_REFERENCE.md is the
> single exhaustive catalog of the right-sized **22-agent** architecture (roles,
> dependencies, typed inputs/outputs, tools, validators, and a standalone build
> checklist per agent) plus the deterministic services layer, meant to be built one
> file at a time, in the numbered order it specifies.

## Step map

| Step | Name | Covers blueprint phase(s) | Primary folders touched |
|---|---|---|---|
| 1 | Foundations & Contracts | Phase 0 | `agent/src/domain`, `agent/src/db`, `agent/src/agents/state.py`, `agent/src/agents/graph.py`, `agent/src/cli`, `agent/tests` |
| 2 | Acquisition & Document Intelligence | Phase 1A + 1B | `agent/src/services/acquisition_service`, `agent/src/services/document_service`, `agent/src/agents/orchestration/stage1_2_*`, `stage3_4_*` |
| 3 | Comparisons, Specialist Agents & Critique | Phase 1C + 1D | `agent/src/agents/specialists/*`, `agent/src/agents/orchestration/stage6_*` .. `stage10_*`, `agent/src/services/evidence_service.py`, `fact_service.py` |
| 4 | React Research Cockpit | Phase 1E | `frontend/src/app`, `frontend/src/components`, `frontend/src/hooks`, `frontend/src/lib` |
| 5 | Memory, Model/Valuation & Portfolio | Phase 2 + 3 + 5 | `agent/src/services/memory_service`, `model_service`, `valuation_service`, `portfolio_service`, `agent/src/agents/orchestration/stage8_*`, `stage12_*` |

Enterprise platform (blueprint Phase 6 — multi-tenant, VPC, Excel/PPT add-ins) is
intentionally deferred as a Step 6+ once Steps 1-5 are proven on the earnings-review
wedge, per the blueprint's "start with the smallest complete institutional workflow"
guidance.

## Hand-off prompts

Copy each prompt verbatim into a new session, in order. Each is self-contained and
references the scaffold already in the repository.

---

### Prompt 1 — Foundations & Contracts

> Implement Step 1 (Foundations & Contracts) of the IROS build in this repository.
> Flesh out the canonical Pydantic v2 domain schemas already stubbed in
> `agent/src/domain/` to match `docs/data_contracts.md` exactly (field names, types,
> required/optional). Wire real SQLAlchemy models + Alembic migrations in `agent/src/db/`
> for every canonical object. Implement the top-level LangGraph `StateGraph` in
> `agent/src/agents/graph.py` and the shared state schema in `agent/src/agents/state.py`
> per `docs/workflow_state_machine.md`, with a Postgres checkpointer
> (`agent/src/agents/checkpointing/checkpointer.py`) so runs are resumable.
> Implement the `validate_research_run` CLI so it parses a `ResearchRun` request,
> resolves it against the state machine, and prints the planned DAG without doing any
> network work. Add unit + contract tests for every schema and the CLI. No acquisition,
> no analysis agents, no UI in this step. Run all tests and report results.

---

### Prompt 2 — Acquisition & Document Intelligence

> Implement Step 2 of the IROS build. Build out the connectors in
> `agent/src/services/acquisition_service/connectors/` (SEC/EDGAR, IR website discovery,
> web/news, webcast/audio) behind the shared `ConnectorBase` interface, with source
> manifest generation, artifact hashing/versioning, amendment detection, and coverage
> scoring, using offline fixtures for a small set of US-company test cases (no live
> scraping in tests). Build out the parsers in
> `agent/src/services/document_service/parsers/` (PDF/HTML, table reconstruction,
> transcript structuring, local audio transcription via faster-whisper) with preserved
> page/slide/cell/timestamp coordinates and confidence scores. Wire
> `agent/src/agents/orchestration/stage1_2_entity_and_acquisition.py` and
> `stage3_4_document_intelligence.py` as LangGraph subgraphs that call these services.
> Add golden-document accuracy tests. Do not implement analysis agents or reconciliation
> scoring beyond what's needed to produce typed `Fact`/`DocumentElement` outputs.

---

### Prompt 3 — Comparisons, Specialist Agents & Critique

> Implement Step 3 of the IROS build. Flesh out the specialist agents stubbed in
> `agent/src/agents/specialists/` (right-sized to 22 agents, one folder per agent —
> see docs/AGENTS_MASTER_REFERENCE.md, which supersedes the original 36-agent
> blueprint count; the actual build grew to 24 on-demand + 1 standing agent — see
> docs/agent_modularization_plan.md for the current, code-verified count) as real
> LangGraph nodes with typed inputs/outputs per `AgentSpec`,
> bounded evidence packs, and the model routing policy in `agent/src/agents/routing.py`. Implement
> `agent/src/agents/orchestration/stage5_reconciliation.py` (deterministic reconciliation
> only, no LLM),  `stage6_comparison.py` (actual-vs-consensus/internal/guidance/peer/
> thesis deltas), `stage7_specialist_analysis.py` (fan-out/fan-in to specialists),
> `stage9_thesis_synthesis.py`, and `stage10_adjudication.py` (Devil's Advocate,
> Evidence Auditor, Numerical Auditor, Investment Committee Adjudicator). Enforce that
> no agent introduces new facts during prose generation. Add unsupported-claim and
> citation tests, plus an adversarial test corpus (missing guidance, restatement,
> conflicting sources). Produce a machine-readable `EarningsEventAnalysis` object.

---

### Prompt 4 — React Research Cockpit

> Implement Step 4 of the IROS build. Build the Next.js + TypeScript research cockpit in
> `frontend/`. Wire `src/lib/apiClient.ts` to the FastAPI gateway's
> `POST /v1/research-runs`, `GET /v1/research-runs/{run_id}`, and related endpoints; wire
> `src/hooks/useRunWebSocket.ts` to stream LangGraph stage/node progress. Implement the
> command bar + context selector + run plan (`src/components/command/`), the cockpit
> modules (`src/components/cockpit/`: decision card, what-changed, financial scorecard,
> estimate bridge, variant perception, bull/bear debate, management credibility,
> catalyst calendar, risk map, provenance/quality), and the evidence drawer
> (`src/components/evidence/`) that opens the exact source coordinate for any number or
> claim. Gate `/admin` (agent traces, connector health, prompts, source conflicts) behind
> a role check — same app, not a separate tool. Add Playwright E2E tests for the
> ticker-to-cockpit flow and basic accessibility/responsive checks.

---

### Prompt 5 — Memory, Model/Valuation & Portfolio

> Implement Step 5 of the IROS build. Implement `agent/src/services/memory_service`
> (versioned company memory, event timeline, management credibility, thesis history —
> new quarters must update, never overwrite, history) and wire
> `agent/src/agents/orchestration/stage12_memory_update.py`. Implement
> `agent/src/services/model_service` (canonical driver-based formula graph, Excel
> import/export via openpyxl, estimate-change ledger) and `valuation_service` (DCF, comps,
> SOTP, sector plug-ins), wired into `stage8_model_valuation.py`, with independent
> numerical-audit reproducibility tests. Implement `agent/src/services/portfolio_service`
> (position-level event exposure, factor/concentration read-through) and the Portfolio
> workspace route in the frontend. Add property-based tests for formulas, statement
> balance identities, scenario isolation, and valuation reproducibility, plus a
> regression test proving new quarters update rather than overwrite company memory.

## Acceptance bar for the whole roadmap

Same acceptance criteria as the master blueprint §18.1 (see
`docs/blueprint/Institutional_Research_OS_Blueprint_v3_React_LangGraph.md`), applied at
the end of Step 3 for the earnings-review wedge and re-verified after Step 5.
