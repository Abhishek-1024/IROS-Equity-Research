# Project Structure

High-level map of the repository. See `agent/README.md` and `frontend/README.md` for
the detailed per-app trees.

```
Equity_Research/
├── docs/
│   ├── product_spec.md              Phases, roadmap, hand-off prompts
│   ├── architecture.md              System architecture (services, data flow)
│   ├── data_contracts.md            Canonical object schemas (source of truth)
│   ├── workflow_state_machine.md    LangGraph state machine / stage graph
│   ├── source_policy.md             Source authority hierarchy, conflict rules
│   ├── evaluation_plan.md           Quality gates + evaluation metrics
│   ├── project_structure.md         This file
│   ├── adr/                         Architecture Decision Records
│   ├── blueprint/                   Edited master product blueprint (React + LangGraph)
│   └── AGENTS_MASTER_REFERENCE.md   Right-sized 22-agent roster, build order, per-agent
│                                     input/output spec — the primary reference for
│                                     agent-by-agent implementation
│
├── agent/                           Python backend (FastAPI + LangGraph)
│   ├── src/api/                     HTTP + WebSocket gateway
│   ├── src/core/                    Config, security, observability, errors
│   ├── src/domain/                  Canonical Pydantic v2 schemas
│   ├── src/services/                Identity, acquisition, document, fact, evidence,
│   │                                 memory, model, valuation, report, evaluation,
│   │                                 notification, portfolio services — also the home
│   │                                 for logic reclassified out of the agent roster
│   │                                 (see AGENTS_MASTER_REFERENCE.md §4/§8)
│   ├── src/agents/                  LangGraph orchestration graphs + 25 specialist
│   │                                 agents, ONE PACKAGE PER AGENT under
│   │                                 specialists/<tier>/<agent_id>/{spec,schemas,
│   │                                 agent,prompts}.py, plus resilience.py
│   │                                 (timeout/retry/circuit-breaker) and registry.py's
│   │                                 dependency-based parallel-wave scheduler
│   ├── src/db/                      SQLAlchemy models, sessions, migrations
│   ├── src/cli/                     Operator CLI (e.g. validate a ResearchRun request)
│   └── tests/                       unit, contract, golden, property, e2e
│
└── frontend/                        React (Next.js + TypeScript) cockpit
    ├── src/app/                     Routed pages (App Router)
    ├── src/components/cockpit/      Decision card, scorecard, bridge, debate, etc.
    ├── src/components/evidence/     Evidence drawer / citation rendering
    ├── src/components/command/      Command bar, context selector, run plan, actions
    ├── src/hooks/                   Data hooks (REST + WebSocket run streaming)
    ├── src/lib/                     API client, shared types, formatting
    ├── src/state/                   Client state stores
    └── tests/                       unit (Vitest/RTL) + e2e (Playwright)
```
