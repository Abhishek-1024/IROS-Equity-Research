# ADR 0001: LangGraph as the single workflow & agent orchestration engine

## Status
Accepted

## Context
The master blueprint's original technical baseline proposed Temporal for durable
production workflow execution, with LangGraph (or a custom DAG) used only for the
inner agent-reasoning subgraphs. The user has asked to standardize on LangGraph for
the *entire* agentic workflow, not just the reasoning subgraphs.

## Decision
Use **LangGraph** as the single orchestration layer for:
1. The top-level research lifecycle (Stage 0 mandate interpretation through Stage 12
   continuous memory/learning) — implemented as one top-level `StateGraph` in
   `agent/src/agents/graph.py`, composed of subgraphs per stage
   (`agent/src/agents/orchestration/stage*.py`).
2. Every specialist-agent subgraph (right-sized to **22 agents** — see
   `docs/AGENTS_MASTER_REFERENCE.md` — in `agent/src/agents/specialists/`, plus a
   deterministic services layer for everything that doesn't need a model call).

Durability, resumability, retries, and human-in-the-loop approval gates are provided by:
- LangGraph's built-in **checkpointer** interface, backed by PostgreSQL
  (`agent/src/agents/checkpointing/checkpointer.py`), so a `ResearchRun`
  survives process restarts and can resume from the last completed node.
- LangGraph's `interrupt`/human-in-the-loop primitives for the mandatory approval gates
  defined in the blueprint (publish, model overwrite, trade-related output).
- Idempotent node design: every node reads/writes typed state (`agent/src/agents/state.py`)
  and canonical domain objects, so re-running a node with the same inputs is safe.

## Consequences
- One mental model and one library for both macro workflow and micro agent reasoning —
  simpler ops, fewer moving parts than Temporal + LangGraph.
- We give up some of Temporal's heavier durable-execution guarantees (cross-language
  workers, very long-running workflow histories at massive scale). This is an
  acceptable trade-off for the target deployment (local-first / single-tenant / VPC),
  and can be revisited only if operational scale later demands it (tracked as a
  future ADR, not a current requirement).
- All workflow state, retries, and audit trail requirements from the blueprint
  ("resumable, idempotent, observable, testable, versioned") map directly onto
  LangGraph checkpoints + our own `AgentRun`/`ResearchRun` audit objects.

## Alternatives considered
- **Temporal for macro workflow + LangGraph for agent subgraphs** (original blueprint
  suggestion): rejected for this project to reduce operational surface area, per
  explicit user direction.
- **Custom hand-rolled DAG executor**: rejected — LangGraph already provides
  checkpointing, streaming, human-in-the-loop, and a large tool/agent ecosystem.

## Update (2026-07-31)
The "right-sized to 22 agents" figure in the Decision section above was the original
target architecture from `docs/AGENTS_MASTER_REFERENCE.md`. As the system was
actually implemented, 3 additional agents were added beyond that original roster —
`filing_narrative_analyst`, `market_data_validation`, and `ic_memo_writer` — and
`continuous_monitoring_agent` (originally counted as one of the 22) was
reclassified as a "standing" agent that runs on its own separate schedule
(`continuous_ops_graph.py`) rather than inside the on-demand `ResearchRun`
pipeline. The actual shipped count is **24 on-demand agents + 1 standing agent =
25 total** — see `docs/agent_modularization_plan.md` for the full, code-verified
current-state audit. This ADR's core decision (LangGraph as the single
orchestration engine for both the top-level workflow and every specialist-agent
subgraph) is unaffected by the exact agent count.
