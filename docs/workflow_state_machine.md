# Workflow State Machine (LangGraph)

The whole research lifecycle is one top-level LangGraph `StateGraph`
(`agent/src/agents/graph.py`), built by composing one subgraph per stage
(`agent/src/agents/orchestration/stage*.py`). Shared state is defined once in
`agent/src/agents/state.py` and flows through every stage/node.

## Stages → LangGraph subgraphs

| # | Stage (blueprint §3) | Subgraph module | Human gate? |
|---|---|---|---|
| 0 | Mandate interpretation | `stage0_research_planning.py` | optional (clarify) |
| 1-2 | Entity/period resolution + source planning & acquisition | `stage1_2_entity_and_acquisition.py` | on ambiguous identifier |
| 3-4 | Document intelligence + structured fact extraction | `stage3_4_document_intelligence.py` | no |
| 5 | Reconciliation & validation (deterministic only) | `stage5_reconciliation.py` | on unresolved high-severity conflict |
| 6 | Historical & expectation comparison | `stage6_comparison.py` | no |
| 7 | Specialist analysis (fan-out to relevant agents) | `stage7_specialist_analysis.py` | no |
| 8 | Model & valuation update | `stage8_model_valuation.py` | on model overwrite |
| 9 | Investment thesis synthesis | `stage9_thesis_synthesis.py` | no |
| 10 | Critique & adjudication | `stage10_adjudication.py` | on adjudicator abstain/downgrade |
| 11 | Output generation | `stage11_output_generation.py` | on external publication |
| 12 | Continuous memory & learning | `stage12_memory_update.py` | no |

## Node contract

Every node:
1. Reads only the typed state slice it declares (`required_inputs` on its `AgentSpec`).
2. Calls deterministic services directly for arithmetic/reconciliation/formatting, and
   the model router (`agents/routing.py`) only for interpretation/synthesis/critique.
3. Writes a typed output back onto state plus an `AgentRun` audit record.
4. Never raises silently — missing data, low confidence, and conflicts become explicit
   state fields (`missing_data`, `conflicts`, `warnings`), not exceptions swallowed by
   the graph.

## Resumability

- Checkpointer: `agent/src/agents/checkpointing/checkpointer.py` persists graph
  state after every node using LangGraph's checkpoint API, keyed by `research_run_id`.
- Re-invoking a `ResearchRun` with the same `research_run_id` resumes from the last
  checkpoint instead of restarting (idempotent nodes make this safe even if a node
  partially executed before a crash).
- Human-in-the-loop gates use LangGraph `interrupt()`; the graph pauses and persists
  state until an `Approval` object is written, then resumes.

## Error taxonomy (surfaced on state, never silent)

`AmbiguousIdentifier`, `PeriodUnavailable`, `SourceUnavailable`, `SourceConflict`,
`ReconciliationFailure`, `LowConfidenceExtraction`, `UnsupportedClaim`,
`ModelProviderOutage`, `ApprovalRequired`, `AbstentionRequired`.
