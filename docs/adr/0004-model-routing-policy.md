# ADR 0004: Model routing policy for LangGraph agents

## Status
Accepted

## Decision
`agent/src/agents/routing.py` implements a task-based model router consumed by every
LangGraph node, per the blueprint's routing table:

| Task | Mechanism |
|---|---|
| Identity, dates, formulas, reconciliation | Deterministic code only — never an LLM. |
| Classification / simple extraction | Small local/cheap structured-output model + validators. |
| Vision / table interpretation | Specialized document/vision model, reconciled deterministically after. |
| Long-document retrieval | Keyword + semantic + graph retrieval, reranker, bounded evidence pack. |
| Complex thesis synthesis | Strong reasoning model, sanitized/bounded evidence, structured output only. |
| Critique / adjudication | Independent model family from the synthesis step, where possible. |
| Confidential internal data | Local/customer-hosted model or approved private endpoint only. |
| Final prose | Strong model, invoked only after facts/calculations/conclusions are frozen. |

Every LangGraph node declares its task type in its `AgentSpec`; the router resolves the
task type + data-sensitivity label to a concrete provider/model at run time, so model
choice is configuration, not code, per agent.

## Consequences
Swapping providers (e.g., local Ollama model to a hosted model) is a config change, and
confidential-data workflows are structurally prevented from reaching unapproved
endpoints.
