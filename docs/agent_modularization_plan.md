# Agent Modularization & Decision-Registry Plan

**Status:** Planning / not yet implemented. This document is the output of a full
code-level audit of the current 25-agent system (not a redesign from scratch) —
every claim below was verified against the actual source, not assumed. **Section 7
contains 10 extensive, fully self-contained prompts** (each restates its own context,
exact files, exact schemas, edge cases, and acceptance criteria) — copy the contents
of one code block at a time, in order, into a session to implement that piece.

## Quick index — jump straight to a prompt

| # | Prompt | Scope |
|---|---|---|
| 0 | [Cleanup pass](#prompt-0) | Fix 18 stale agent-count references; delete 1 dead file |
| 1 | [Decision Registry core](#prompt-1) | New `decision_registry` state field, auto-populated in `BaseAgent.__call__` |
| 2 | [Context Registry Compiler + temperature](#prompt-2) | `build_node_context`, per-task-type temperature, prompt versioning — the 4 LLM agents only |
| 3 | [Contradiction detection](#prompt-3) | Structured `state["contradictions"]`, fixes which-agent-said-what |
| 4 | [Folder restructure — Desks 1-3](#prompt-4) | `desk1_mandate_coverage/` .. `desk3_document_fact_extraction/` |
| 5 | [Folder restructure — Desk 4](#prompt-5) | `desk4_fundamental_context_research/` + fixes the `market_data_validation` misfiling |
| 6 | [Folder restructure — Desks 5-6](#prompt-6) | `desk5_strategy_idea_generation/`, `desk6_modeling_valuation/` |
| 7 | [Folder restructure — Desk 7](#prompt-7) | `desk7_investment_committee/` |
| 8 | [Folder restructure — Desk 8](#prompt-8) | `desk8_decision_distribution_monitoring/` + final full regression pass |
| 9 | [Eval harness (optional)](#prompt-9) | A/B compare two prompt versions on real tickers |

---

## 1. Grounded findings — what the system actually does today

Before proposing anything, here is what direct code inspection confirmed (not
what the docs/comments claim — several of those are stale, see 1.4):

### 1.1 Parallelism is real, not aspirational

[`agents/orchestration/_wave_runner.py`](../agent/src/agents/orchestration/_wave_runner.py)'s
`run_wave()` runs every agent in a dependency-resolved wave concurrently via
`asyncio.gather`, then merges partial-state updates with clean, explicit semantics
(`merge_state_update`: list-valued keys concatenate; scalar keys are last-write-wins
with a recorded collision warning, never a silent clobber). `registry.resolve_execution_waves`
topologically sorts agents by `AgentSpec.depends_on` into waves; `run_waves` threads
each wave's output into the next wave's input state.

Per [`desk_registry.py`](../agent/src/agents/orchestration/desk_registry.py)'s own
`CollaborationMode` per desk:

| Desk | Mode | Real behavior |
|---|---|---|
| 1. Mandate & Coverage | `SEQUENTIAL_HANDOFF` | strictly ordered (planner must scope before the resolver runs) |
| 2. Data Acquisition | `PARALLEL_WAVE` | 2 agents concurrent |
| 3. Document & Fact Extraction | `GATED_PARALLEL` | 1 gatekeeper, then 2 agents concurrent, then 2 deterministic checks |
| 4. Fundamental & Context Research | `PARALLEL_WAVE` | **5 agents concurrent** |
| 5. Strategy & Idea Generation | `PARALLEL_WAVE` | 2 agents concurrent |
| 6. Modeling & Valuation | `SEQUENTIAL_HANDOFF` | model must reconcile before valuation runs |
| 7. Investment Committee | `ADVERSARIAL_CHAIN` | **deliberately sequential** — separation of powers, not a perf choice |
| 8. Decision, Distribution & Monitoring | `PARALLEL_WAVE` | 3 agents concurrent |

So: yes, this is already a genuine multi-agent, partially-parallel system — 4 of 8
desks fan out concurrently, and the adversarial desk is *intentionally* sequential
(merging those agents would remove the actual governance value, not just an
implementation detail — see §4).

### 1.2 The surprising part: only 4 of 25 agents touch an LLM at all

An exhaustive `grep` for `ModelRouter().get_client(` across the entire `src/` tree
returns exactly 8 call sites — 4 inside registered agents, 4 inside services:

| Call site | Kind | Task type |
|---|---|---|
| `industry_competitive_context/agent.py` (x2) | agent (direct) | SYNTHESIS |
| `transcript_intelligence/agent.py` | agent (direct) | CLASSIFICATION |
| `continuous_monitoring_agent/agent.py` | agent (direct) | CLASSIFICATION |
| `filing_narrative_analyst/agent.py` → `filings_rag/service.py` (x2) | agent (**indirect**, via service) | RETRIEVAL |
| `market_data/ai_narrative.py` | service (not a registered agent) | FINAL_PROSE |
| `market_data/domain_classifier.py` | service | SYNTHESIS |
| `market_data/validation_narrative.py` | service | CRITIQUE |

Verified by direct inspection that these are **fully deterministic Python** (no LLM
import at all): `thesis_synthesizer`, `devils_advocate`, `verification_agent`,
`ic_memo_writer`. The pattern is consistent enough (confirmed on 4 separate "judgment"-
sounding agents, cross-checked against the exhaustive grep) to conclude with high
confidence: **21 of the 25 agents are pure deterministic Python today** — they read
already-typed/already-extracted state, apply rules/templates/threshold logic, and
produce structured output, with zero model call and therefore zero hallucination
surface in the traditional sense. Only **4 agents (16%) — `industry_competitive_context`,
`transcript_intelligence`, `continuous_monitoring_agent`, `filing_narrative_analyst`
— plus 3 supporting services genuinely call a language model.**

This matters a lot for the rest of this plan: a "reduce hallucination / manage context"
architecture only needs to be applied where an LLM is actually in the loop — not to
all 25 agents. Retrofitting all 25 with a heavyweight context-registry mechanism
would be solving a problem 21 of them don't have.

### 1.3 Good practices that already exist (don't reinvent these)

- **Evidence-by-reference, not by-value**: every claim cites a `fact_id`/`evidence_ref`
  string resolved via `evidence_service.collect_known_evidence_refs(state)` — nothing
  duplicates raw text into a "thesis," it cites the ID. This *is* a decision-registry
  pattern already, just not named/packaged as one.
- **`AgentRunResult`** (`domain/runs.py`) already carries `status`, `confidence`,
  `evidence_refs`, `warnings`, `quality_checks` for every single agent call —
  `state["agent_runs"]` (an `operator.add`-reduced list) is already an append-only
  decision ledger.
- **`prompt_budget.py`** already measures every real prompt against 60% of the active
  model's context window before sending and requires the caller to react — this is
  the "don't gobble up context" discipline, just enforced ad hoc per call site rather
  than through a shared builder.
- **`industry_competitive_context`**'s real-ticker path already hard-caps its business-
  description input at 700 characters before it goes into a prompt — a real,
  working example of deliberate context curation, again ad hoc.
- **`merge_state_update`**'s collision warning is a primitive form of contradiction
  detection already.

### 1.4 One thing NOT done today, worth fixing first: temperature

Confirmed: **`llm_client.py` never sets a `temperature` parameter** for any provider
(Ollama, OpenAI, or Anthropic) — every real call runs at that provider's/model's
*default* temperature (typically 0.7–1.0), not a low, deterministic setting. This is
the single most direct, lowest-risk fix matching your explicit ask for
"temperature 0.1 agent intelligence" — see §3.4.

### 1.5 Stale numbers to clean up (found, not fixed yet)

`AGENTS_MASTER_REFERENCE.md` says "22 agents"; `desk_registry.py` and `base_agent.py`
docstrings say "23"; the frontend says "25"; `thesis_synthesizer`'s own folder has an
unused `prompts.py` (never imported by `agent.py` — dead code, likely a leftover from
an earlier design that DID call an LLM there). All confirmed by direct inspection —
worth a cleanup pass (see §7, Prompt 0).

---

## 2. Should any agents be combined?

Applying the codebase's *own* stated framework (`AGENTS_MASTER_REFERENCE.md` §1.2:
merge only when no genuinely new evidence pack or governance role is lost) to the
real candidates:

| Candidate pair | Same wave today? | Recommendation | Why |
|---|---|---|---|
| `report_and_notebook_agent` + `ic_memo_writer` (Desk 8) | Yes (parallel) | **Keep separate, but worth a follow-up review** | Both deterministic, both gated on the same `compliance_report.cleared` flag, ~80% same input state. Genuinely different OUTPUT ARTIFACTS (cockpit JSON/exports vs. a 10–15pg IC memo PDF) for different consumers, and failure-isolation matters (a bug in one shouldn't break the other). Candidate for a *shared internal helper* (dedupe the state-reading boilerplate) without merging the registered agents themselves. |
| `devils_advocate` + `verification_agent` (Desk 7) | Yes (parallel) | **Do not merge** | Both deterministic, so no LLM-cost argument for merging — but the whole point of `ADVERSARIAL_CHAIN` is *structural independence* (a governance/audit design goal, explicitly documented as "never merge... that is the entire point"). Merging would remove the separation-of-powers property even though it wouldn't change any number. |
| `risk_catalyst` + `variant_perception_ideation` (Desk 5) | Yes (parallel) | **Keep separate** | Deliberately two different cognitive lenses on the same evidence (chronological/probabilistic risk-mapping vs. contrarian-thesis-generation) — merging would blend two distinct jobs into one prompt/function, which this system's own principle argues against. |
| `financial_integrity` + `market_data_validation` (Desk 4) | Yes (parallel) | **Keep separate** | Different evidence (earnings quality vs. live market-data feed correctness) and different audiences (analyst judgment vs. data-engineering QA). |
| `investment_committee_adjudicator` + `compliance_mnpi_guardrail` (Desk 7) | Sequential (chain) | **Do not merge** | Compliance is explicitly a **legal** gate independent of research quality — it must be able to override a clean research verdict. Same reasoning as devil's-advocate/verification: this is a governance separation, not an efficiency question. |

**Bottom line: no agent pair should be merged for LLM-cost/latency reasons** (since
21 of 25 don't call an LLM at all, there's no cost to save), and the pairs that
*look* mergeable on paper (same wave, overlapping input) were deliberately kept
separate for governance/audit-independence reasons that are more important than
code deduplication. The one real, low-risk opportunity is de-duplicating the
*state-reading boilerplate* between `report_and_notebook_agent` and `ic_memo_writer`
into a shared helper — without merging the two agents/registry entries themselves.

---

## 3. The Decision Registry / context-engineering architecture

Scoped specifically to the 4 agents (+ 3 services) that actually call an LLM —
formalizing and extending the patterns in §1.3, not replacing them.

### 3.1 Decision Registry schema (new `ResearchState` key: `decision_registry`)

```json
{
  "sequence": 9,
  "agent_id": "industry_competitive_context",
  "desk_id": "desk4",
  "timestamp": "2026-07-31T19:12:04Z",
  "decision_summary": "Classified AAPL as Consumer Electronics; identified 6 peers via live Yahoo classification; no LLM-inferred edges beyond the labeled business-description synthesis.",
  "key_facts": [
    {"fact_id": "fact-AAPL-industry", "label": "Industry classification", "value": "Consumer Electronics"}
  ],
  "evidence_refs": ["fact-AAPL-industry", "source_version:sec-0000320193"],
  "confidence": 0.78,
  "warnings": [],
  "prompt_version": "industry_map_v1",
  "context_tokens_used": 612,
  "context_budget_tokens": 4915,
  "supersedes": []
}
```

- Reuses the existing `Annotated[list[dict], operator.add]` reducer pattern already
  used for `agent_runs`/`facts`/`warnings` — no new LangGraph mechanism needed.
- Populated automatically for **every** agent (not just LLM ones) inside
  `BaseAgent.__call__` (the one shared chokepoint all 25 already go through) from
  the `AgentRunResult` it already returns — `decision_summary`/`key_facts` become two
  new *optional* fields on `AgentRunResult`, auto-generated from `result` if an agent
  doesn't supply them explicitly, so this is a strictly additive, backward-compatible
  change (existing 144 tests keep passing without modification).
- `prompt_version`/`context_tokens_used`/`context_budget_tokens` populate only for the
  4 LLM-backed agents (via the context-registry compiler below) — `None` for the 21
  deterministic ones.

### 3.2 Context Registry Compiler (new `agents/context_registry.py`)

The single shared utility that replaces each LLM call site's ad-hoc context curation:

```python
def build_node_context(
    state: ResearchState, *, include_fields: list[str], max_registry_entries: int = 8,
) -> dict:
    """Returns {field: state.get(field) for field in include_fields} (a NAMED
    ALLOWLIST each agent's spec.py declares, never the raw state dump) plus the
    `decision_summary` (never the full result) of the last `max_registry_entries`
    decision_registry entries — the compact, carried-forward memory the user asked
    for, instead of re-serializing every upstream agent's full output into every
    downstream prompt."""
```

- Each LLM-backed agent's `spec.py` gains a `context_fields: list[str]` declaration
  (which `ResearchState` keys it actually needs) — self-documenting, and testable
  (a unit test can assert the allowlist doesn't silently grow unbounded over time).
- Wired together with the *existing* `prompt_budget.check_prompt_budget` — if the
  curated slice is still over budget, the compiler drops the OLDEST
  `decision_registry` summaries first (not raw facts — those are cheap and precise),
  then logs which fields were dropped as a `warnings` entry, never silently truncates
  facts mid-sentence.
- This is the literal implementation of "erase context, but keep a registry of what
  matters, and give that to the next node" — scoped correctly to only the 4 agents
  that need it.

### 3.3 Prompt versioning

Every agent's `prompts.py` (already an established, if inconsistently-used, file
convention) gets one required export per prompt: a `PROMPT_VERSION` string constant
alongside the template, e.g. `INDUSTRY_MAP_V1 = "..."`. The Decision Registry entry
records which version actually ran. This makes "I changed the system prompt for
better accuracy" (your ask) a trackable, comparable event instead of an invisible
code edit — a future eval harness can replay the same real inputs against `V1` vs
`V2` and compare confidence/verification pass-rates.

### 3.4 Temperature — the concrete, low-risk fix

`RealLLMClient.__init__` gains a `temperature: float` parameter (threaded into the
Ollama `"options": {"temperature": ...}` body, OpenAI's/Anthropic's top-level
`"temperature"` field). `ModelRouter.get_client` passes a **per-task-type default**,
not one single global number — a classification/extraction task should be
near-deterministic, but `CRITIQUE` (devil's-advocate-style, if ever LLM-backed in
the future) genuinely benefits from slightly more variation to find a genuinely
different angle:

| TaskType | Proposed default temperature |
|---|---|
| CLASSIFICATION | 0.1 |
| RETRIEVAL | 0.1 |
| SYNTHESIS | 0.2 |
| CRITIQUE | 0.3 |
| FINAL_PROSE | 0.2 |

All far lower than today's implicit provider defaults, and directly matches your
"temperature 0.1 agent intelligence" ask — this alone, with zero other changes, will
measurably reduce output variance on every real LLM call in the system.

### 3.5 Compaction boundaries (new idea, not yet in the codebase)

A "compaction boundary" is a point in the pipeline where a RAW, verbose input
(a parsed filing chunk, a full transcript) has already been distilled into a typed,
compact fact, and nothing downstream should re-read the raw form for prompt purposes
— only for audit (still fully retained in `ResearchState`/the LangGraph checkpoint,
just not re-serialized into later prompts). Concretely:

- After `financial_fact_extraction` runs, no later prompt should ever include
  `document_elements` (the raw parsed tables) again — only `facts` (already typed).
- After `filings_rag`'s hybrid retrieval + extraction produces `filing_narrative_analysis`,
  no later prompt should re-embed retrieved chunk text — only the labeled findings +
  their citations.
- This is enforced simply: the `context_fields` allowlist in §3.2 for every node
  AFTER a compaction boundary just never lists the raw field. No new mechanism
  needed — this is a *convention* for how `context_fields` allowlists should be
  written, backed by a lint-style test that fails if e.g. `thesis_synthesizer`'s
  spec ever lists `document_elements`.

### 3.6 Contradiction detection (extends the existing collision warning)

`merge_state_update`'s current collision warning is a generic string. Extend it (only
for scalar fields both waves *disagree* on, not benign overwrites) into a structured
`state["contradictions"]` entry: `{"field", "agent_a", "value_a", "agent_b", "value_b",
"desk"}` — surfaced explicitly to the Investment Committee desk (7) as a required
review item, rather than a warning buried in a log line. Directly serves "strictly no
hallucinations": two agents disagreeing on a number should be a visible, first-class
event, not a footnote.

---

## 4. Folder structure & naming convention

### Current state (verified 2026-07-31)

> **Update, 2026-07-31 (Prompt 4 executed):** `planning/`, `acquisition/`, and
> `document_fact_intelligence/` below have been renamed to `desk1_mandate_coverage/`,
> `desk2_data_acquisition/`, and `desk3_document_fact_extraction/` respectively, with
> their agent subfolders renamed to `agent_01_research_planner` ..
> `agent_07_transcript_intelligence` per §4's "Recommended new naming" below. This is
> a pure path/name rename only — `AgentSpec.id` strings, `desk_registry.py`'s data,
> and all execution/dependency behavior are byte-for-byte unchanged (verified via
> `pytest -q`, `test_desk_registry.py`, the e2e smoke test, and a live
> `GET /v1/research-runs/desks` check against a freshly started server). The tree
> below is left as-is as the historical "before" record; see §4's "Recommended new
> naming" section for the current, actual structure of these 3 desks.
> `integrity_context/`/`strategy_insight/`/`modeling_valuation/`/`governance/`/
> `decision_ops/` are NOT yet renamed (Prompts 5-8).
>
> **Update, 2026-07-31 (Prompt 5 executed):** `integrity_context/` below has been
> renamed to `desk4_fundamental_context_research/` (`agent_08_financial_integrity`
> .. `agent_11_macro_esg_signal_context`), AND `governance/market_data_validation/`
> has been moved into it as `agent_12_market_data_validation` — the real
> folder/desk-registry drift noted below is now fixed. Same verification bar as
> Prompt 4 (`pytest -q`, `test_desk_registry.py`, e2e smoke test, live
> `GET /v1/research-runs/desks`), plus the additional Desk 4-specific check that
> `desk_registry.get_desk('desk4').agents` still lists `market_data_validation`
> correctly. `strategy_insight/`/`modeling_valuation/`/`governance/`/`decision_ops/`
> are NOT yet renamed (Prompts 6-8) — `governance/` now has only its real 5
> agents (`market_data_validation` no longer lives there).
>
> **Update, 2026-07-31 (Prompt 6 executed):** `strategy_insight/` and
> `modeling_valuation/` below have been renamed to `desk5_strategy_idea_generation/`
> (`agent_13_risk_catalyst`, `agent_14_variant_perception_ideation`) and
> `desk6_modeling_valuation/` (`agent_15_operating_model`,
> `agent_16_valuation_scenario`) respectively. Same verification bar as Prompts 4-5
> (`pytest -q` — 173 passed/2 xfailed, unchanged; `test_desk_registry.py`; e2e smoke
> test; live `GET /v1/research-runs/desks`). Only `governance/`/`decision_ops/`
> remain unrenamed (Prompts 7-8).
>
> **Update, 2026-07-31 (Prompt 7 executed):** `governance/` below has been renamed
> to `desk7_investment_committee/` (`agent_17_thesis_synthesizer` ..
> `agent_21_compliance_mnpi_guardrail`) — a pure rename/move only; confirmed all 5
> agents' `AgentSpec.depends_on` chains are byte-for-byte identical to before,
> still referencing agent_id strings (never paths), so the adversarial chain's
> execution order/dependency wiring is untouched. Same verification bar as
> Prompts 4-6 (`pytest -q` — 173 passed/2 xfailed, unchanged; `test_desk_registry.py`;
> e2e smoke test; live `GET /v1/research-runs/desks`). Only `decision_ops/` remains
> unrenamed (Prompt 8, which also runs the final full regression pass).
>
> **Update, 2026-07-31 (Prompt 8 executed — FULL FOLDER MIGRATION COMPLETE):**
> `decision_ops/` below has been renamed to
> `desk8_decision_distribution_monitoring/` (`agent_22_portfolio_sizing_advisor`,
> `agent_23_report_and_notebook_agent`, `agent_24_ic_memo_writer`, and the standing
> `agent_S1_continuous_monitoring_agent` — deliberately "S1", not "25", since it
> never runs inside the on-demand 1-24 sequence). **This completes the entire
> 5-prompt folder migration (Prompts 4-8)** — every one of `agents/specialists/`'s
> 8 category folders now matches the "Recommended new naming" tree below exactly;
> the tree immediately following this callout (showing the OLD `planning/`/
> `acquisition/`/etc. names) is left as-is as a historical "before" record only,
> it no longer reflects the real filesystem. Final regression pass: `pytest -q`
> — **173 passed, 2 xfailed**, the exact same count as immediately before Prompt 4
> was first started, confirming the whole 5-prompt migration was a complete no-op
> on test outcomes; `test_desk_registry.py` and the e2e smoke test both
> individually green; and a REAL live run through the actual FastAPI server
> (`POST /v1/research-runs`, `run_mode="auto"`) completed successfully with all
> 24 on-demand agents present, **0 failed agent_runs** (20 `ok` + 4 `abstained`),
> 24 decision_registry entries, 0 contradictions, and the expected fail-closed
> `compliance_report.cleared=False`/`requires_approval=True` gate. Note: the
> live-run verification used the TXN fixture ticker rather than a real one —
> two consecutive attempts against a real ticker (AAPL) both failed identically
> with a genuine external-HTTP read timeout inside `entity_universe_resolver`
> (the first agent needing outbound network access), immediately after
> `research_planner` — the one network-free agent — succeeded both times. This
> is a sandbox network limitation in this specific session (confirmed via
> `USE_REAL_DATA_SOURCES=true` requiring live outbound calls the sandbox
> couldn't complete), not a regression from the rename: no agent logic was
> touched by Prompts 4-8, and the fixture-based run above exercises the exact
> same renamed 24-agent chain end-to-end successfully.

The 8 category folders **already exist** and already correspond almost exactly to
the 8 desks — your "8 folders, each with individual agent folders" instinct is
already how this is built:

```
agents/specialists/
  planning/                    -> Desk 1 (2 agents) ✓ clean match
  acquisition/                 -> Desk 2 (2 agents) ✓ clean match
  document_fact_intelligence/  -> Desk 3 (3 agents) ✓ clean match
  integrity_context/           -> Desk 4, MISSING market_data_validation (4 of 5 agents)
  strategy_insight/            -> Desk 5 (2 agents) ✓ clean match
  modeling_valuation/          -> Desk 6 (2 agents) ✓ clean match
  governance/                  -> Desk 7 (5 agents) PLUS market_data_validation (6 total)
  decision_ops/                -> Desk 8 (3 on-demand + 1 standing) ✓ clean match
```

**One real bug found**: `market_data_validation` conceptually belongs to Desk 4 (per
`desk_registry.py`, the system's own "single source of truth") but its folder lives
under `governance/` (Desk 7's folder) instead of `integrity_context/` (Desk 4's
folder) — a real drift between the folder layout and the desk registry.

### Recommended new naming (desk-numbered parents + agent-numbered children)

```
agents/specialists/
  desk1_mandate_coverage/
    agent_01_research_planner/
    agent_02_entity_universe_resolver/
  desk2_data_acquisition/
    agent_03_acquisition_orchestrator/
    agent_04_expert_notes_ingestion/
  desk3_document_fact_extraction/
    agent_05_document_intelligence/
    agent_06_financial_fact_extraction/
    agent_07_transcript_intelligence/
  desk4_fundamental_context_research/
    agent_08_financial_integrity/
    agent_09_industry_competitive_context/
    agent_10_filing_narrative_analyst/
    agent_11_macro_esg_signal_context/
    agent_12_market_data_validation/        <- moved here (bug fix)
  desk5_strategy_idea_generation/
    agent_13_risk_catalyst/
    agent_14_variant_perception_ideation/
  desk6_modeling_valuation/
    agent_15_operating_model/
    agent_16_valuation_scenario/
  desk7_investment_committee/
    agent_17_thesis_synthesizer/
    agent_18_devils_advocate/
    agent_19_verification_agent/
    agent_20_investment_committee_adjudicator/
    agent_21_compliance_mnpi_guardrail/
  desk8_decision_distribution_monitoring/
    agent_22_portfolio_sizing_advisor/
    agent_23_report_and_notebook_agent/
    agent_24_ic_memo_writer/
    agent_S1_continuous_monitoring_agent/    <- "S" = standing, not part of the 1-24 on-demand sequence
```

Why this satisfies both things you asked for at once: you get **8 folders** (desk
parents) *and* you can still literally see **24 numbered agent folders** (25 counting
the standing one) — the number tells you execution order, the name tells you
purpose, and the desk-numbered parent tells you which review checkpoint it belongs
to, all without needing to cross-reference `desk_registry.py` to know what
"`integrity_context`" or "`governance`" means.

Each agent folder keeps its existing internal convention (`agent.py`, `spec.py`,
`schemas.py`, and `prompts.py` **only** for the 4 that actually call an LLM — no
more dead unused `prompts.py` files like `thesis_synthesizer`'s today).

This is a mechanical rename (updating `__init__.py` imports in each desk folder,
`registry.py`'s registration calls, and the contract test
`test_desk_registry_matches_graph.py`) — safe and reversible, but touches ~24
folders and every import path, so it's scoped as its own prompt in §7 rather than
done in this pass.

---

## 5. Full flow

```mermaid
flowchart TD
    subgraph Desk1["Desk 1: Mandate & Coverage (sequential)"]
        A1[agent_01 research_planner]
        A2[agent_02 entity_universe_resolver]
        A1 --> A2
    end
    subgraph Desk2["Desk 2: Data Acquisition (parallel)"]
        A3[agent_03 acquisition_orchestrator]
        A4[agent_04 expert_notes_ingestion]
    end
    subgraph Desk3["Desk 3: Document & Fact Extraction (gated parallel)"]
        A5[agent_05 document_intelligence] --> A6[agent_06 financial_fact_extraction]
        A5 --> A7[agent_07 transcript_intelligence - LLM]
        A6 --> R3[deterministic reconciliation + comparison]
        A7 --> R3
    end
    subgraph Desk4["Desk 4: Fundamental & Context Research (parallel x5)"]
        A8[agent_08 financial_integrity]
        A9[agent_09 industry_competitive_context - LLM]
        A10[agent_10 filing_narrative_analyst - LLM via filings_rag]
        A11[agent_11 macro_esg_signal_context]
        A12[agent_12 market_data_validation]
    end
    subgraph Desk5["Desk 5: Strategy & Idea Generation (parallel)"]
        A13[agent_13 risk_catalyst]
        A14[agent_14 variant_perception_ideation]
    end
    subgraph Desk6["Desk 6: Modeling & Valuation (sequential)"]
        A15[agent_15 operating_model] --> Gate6{deterministic reconciliation gate} --> A16[agent_16 valuation_scenario]
    end
    subgraph Desk7["Desk 7: Investment Committee (adversarial chain - never parallelized)"]
        A17[agent_17 thesis_synthesizer] --> Wave7{parallel wave}
        Wave7 --> A18[agent_18 devils_advocate]
        Wave7 --> A19[agent_19 verification_agent]
        A18 --> A20[agent_20 investment_committee_adjudicator]
        A19 --> A20
        A20 --> A21[agent_21 compliance_mnpi_guardrail]
    end
    subgraph Desk8["Desk 8: Decision, Distribution & Monitoring (parallel)"]
        A22[agent_22 portfolio_sizing_advisor]
        A23[agent_23 report_and_notebook_agent]
        A24[agent_24 ic_memo_writer]
        AS1["agent_S1 continuous_monitoring_agent (standing - own schedule)"]
    end

    DR[(Decision Registry - JSON, append-only)]

    Desk1 --> Desk2 --> Desk3 --> Desk4 --> Desk5 --> Desk6 --> Desk7 --> Desk8
    Desk1 -.append.-> DR
    Desk2 -.append.-> DR
    Desk3 -.append.-> DR
    Desk4 -.append.-> DR
    Desk5 -.append.-> DR
    Desk6 -.append.-> DR
    Desk7 -.append.-> DR
    Desk8 -.append.-> DR
    DR -.curated slice + prompt_version + temp=0.1.-> A9
    DR -.curated slice + prompt_version + temp=0.1.-> A7
    DR -.curated slice + prompt_version + temp=0.1.-> A10
```

---

## 6. What this plan deliberately does NOT change

- **`ResearchState`, checkpointing, LangGraph node wiring**: untouched — the Decision
  Registry is an *additive* field, not a replacement.
- **The 21 deterministic agents' actual logic**: untouched — no LLM/context work
  needed there.
- **Desk 7's adversarial sequencing**: explicitly preserved, not merged (§2).
- **The existing static Excel export, financial model engine, or the new
  live-formula model pipeline**: unrelated to this effort.

---

## 7. Extensive, self-contained prompts for follow-up sessions

Each prompt below is written to be **pasted as a complete, standalone message** —
either to me in a fresh session, or to any other coding agent working in this repo.
Each one restates its own context, exact scope, exact technical spec, edge cases,
and acceptance criteria, so it does not depend on the rest of this conversation
still being in context. Paste them **in order** — later ones assume earlier ones
are already done (each says so explicitly).

Every prompt ends with the same non-negotiable guardrail, repeated inline: **run the
full test suite (`pytest -q` from `agent/`, with `.venv` active) before and after,
and do not proceed if the count regresses from 144 passed / 2 xfailed.**

---

<a id="prompt-0"></a>

### Prompt 0 — Cleanup pass: fix every stale agent-count reference

```
Context: this repo's own documentation and code comments disagree with each other
and with reality about how many specialist agents exist. A full code-level audit
(desk_registry.py enumeration, cross-checked against a live real-ticker run's actual
agent_runs count and the frontend's own displayed text) established the TRUE number:
24 agents run in the on-demand research pipeline, plus 1 standing agent
(continuous_monitoring_agent, which runs on its own separate schedule via
continuous_ops_graph.py and is never part of a live ResearchRun) = 25 total.

Your task: update every one of the following 18 confirmed stale references (found via
grep for "22 agents|23 agents|22 specialist" across the whole repo) to say the
correct number. Do not just find-and-replace "22"->"24" blindly — read each
sentence's exact phrasing first, since some need slightly different wording (e.g.
"22 agents that make a judgment call" in AGENTS_MASTER_REFERENCE.md is describing the
ORIGINAL target architecture's philosophy, not a literal count you should just bump —
read section 1 of that same doc and decide whether the number itself should change to
24, or whether a short editorial note should be added acknowledging the actual build
grew to 24 on-demand + 1 standing agent as it was implemented, without rewriting the
whole philosophical argument). Exact locations to fix:

1. agent/main.py line 2 — "all 22 agents in-process" -> update count
2. agent/README.md line 15 — "22 specialist" in the src/agents/ tree description
3. agent/src/agents/base_agent.py line 4 (module docstring) — "confidence rubric
   shared by all 22 specialist agents" -> update, AND check for a second inline
   comment further down in the same file mentioning "23 agents' invocations" (search
   the whole file, don't assume there's only one)
4. agent/src/agents/orchestration/desk_registry.py — module docstring says "this
   system's 23 LLM-backed agents" -> this phrasing is doubly wrong: it's not "23" AND
   most of them aren't "LLM-backed" (only 4 of 25 actually call a language model —
   see docs/agent_modularization_plan.md section 1.2). Reword this docstring to say
   something accurate like "this system's 24 on-demand agents (plus 1 standing) onto
   8 research desks."
5. agent/src/agents/orchestration/desk_registry.py line ~112 — research_planner's
   DeskAgent role text says "decides which of the other 22 agents" -> update to 24
6. agent/src/agents/specialists/__init__.py line 1 — "All 22 specialist agents,
   grouped into 8 tiers" -> update count (and consider whether "tiers" should say
   "desks" instead, matching desk_registry.py's own current terminology — check if
   "tier" is used elsewhere as a synonym for "desk" before renaming, to avoid
   breaking a term that's intentionally used two ways)
7. agent/src/agents/state.py line 14 (module docstring) — "of the 22 agents'
   AgentRunResult.result dicts" -> update count
8. agent/src/api/routers/research_runs.py line 23 — "silently runs all 23 agents
   end to end" -> update count
9. agent/src/api/routers/research_runs.py line ~306 — "fires for every one of the 23
   agents' invocations" -> update count
10. agent/src/cli/validate_research_run.py line 2 — "which of the 22 specialist
    agents would fan out" -> update count
11. agent/src/fixtures/demo_company.py line 2 — "so all 22 agents can run fully
    end-to-end" -> update count
12. docs/adr/0001-orchestration-langgraph.md line 18 — "right-sized to 22 agents" ->
    update count (this is an ADR — read the surrounding paragraph; if it's describing
    a decision made AT THE TIME with 22 as the number, consider adding a short
    "Update" note at the bottom of the ADR instead of silently rewriting history —
    ADRs are meant to be historical records; check how other ADRs in this repo
    handle later corrections before deciding)
13. docs/AGENTS_MASTER_REFERENCE.md — FOUR separate "22" mentions (lines 8, 19, 93,
    157). This file explicitly frames itself as "the single source of truth for how
    many agents this system needs" — read the whole document's section 1 argument
    first. Decide whether to (a) update the number to 24 throughout and add a short
    note explaining the growth from 22 to 24 during implementation (two agents that
    weren't in the original blueprint - filing_narrative_analyst and
    market_data_validation and ic_memo_writer - were added; verify exactly which
    ones by diffing this doc's own agent list against desk_registry.py's real list),
    or (b) leave the philosophical "22" as the original target number and add ONE
    clear callout box near the top noting the actual shipped system has 24+1. Prefer
    option (b) if the document reads as a historical/rationale document elsewhere
    (check for other "revision note" callouts already in the file - it has at least
    one at the very top already, follow that existing pattern).
14. docs/product_spec.md line 76 — "right-sized to 22 agents, one folder per agent"
    -> update count
15. docs/project_structure.md line 31 — "22 specialist" in the tree description ->
    update count

Also: agents/specialists/governance/thesis_synthesizer/ has an unused prompts.py file
(confirmed via grep - agent.py never imports from .prompts). Delete this dead file.

Acceptance criteria:
- Re-run the same grep (`grep -rn "22 agents\|23 agents\|22 specialist" .` from the
  repo root, excluding node_modules/.venv/.git) and confirm zero remaining stale
  hits, OR confirm any remaining "22" is a deliberate historical reference with a
  clear note explaining why it wasn't changed (per item 13's option (b)).
- From agent/ with .venv active: `pytest -q` must still show "144 passed, 2 xfailed"
  (this is a text-only change, so the count must be identical, not just "no new
  failures").
- grep for "thesis_synthesizer" + "prompts" to confirm nothing else references the
  deleted file before removing it.
```

---

<a id="prompt-1"></a>

### Prompt 1 — Decision Registry core (foundation; no folder changes, no LLM changes)

```
Context: this repo has a LangGraph-based, 8-desk, 25-agent equity research pipeline.
Every agent already extends a shared BaseAgent class (agent/src/agents/base_agent.py)
whose __call__ method is the ONE place every single agent invocation passes through
(parallel-wave or sequential, no exceptions) — it validates required inputs, runs the
agent's execute() under a resilience wrapper (timeout/retry), applies deterministic
validators, and returns a partial ResearchState update. state["agent_runs"] already
accumulates every AgentRunResult as a list (via an operator.add-reduced field in
agent/src/agents/state.py).

Goal: add a NEW, richer, append-only "Decision Registry" alongside the existing
agent_runs list — an explicit, informative, structured JSON trail of every decision
made across the whole run, designed to be readable both by a human (for audit) and
by a LATER LLM-backed agent's prompt (a compact "what happened so far" digest, so a
downstream prompt doesn't need the FULL raw state dumped into it — see Prompt 2 for
how this gets consumed; this prompt ONLY builds the registry, it does not change any
prompt yet).

Exact schema (one entry per agent invocation), as a plain dict (not a new Pydantic
model unless the rest of domain/runs.py already prefers Pydantic - check that file's
existing convention for AgentRunResult/AgentSpec first and match it):

{
  "sequence": <int, 1-based, monotonically increasing across the whole run>,
  "agent_id": "<str, matches AgentSpec.id>",
  "desk_id": "<str, resolved via agents.orchestration.desk_registry.desk_for_agent(agent_id) - None if not found>",
  "timestamp": "<ISO-8601 UTC string>",
  "status": "<str, copied from AgentRunResult.status>",
  "decision_summary": "<str, one or two plain-English sentences - see auto-generation rule below>",
  "key_facts": [ { "fact_id": "<str or null>", "label": "<str>", "value": <any JSON-serializable> }, ... ],
  "evidence_refs": [ "<str>", ... copied from AgentRunResult.evidence_refs ],
  "confidence": <float or null, copied from AgentRunResult.confidence>,
  "warnings": [ "<str>", ... copied from AgentRunResult.warnings ],
  "prompt_version": null,
  "context_tokens_used": null,
  "context_budget_tokens": null
}

(prompt_version/context_tokens_used/context_budget_tokens stay null for now — Prompt
2 populates them for the 4 LLM-backed agents only. Do not implement that here.)

Implementation steps:
1. In agent/src/domain/runs.py, add two NEW OPTIONAL fields to AgentRunResult:
   `decision_summary: str | None = None` and `key_facts: list[dict] | None = None`.
   These must be optional with safe defaults so every existing agent.py's
   `AgentRunResult(...)` constructor call (there are 25 of them) keeps working
   completely unmodified — do not touch any individual agent.py file in this prompt.
2. In agent/src/agents/state.py, add a new top-level key:
   `decision_registry: Annotated[list[dict], operator.add]` (same reducer pattern
   already used for agent_runs/facts/warnings — copy that exact pattern). Add a
   short comment explaining what it's for and pointing at
   docs/agent_modularization_plan.md section 3.1.
3. In agent/src/agents/base_agent.py's BaseAgent.__call__, AFTER result is fully
   built (status/confidence/latency/attempts all set) and AFTER
   self._run_deterministic_validators(result) runs, but BEFORE the existing
   agent-progress-hook code, build ONE decision_registry entry per the schema above
   and add it to the returned partial-state dict under the "decision_registry" key
   (as a single-element list, so the operator.add reducer appends it correctly across
   waves — do NOT return a bare dict, it must be `[entry]`).
   - sequence: you'll need a way to know "how many entries exist so far" to assign
     the next sequence number. Since BaseAgent.__call__ only receives the CURRENT
     state snapshot (not the future merged one), use
     `len(state.get("decision_registry") or []) + 1` as a best-effort sequence
     number — note in a comment that under true parallel execution within one wave,
     two agents starting from the SAME state snapshot could compute the same
     sequence number (this is a known, accepted limitation - sequence is for human
     readability/rough ordering, not a strict monotonic guarantee across a wave;
     `timestamp` is the tie-breaker if exact ordering ever matters). Do not attempt
     to build true cross-wave atomic counters — that's out of scope and would need
     a shared mutable counter that doesn't fit LangGraph's functional state-update
     model cleanly.
   - decision_summary auto-generation (only used if the agent's own AgentRunResult
     didn't set decision_summary explicitly): build a single sentence like
     f"{agent_id} finished with status={status}" then, if confidence is not None,
     append f", confidence={confidence:.2f}"; if warnings is non-empty, append
     f" ({len(warnings)} warning(s))". Keep this generic and short — it is a
     fallback, not meant to be as good as an agent-supplied summary.
   - key_facts auto-generation (only used if the agent didn't set key_facts
     explicitly): default to an empty list `[]` — do NOT try to auto-guess which
     fields in `result.result` are "key facts", that would be a fragile heuristic;
     it's fine for most entries to have an empty key_facts list until Prompt 2/later
     work opts specific agents into supplying real ones.
4. A hook-failure-safety requirement: building the decision_registry entry must
   NEVER raise and break a real research run - wrap the entry-construction logic in
   a try/except that logs and falls back to a minimal entry
   ({"sequence":..., "agent_id":..., "status": status, "decision_summary": "(failed
   to build decision registry entry)", ...all other fields null/empty}) on any
   unexpected error, mirroring how the existing agent-progress-hook code right below
   it already swallows and logs hook failures rather than ever crashing a real run.

Testing requirements:
- Add a new unit test (agent/tests/unit/, follow existing test file naming/location
  conventions in that folder) asserting: given a fake AgentSpec + a fake execute()
  that returns a known AgentRunResult, calling BaseAgent.__call__ produces a partial
  state dict containing exactly one decision_registry entry, with all fields
  correctly populated from the AgentRunResult, and that decision_summary is
  auto-generated correctly when not supplied.
- Add a second test confirming an agent that DOES supply decision_summary/key_facts
  explicitly has those values preserved verbatim, not overwritten by the
  auto-generation fallback.
- Do NOT modify any of the 25 existing agent.py files, any existing test file's
  assertions, or graph.py's wiring in this prompt — this must be a strictly additive
  change. Confirm by running the full suite: from agent/ with .venv active,
  `pytest -q` must show "144 passed, 2 xfailed" PLUS your new test(s) passing (so
  the total passed count will be 144 + however many new tests you added — do not
  expect exactly 144 anymore, but zero of the ORIGINAL 144 may fail or change
  behavior).
- Also run `pytest tests/e2e/test_full_pipeline_smoke.py -v` specifically and
  confirm it still passes and that the final state now genuinely contains a
  non-empty `decision_registry` list with one entry per real agent that ran in that
  test (print/inspect its length if useful during development, but don't leave debug
  prints in the final code).
```

---

<a id="prompt-2"></a>

### Prompt 2 — Context Registry Compiler + per-task-type temperature (the 4 LLM-backed call sites only)

```
Context: this repo's 25-agent pipeline has exactly 4 agents that call a language
model at all (verified by an exhaustive grep for "ModelRouter().get_client(" across
the whole src/ tree, cross-checked by direct code inspection of several
non-LLM agents): industry_competitive_context (2 call sites, both TaskType.SYNTHESIS),
transcript_intelligence (TaskType.CLASSIFICATION), continuous_monitoring_agent
(TaskType.CLASSIFICATION), and filing_narrative_analyst (indirectly, via
src/services/filings_rag/service.py's 2 call sites, both TaskType.RETRIEVAL). The
other 21 agents are fully deterministic Python and must NOT be touched by this
prompt. This prompt assumes Prompt 1 (the Decision Registry core) is already merged.

Also confirmed: agent/src/agents/llm_client.py currently never sets a `temperature`
parameter for any of the three providers it supports (Ollama/OpenAI/Anthropic) —
every real call runs at that provider's/model's implicit default (typically
0.7-1.0), which is NOT the low-temperature, near-deterministic behavior wanted.

Part A - temperature (do this part first, it's small and independent):
1. In agent/src/agents/llm_client.py, add a `temperature: float = 0.2` parameter to
   RealLLMClient.__init__ (store as self.temperature), and thread it into each
   provider's request body:
   - OpenAI (_call_openai): add `"temperature": self.temperature` to the JSON body
     alongside the existing "model"/"messages"/"response_format" keys.
   - Anthropic (_call_anthropic): add `"temperature": self.temperature` to the JSON
     body alongside "model"/"max_tokens"/"messages".
   - Ollama (_call_ollama): add `"options": {"temperature": self.temperature}` to
     the JSON body alongside "model"/"messages"/"format"/"stream".
2. In agent/src/agents/routing.py, ModelRouter.get_client needs a way to pick a
   temperature per TaskType. Add a module-level mapping:
   ```
   _TASK_TYPE_TEMPERATURE: dict[TaskType, float] = {
       TaskType.CLASSIFICATION: 0.1,
       TaskType.VISION_TABLE: 0.1,
       TaskType.RETRIEVAL: 0.1,
       TaskType.SYNTHESIS: 0.2,
       TaskType.CRITIQUE: 0.3,
       TaskType.FINAL_PROSE: 0.2,
   }
   _DEFAULT_TEMPERATURE = 0.2
   ```
   Then, everywhere `get_client` currently constructs a `RealLLMClient(...)` (there
   are 3 such construction call sites in that file — the CONFIDENTIAL_INTERNAL
   branch, the "provider == ollama" branch, and the generic cloud-provider branch at
   the end), pass `temperature=_TASK_TYPE_TEMPERATURE.get(task_type, _DEFAULT_TEMPERATURE)`
   through to the constructor. MockLLMClient needs no change (it ignores prompts
   entirely already).
3. Do not change MockLLMClient, do not change any agent.py file for this part, do
   not change the mock/fixture test paths.
4. Testing: agent/tests/contract/test_llm_client.py already exercises
   ModelRouter().get_client(...) - extend it with a new assertion that the returned
   RealLLMClient's temperature attribute matches the expected value for at least
   TaskType.CLASSIFICATION (expect 0.1) and TaskType.CRITIQUE (expect 0.3). Also add
   a test on RealLLMClient directly (construct one with temperature=0.15 and a
   fake/mocked httpx client, or inspect the constructed request body some other way
   consistent with how that test file already mocks httpx) confirming the built
   request body for at least one provider actually includes the temperature value in
   the right place (top-level "temperature" key for OpenAI/Anthropic, nested
   "options.temperature" for Ollama).

Part B - the Context Registry Compiler:
1. Create a new file agent/src/agents/context_registry.py with one function:
   ```
   def build_node_context(
       state: ResearchState, *, include_fields: list[str], max_registry_entries: int = 8,
   ) -> dict:
       """Returns a compact dict: only the explicitly-named `include_fields` pulled
       from `state` (never the full state), plus a "recent_decisions" key containing
       the `decision_summary` (never the full entry - not evidence_refs, not
       key_facts) of the most recent `max_registry_entries` entries in
       state["decision_registry"]. This is the ONLY sanctioned way an LLM-backed
       agent should read `state` when building its prompt - it must never serialize
       `state` directly into a prompt string."""
   ```
   Also add a second function in the same file:
   ```
   def context_to_prompt_text(context: dict) -> str:
       """Renders the dict `build_node_context` returned into a plain-text block
       suitable for embedding in a prompt (e.g. simple 'Key: value' lines per field,
       and a short numbered list for recent_decisions) - keep this simple and
       readable, not a raw json.dumps of the whole thing (a human-readable digest is
       both more token-efficient AND easier for a small local model to actually use
       correctly than a deeply-nested JSON blob)."""
   ```
2. Add a `context_fields: list[str] = []` field to AgentSpec (agent/src/domain/runs.py
   - check its exact current shape first) - this is the explicit, self-documenting
   allowlist of which ResearchState keys a given agent's prompt is allowed to pull
   from. Give it an empty-list default so none of the 21 deterministic agents' specs
   need to change.
3. Wire `build_node_context` + `context_to_prompt_text` into the 4 real LLM call
   sites' prompt-building code (read each file's current prompt-construction logic
   first, then replace whatever ad-hoc field-selection it currently does with a call
   to build_node_context using that specific agent's own context_fields list from its
   spec.py):
   - industry_competitive_context/agent.py's `_real_context` method (the
     `_synthesize_industry_map`-style real-ticker path) - context_fields should
     include at minimum whatever real fields it currently reads (profile/business
     description fields) - check the current code to get this list right, don't
     guess. Keep the existing 700-character business-description cap - it's a good,
     already-working practice, just make sure it composes cleanly with the new
     context builder rather than being replaced by it.
   - transcript_intelligence/agent.py
   - continuous_monitoring_agent/agent.py
   - filings_rag/service.py's two call sites (these are service-level, not
     agent-level, so they don't have an AgentSpec.context_fields to read from -
     instead, define the allowlist as a small module-level constant right there in
     filings_rag/service.py, e.g. `_CONTEXT_FIELDS_FOR_EXTRACTION = [...]`, and use
     the same build_node_context/context_to_prompt_text functions with that
     constant).
4. Also wire in `prompt_budget.check_prompt_budget` at each of these 4 sites (if not
   already called there - check first) using the text from context_to_prompt_text
   plus whatever system prompt is used, and if over budget, drop the OLDEST entries
   from "recent_decisions" first (not real facts/fields) and recheck, logging a
   warning listing what was dropped, before falling back to the caller's existing
   over-budget handling (check what each site currently does on a budget failure -
   probably just logs and proceeds, per that module's own docstring that it never
   auto-truncates FACTS, only being conservative about dropping already-summarized
   history is safe to automate).
5. Add prompt versioning: in whichever prompts.py file each of these 4 call sites
   uses (create one if it doesn't exist yet, following the existing file-naming
   convention seen in other agent folders like thesis_synthesizer's - even though
   that one turned out to be unused/deleted in Prompt 0, the STRUCTURE - a
   `prompts.py` sibling file - is the right convention to follow), add a
   `PROMPT_VERSION = "v1"` string constant next to each prompt template, and record
   it in the decision_registry entry your agent's AgentRunResult should now set (via
   the decision_summary/key_facts optional fields from Prompt 1 - you may need to add
   a THIRD optional field to AgentRunResult here, `prompt_version: str | None = None`,
   and thread it through BaseAgent.__call__'s decision_registry entry construction
   from Prompt 1 - update that method's entry-building code to read
   `result.prompt_version` if the field is present).
6. Compaction-boundary lint test: add a test asserting that no agent whose
   AgentSpec.depends_on (directly or transitively - check registry.py for how
   dependency resolution works) includes financial_fact_extraction has
   "document_elements" in its context_fields list (this proves the compaction
   boundary from section 3.5 of docs/agent_modularization_plan.md is respected -
   raw parsed document elements should never be re-read for prompt purposes once
   typed facts exist).

Guardrails - do NOT do in this prompt:
- Do not change the TXN fixture path's mock_fn functions in any of the 4 agents -
  MockLLMClient still ignores the prompt entirely, so context_to_prompt_text's
  output still needs to be built (for the Decision Registry entry / real-provider
  path) but its exact content doesn't affect fixture-mode test outcomes.
- Do not touch any of the other 21 agents' files.
- Do not implement contradiction detection (that's Prompt 3) or any folder
  renaming (that's Prompts 4-8) in this prompt.

Acceptance criteria:
- From agent/ with .venv active: `pytest -q` shows zero regressions versus
  whatever the passed/xfailed count was after Prompt 1 (should only ever grow, never
  shrink or newly-fail).
- `pytest tests/e2e/test_full_pipeline_smoke.py -v` still passes.
- Manually verify (a small ad-hoc script or REPL check is fine, don't need to keep
  it) that build_node_context on a real ResearchState-shaped dict only returns the
  fields you explicitly named, never the whole state.
```

---

<a id="prompt-3"></a>

### Prompt 3 — Contradiction detection (extends existing collision-warning logic)

```
Context: agent/src/agents/orchestration/_wave_runner.py's merge_state_update already
detects when two agents in the same parallel wave write different values to the same
scalar state key, and currently appends a plain warning STRING like
"state merge collision on key '<key>' (wave=[...])" to state["warnings"]. This prompt
assumes Prompts 1 and 2 are already merged (it reuses the decision_registry concept).

Goal: replace the plain string warning (only for the genuine-collision branch - the
"else" branch of the existing if/elif/else in merge_state_update - do not touch the
list-concatenation branch or the "not set yet"/None-placeholder branch, both of which
are correct as-is and are not contradictions) with a structured entry appended to a
NEW ResearchState key, `contradictions: Annotated[list[dict], operator.add]`, with
this shape:
{
  "field": "<the colliding state key>",
  "agent_a": "<best-effort: the wave's agent_ids, since merge_state_update currently
              only knows the WAVE's agent id list via collision_context, not which
              SPECIFIC agent produced which value - see note below>",
  "value_a": <the value already in `merged` before this update>,
  "value_b": <the new colliding `value`>,
  "wave": "<the collision_context string, e.g. 'wave=[...]'>",
  "detected_at": "<ISO-8601 UTC timestamp>"
}

Important nuance to actually resolve, not hand-wave: merge_state_update as it exists
today is called once per WAVE with an already-merged dict of ALL agents' outputs in
that wave (see run_wave's loop: `for partial in results: merged =
merge_state_update(merged, partial, ...)`), so by the time a collision is detected,
you only know "some agent in this wave disagrees with some earlier-processed agent in
this same wave" - not the two specific agent_ids. Fixing this properly means changing
run_wave to merge one result at a time while tracking which agent_id produced each
partial dict (results and agent_ids are already both available as parallel lists in
run_wave - `agent_ids` param and `results` from asyncio.gather are in the same order),
threading the CURRENT agent_id into merge_state_update's collision_context or a new
parameter, so a real contradiction entry can correctly name both agent_ids. Implement
this properly (don't fake it with the wave's full id list as a placeholder for both
sides - that is a real quality regression from what's being asked here, be a good
architect and thread the actual pair through even if it takes touching both
_wave_runner.py functions).

Implementation steps:
1. Add `contradictions: Annotated[list[dict], operator.add]` to ResearchState in
   agent/src/agents/state.py, with a short comment cross-referencing this prompt/
   docs/agent_modularization_plan.md section 3.6.
2. Modify merge_state_update's signature to optionally accept the producing agent_id
   for `update` (e.g. `producer_agent_id: str | None = None`), and modify run_wave to
   pass each result's actual agent_id when folding it into `merged`, plus track (in a
   local dict keyed by field name) which agent_id last wrote each scalar key, so a
   real collision can report BOTH agent_ids correctly, not just the wave's full list.
3. On a genuine scalar collision (the existing else branch), instead of only
   appending a warning string, ALSO build and append one contradiction entry (as
   above) to a "contradictions" list in the merged dict (following the exact same
   list-append pattern already used for "warnings" in that same branch - do not
   remove the existing warning string append, keep both; the warning is for
   quick-scan visibility, the contradiction entry is for structured/queryable
   detail).
4. Frontend: locate the Desk 7 (Investment Committee) page component (check
   frontend/src/app or frontend/src/components/cockpit for how other desk-specific
   review-focus content is rendered - follow whatever existing pattern shows e.g.
   compliance_report or adjudication data on that page) and add a new section
   rendering state["contradictions"] (if non-empty) as a clearly-flagged "Detected
   Contradictions - Review Required" list, each item showing field/both agents/both
   values. Match the existing visual style (this repo uses a dark, professional
   cockpit UI - check an existing component like the one rendering compliance
   warnings for the right Tailwind classes/structure to copy).

Testing requirements:
- Add a unit test to agent/tests/unit/ (find the existing test file for
  _wave_runner.py if one exists, else create one following the naming convention of
  sibling test files) that runs two fake agents in the same wave whose fake
  AgentRunResults deliberately disagree on one scalar field, and asserts exactly one
  contradiction entry is produced with the correct field name, both correct
  agent_ids, and both correct values.
- Confirm the list-concatenation branch (e.g. two agents both contributing to
  `warnings` or `agent_runs`) still produces ZERO contradiction entries - this must
  never fire for legitimately-additive list fields.
- Confirm a None-placeholder-being-filled-in case (e.g. model_version_id going from
  None to a real value) still produces ZERO contradiction entries.
- From agent/ with .venv active: `pytest -q` — zero regressions from wherever the
  count stood after Prompt 2.
- `pytest tests/e2e/test_full_pipeline_smoke.py -v` still passes (this test's fixture
  path should produce zero real contradictions - if it now DOES produce one, that is
  either a genuine latent bug this feature just surfaced for the first time, worth
  investigating and reporting back rather than silently suppressing, or a bug in your
  own detection logic - figure out which before considering this prompt done).
```

---

<a id="prompt-4"></a>

### Prompt 4 — Folder restructure, Desks 1-3 (Mandate/Coverage, Data Acquisition, Document/Fact Extraction)

```
Context: this repo's specialist agents live under agent/src/agents/specialists/,
currently organized into 8 category folders (planning, acquisition,
document_fact_intelligence, integrity_context, strategy_insight, modeling_valuation,
governance, decision_ops) that mostly-but-not-entirely map 1:1 onto the 8 "desks"
defined in agent/src/agents/orchestration/desk_registry.py (the system's own stated
"single source of truth", enforced by a contract test,
agent/tests/contract/test_desk_registry_matches_graph.py, that must never break).
This is the first of 5 folder-restructure prompts (this one covers desks 1-3 only;
desk 4 - which includes fixing a real misfiled-agent bug - is Prompt 5; desks 5-6 are
Prompt 6; desk 7 is Prompt 7; desk 8 is Prompt 8. Do ONLY this prompt's scope, not the
others, even though you now have the full picture - each is meant to be independently
reviewable and revertable).

Exact rename mapping for this prompt:
- agents/specialists/planning/ -> agents/specialists/desk1_mandate_coverage/
  - research_planner/ -> agent_01_research_planner/
  - entity_universe_resolver/ -> agent_02_entity_universe_resolver/
- agents/specialists/acquisition/ -> agents/specialists/desk2_data_acquisition/
  - acquisition_orchestrator/ -> agent_03_acquisition_orchestrator/
  - expert_notes_ingestion/ -> agent_04_expert_notes_ingestion/
- agents/specialists/document_fact_intelligence/ -> agents/specialists/desk3_document_fact_extraction/
  - document_intelligence/ -> agent_05_document_intelligence/
  - financial_fact_extraction/ -> agent_06_financial_fact_extraction/
  - transcript_intelligence/ -> agent_07_transcript_intelligence/

Implementation steps (do this carefully and mechanically - the goal is ZERO behavior
change, only paths/names):
1. Use `git mv` if this becomes a git repo by the time you do this (check with
   `git status` first - as of the last audit this was NOT a git repository at all;
   if still true, use plain `mv`/shell moves instead, there's no history to preserve).
2. For each renamed folder, update:
   a. The parent __init__.py that imports from it (find every __init__.py under
      agents/specialists/ that references the OLD folder/module path and update the
      import statement - do a repo-wide grep for the exact old dotted path, e.g.
      "specialists.planning" or "specialists.acquisition", not just the bare folder
      name, since a bare name like "planning" could false-positive match unrelated
      text).
   b. agent/src/agents/registry.py if it references any of these paths directly
      (check - it likely only receives AgentSpec objects passed to register(), which
      shouldn't encode folder paths, but verify).
   c. Every spec.py's own internal references, if any (unlikely, but check for
      relative imports that might reference a sibling by old path).
   d. agent/tests/contract/test_desk_registry_matches_graph.py and any other test
      file that imports these agent modules by their old dotted path - grep the
      whole tests/ directory for the old paths.
   e. agent/docs cross-references are LOWER priority for behavior but should still be
      updated where practical - at minimum, docs/agent_modularization_plan.md's own
      "current state" section (4) describing the OLD folder names should get a note
      that this rename is now done, so a future reader isn't confused by a doc
      describing a structure that no longer exists (add a one-line "DONE 2026-XX-XX"
      marker rather than deleting the historical description - this doc is meant to
      be a readable record of the plan and what's been executed against it).
3. Agent_id strings themselves (e.g. "research_planner", the string used everywhere
   in ResearchState/desk_registry.py/AgentSpec.id) must NOT change - only the Python
   module/folder path changes. Do not rename the registered agent_id.

Testing requirements (the real proof this was done safely):
- From agent/ with .venv active: `pytest -q` must show the EXACT SAME
  passed/xfailed count as immediately before this prompt (whatever it was after
  Prompt 3) - a pure rename must not add, remove, or change any test's outcome.
- `pytest tests/contract/test_desk_registry_matches_graph.py -v` specifically, since
  this is the exact test designed to catch drift between the registry and the real
  graph - it must pass.
- `pytest tests/e2e/test_full_pipeline_smoke.py -v` must still pass.
- Also do a real end-to-end sanity check beyond the test suite: start the backend
  (`python main.py` from agent/) and confirm `GET /v1/research-runs/desks` still
  returns all 8 desks with the same agent lists as before (the API response shape
  should be byte-for-byte identical to before this rename, since desk_registry.py's
  DATA - agent_id strings, desk metadata - didn't change, only file paths did).
```

---

<a id="prompt-5"></a>

### Prompt 5 — Folder restructure, Desk 4 (Fundamental & Context Research) — includes the market_data_validation misfiling fix

```
Context: same overall context as Prompt 4 (read that prompt's context paragraph if
you haven't already done Prompt 4's work). This prompt additionally fixes a REAL,
confirmed bug: market_data_validation conceptually belongs to Desk 4 (per
desk_registry.py's own DESKS tuple, which lists it as one of Desk 4's 5 agents) but
its actual folder currently lives under agents/specialists/governance/ (which is
Desk 7's folder) instead of agents/specialists/integrity_context/ (Desk 4's folder).
This prompt both renames Desk 4's folder AND moves this one misfiled agent into it.

Exact rename/move mapping:
- agents/specialists/integrity_context/ -> agents/specialists/desk4_fundamental_context_research/
  - financial_integrity/ -> agent_08_financial_integrity/
  - industry_competitive_context/ -> agent_09_industry_competitive_context/
  - filing_narrative_analyst/ -> agent_10_filing_narrative_analyst/
  - macro_esg_signal_context/ -> agent_11_macro_esg_signal_context/
- agents/specialists/governance/market_data_validation/ MOVES to
  agents/specialists/desk4_fundamental_context_research/agent_12_market_data_validation/
  (note: this is a cross-folder MOVE, not just a rename within the same parent -
  make sure whatever import-fixing you do in agents/specialists/governance/__init__.py
  REMOVES the reference entirely rather than just updating its path, since it no
  longer lives under governance/desk7 at all after this move, while
  desk4_fundamental_context_research/__init__.py needs to ADD a new import for it).

Follow the exact same implementation steps and testing requirements as Prompt 4
(re-read that prompt's steps 1-3 and testing section - they apply identically here,
just for this folder/these 5 agents instead). The one ADDITIONAL verification specific
to this prompt: after the move, confirm via
`python -c "from src.agents.orchestration import desk_registry; print(desk_registry.get_desk('desk4').agents)"`
(run from agent/ with .venv active) that market_data_validation still shows up
correctly as one of Desk 4's 5 agents in the desk_registry data itself (this data
doesn't change - only the underlying file path - but confirming end-to-end that the
whole chain still resolves correctly after a cross-folder move, not just a same-folder
rename, is worth the extra check since this one is slightly riskier).
```

---

<a id="prompt-6"></a>

### Prompt 6 — Folder restructure, Desks 5-6 (Strategy & Idea Generation, Modeling & Valuation)

```
Context: same overall context as Prompt 4 - read that prompt first if you land on
this one independently.

Exact rename mapping:
- agents/specialists/strategy_insight/ -> agents/specialists/desk5_strategy_idea_generation/
  - risk_catalyst/ -> agent_13_risk_catalyst/
  - variant_perception_ideation/ -> agent_14_variant_perception_ideation/
- agents/specialists/modeling_valuation/ -> agents/specialists/desk6_modeling_valuation/
  - operating_model/ -> agent_15_operating_model/
  - valuation_scenario/ -> agent_16_valuation_scenario/

Follow the exact same implementation steps and testing requirements as Prompt 4
(re-read that prompt in full before starting - steps 1-3 and the entire testing
section apply identically, just for these two folders/four agents).
```

---

<a id="prompt-7"></a>

### Prompt 7 — Folder restructure, Desk 7 (Investment Committee)

```
Context: same overall context as Prompt 4. This prompt assumes Prompt 5 (which moves
market_data_validation OUT of this folder) is already done - the governance/ folder
should already have only 5 agents left in it by the time you do this prompt, not 6.
Verify that precondition first (list agents/specialists/governance/ and confirm
market_data_validation is NOT present before proceeding - if it still is, Prompt 5
was not actually completed yet, stop and do that one first).

Exact rename mapping:
- agents/specialists/governance/ -> agents/specialists/desk7_investment_committee/
  - thesis_synthesizer/ -> agent_17_thesis_synthesizer/
  - devils_advocate/ -> agent_18_devils_advocate/
  - verification_agent/ -> agent_19_verification_agent/
  - investment_committee_adjudicator/ -> agent_20_investment_committee_adjudicator/
  - compliance_mnpi_guardrail/ -> agent_21_compliance_mnpi_guardrail/

Follow the exact same implementation steps and testing requirements as Prompt 4. One
extra thing worth double-checking here specifically: Desk 7 uses
CollaborationMode.ADVERSARIAL_CHAIN and its own docstring in desk_registry.py
explicitly says these agents must "never merge, never reorder, never run
concurrently." This prompt is a pure rename/move and must not change execution
order or dependency wiring in any way - after finishing, diff (conceptually - read
both) the AgentSpec.depends_on chains for all 5 of these agents against what they
were before the rename, and confirm they are byte-for-byte identical, just
referencing the new module paths.
```

---

<a id="prompt-8"></a>

### Prompt 8 — Folder restructure, Desk 8 (Decision, Distribution & Monitoring) — final restructure prompt, full regression pass

```
Context: same overall context as Prompt 4. This is the LAST folder-restructure
prompt - after this one, run the full combined regression check described at the
end (not just this desk's slice) since Prompts 4-8 together are the complete
migration.

Exact rename mapping:
- agents/specialists/decision_ops/ -> agents/specialists/desk8_decision_distribution_monitoring/
  - portfolio_sizing_advisor/ -> agent_22_portfolio_sizing_advisor/
  - report_and_notebook_agent/ -> agent_23_report_and_notebook_agent/
  - ic_memo_writer/ -> agent_24_ic_memo_writer/
  - continuous_monitoring_agent/ -> agent_S1_continuous_monitoring_agent/
    (the "S1" prefix, not a number in the 1-24 sequence, is deliberate - this agent
    is a STANDING agent that runs on its own separate schedule via
    continuous_ops_graph.py and is never part of the on-demand ResearchRun pipeline -
    do not renumber it as "agent_25", that would wrongly imply it's part of the same
    sequential/parallel execution plan as agents 1-24)

Follow the exact same implementation steps as Prompt 4, PLUS this final full-system
regression pass (since this completes the entire 5-prompt folder migration):
1. From agent/ with .venv active: `pytest -q` must show the exact same
   passed/xfailed count as immediately before Prompt 4 was first started (i.e. the
   whole 5-prompt folder migration, taken together, must be a complete no-op on test
   outcomes).
2. `pytest tests/contract/test_desk_registry_matches_graph.py -v` and
   `pytest tests/e2e/test_full_pipeline_smoke.py -v` both individually green.
3. Do a REAL live run end-to-end, not just the test suite: start the backend
   (`python main.py` from agent/, with Ollama running and `.env` configured per
   docs/repo notes), POST a real research run for a real ticker via
   `POST /v1/research-runs` with run_mode="auto", poll until it completes, and
   confirm it still completes successfully with 0 failed agent_runs (same shape of
   verification already done once in an earlier session for AAPL - repeat that same
   check here as the final proof this whole restructure is safe).
4. Update docs/agent_modularization_plan.md section 4 with a note that the full
   folder migration (Prompts 4-8) is complete, dated, so future readers of this plan
   know it's no longer a proposal but the actual current structure.
```

---

<a id="prompt-9"></a>

### Prompt 9 — Prompt-version eval harness (stretch goal, do last, optional)

> **Update, 2026-07-31 (Prompt 9 executed — ALL 10 PROMPTS NOW COMPLETE):**
> `agent/scripts/eval_prompt_versions.py` created. Overrides each of the 4
> LLM-backed agents' own module-level prompt-version constant directly (a
> deliberate, documented monkeypatch — no constructor/env-var indirection
> existed to hook into instead), runs the smallest realistic slice (a minimal
> hand-built state dict per agent, never the full graph) for each requested
> ticker/version pair, and prints a comparison table. Verified: `pytest -q`
> unaffected (173 passed/2 xfailed); `pytest --collect-only` unaffected (175
> tests, the script isn't a test file so was never collected in the first
> place); real end-to-end smoke runs succeeded for `continuous_monitoring_agent`
> (Ollama-only) and `industry_competitive_context` (real AAPL data + Ollama).
> **Important, disclosed limitation**: no agent's code yet branches on its
> prompt-version constant to select between multiple real template variants —
> today there is only ever one template per agent, so this tool currently
> compares a version string label, not genuinely different prompt text. It
> exists so a future second template variant becomes A/B-comparable with zero
> further script changes.

```
Context: assumes Prompts 1-2 are done (Decision Registry + prompt versioning for the
4 LLM-backed agents exist). This is a smaller, standalone, lower-priority addition -
do it after everything else, or skip it entirely if the earlier prompts already
satisfied the actual need.

Goal: a small script (agent/scripts/eval_prompt_versions.py, following the existing
CLI script conventions in that folder - argparse, async main, sys.path bootstrap -
copy the pattern from scripts/generate_professional_model.py or
scripts/verify_market_data_provenance.py) that:
1. Takes a target agent_id (one of the 4 LLM-backed ones) and two prompt_version
   strings to compare.
2. Takes a small fixed list of real tickers (default to a short hardcoded list like
   ["AAPL", "MSFT"] unless told otherwise) to replay against.
3. For each ticker, temporarily monkeypatches/parameterizes which PROMPT_VERSION the
   target agent uses (read how prompts.py's PROMPT_VERSION constant from Prompt 2 is
   consumed and find the least-invasive way to override it for a single run without
   permanently changing code - an environment variable or an explicit constructor
   parameter threaded through is preferable to monkeypatching a module constant, if
   the existing code structure makes that possible cleanly).
4. Runs the SAME real inputs through the agent (or the smallest realistic slice of
   the graph needed to reach that agent with real upstream state - check whether
   running the FULL graph is actually necessary, or whether the graph can be
   invoked starting from a specific desk with a pre-populated fake upstream state -
   look at how existing tests in agent/tests/ construct partial ResearchState
   fixtures for inspiration) under each prompt_version.
5. Prints a comparison table: per ticker, per prompt_version -> confidence score,
   any warnings produced, latency, and (if the agent is downstream of
   verification_agent in the same run) whether verification_agent's pass/fail
   changed between versions.

This is explicitly a "measure, don't guess" tool for future prompt iteration - it is
not meant to auto-pick a winner, just make an A/B comparison possible with real data
instead of vibes. Keep the implementation simple; this does not need its own test
suite entry, but must not require any network/Ollama access to IMPORT successfully
(only to actually RUN a comparison) so `pytest --collect-only` from agent/ still
succeeds with zero collection errors after adding this script.
```

