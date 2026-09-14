# IROS Agent Master Reference (v2 — Right-Sized Architecture)
### The single source of truth for how many agents this system needs, and what each one does

> **Revision note:** the first version of this document specified 50 agents (the
> blueprint's 36 plus 14 gap-fill additions). On review, that number was **not
> defensible** — it confused "every distinct noun in the blueprint's agent table"
> with "every task that actually requires a language model." Section 1 below redoes
> the analysis from first principles. The answer: **22 LLM-backed agents**, plus an
> explicit deterministic services layer that absorbs everything that doesn't need a
> model at all. This is a ~55% reduction, and — this is the important part — it is
> **more** robust against hallucination and process failure than the 50-agent version,
> not less. Section 6 gives the full old→new traceability so nothing is silently lost.

> **Update (2026-07-31):** as this architecture was actually implemented, 3 agents were
> added beyond the 22 specified below — `filing_narrative_analyst` (Tier 4),
> `market_data_validation` (Tier 4), and `ic_memo_writer` (Tier 8) — and
> `continuous_monitoring_agent` (agent #22 below) was reclassified as a "standing"
> agent that runs on its own separate schedule (`continuous_ops_graph.py`), not
> inside the on-demand `ResearchRun` pipeline. The actual shipped system has **24
> on-demand agents + 1 standing agent = 25 total** — every "22" reference below
> describes the original target architecture this document's own analysis arrived
> at, not the final shipped count; see `docs/agent_modularization_plan.md` for the
> full, code-verified current-state audit (including the finding that only 4 of
> these 25 agents actually call a language model — the rest are deterministic
> Python). The reasoning/methodology below (which agents are irreducible, why, and
> the merge bookkeeping in §6) is unaffected and still accurate.

---

## 0. The question, answered directly

**Do you need 50 agents? No.** You need:
- **22 agents that make a judgment call requiring language understanding or
  generation** (extraction from unstructured text, domain interpretation, synthesis,
  critique, compliance judgment, advisory output).
- **A deterministic services layer** (already partly built in `agent/src/services/`)
  that does *everything else* — arithmetic, reconciliation, statistics, policy lookup,
  delivery, scheduling, budget tracking — in plain, testable, zero-hallucination code.

The 50-agent version put things like "recompute a balance sheet identity" and "check
if two alert timestamps are within a dedupe window" into the *same organizational
category* (an "agent" with an `AgentSpec`) as "form a probabilistic investment thesis."
That's a category error, and it's the single biggest lever available for both **cost**
(fewer/cheaper model calls) and **correctness** (deterministic code cannot hallucinate;
an LLM call always can, however small the probability).

---

## 1. First-principles derivation (not "shrink the blueprint's list")

Instead of starting from the blueprint's 36 nouns, start from the actual question:
**what distinct classes of cognitive work does automating an equity-research/hedge-fund
analyst's job require, and which of those classes genuinely need a language model?**

### 1.1 The four kinds of work in this domain

| Kind of work | Example | Needs an LLM? |
|---|---|---|
| **Computation** — arithmetic, statistics, formula evaluation, reconciliation | Balance-sheet identity check, DCF math, hit-rate/p-value on a backtest, dedupe logic | **No.** Deterministic code is strictly better: zero hallucination, auditable, faster, cheaper. |
| **Structured lookup / policy** — deterministic rules over known data | Source-authority hierarchy, peer-universe rule engine, budget-threshold checks | **No.** These are config/rule tables, not judgment. |
| **Structured extraction from unstructured input** — turning prose/tables/audio into typed facts against a known taxonomy | Reading a 10-Q table into `Fact` objects, structuring a transcript into speaker turns | **Yes, but narrowly** — the model's job is pattern-matching into a fixed schema, which is verifiable (does the extracted number appear in the source at the cited coordinate?). |
| **Judgment** — synthesis, interpretation, critique, hypothesis generation, advisory recommendation under genuine uncertainty | "What does this quarter mean for the thesis," "what's the strongest bear case," "is this MNPI" | **Yes, unavoidably.** This is the actual value-add a human analyst provides and the actual reason to build this system. |

Only the last two rows produce **agents**. The first two rows produce **services**.
This single reclassification removes 8 of the original 50 items immediately
(`source_strategist`, `historical_delta`, `model_reconciliation`,
`technical_positioning`, `backtest_signal_validation`, `alerting_notification`,
`feedback_active_learning`, `workflow_supervisor_governor` — see §6 for exactly where
each one's logic now lives).

### 1.2 The economics of agent count: a marginal-cost/marginal-benefit view

Every additional agent has a **marginal cost**: latency, $ per call, an added place
where hallucination or schema drift can occur, and an added file to maintain and test
forever. It has a **marginal benefit** only if it lets a downstream step reason about
something it structurally could not otherwise reason about — i.e. a genuinely new
*evidence pack* or a genuinely new *governance role*, not just a new label on the same
evidence and the same kind of reasoning.

Formally: let $N$ be the number of sequential LLM-backed steps on the critical path to
a published conclusion, and let $p$ be the (small, but non-zero) per-step probability
that a step introduces an unflagged error. Assuming steps are not perfectly
error-correcting of one another, the probability the *pipeline* is clean end-to-end is
bounded above by $(1-p)^N$ — it is monotonically decreasing in $N$. **Every
non-load-bearing agent you remove is pure risk reduction with no offsetting loss**,
provided its function is fully preserved as deterministic code or folded into an agent
that already shares its evidence pack.

This is why the correct move for e.g. `historical_delta` (QoQ/YoY arithmetic) or
`backtest_signal_validation` (a hit-rate/significance calculation) is deletion-as-an-
agent, not "merge it into a bigger agent" — it was never contributing $N$-justifying
judgment in the first place.

### 1.3 Where merging *helps* vs. where it *hurts*

Merging two agents into one is justified only when they share the **same evidence
pack** and the **same cognitive verb** (e.g., "extract a typed fact from parsed
document elements" is one cognitive verb, whether the fact is a revenue line or a KPI).
Merging is **harmful** when it crams unrelated evidence packs into one context window —
the blueprint's own AI-limitations table (§11: "Context overload" → mitigation:
"task-specific context budgets") is exactly the failure mode this would cause. That is
why, below, extraction agents merge aggressively (same verb, same evidence), but
context/industry-research agents stop at three groups rather than collapsing into one
"research everything" agent, and why the five governance agents in Tier 7
(**§2.4**) do not merge *at all* — see the non-negotiable-separation argument there.

### 1.4 The result: 22 agents, organized by irreducible cognitive role

$$ 50 \; \xrightarrow{\;\text{8 removed as pure code}\;} \; 42 \; \xrightarrow{\;\text{13 merge-groups absorb 33 of them}\;} \; 22 $$

Full agent-by-agent bookkeeping is in §6. The rest of this document specifies the 22
survivors to the same standard of detail as before (role, dependencies, typed
inputs/outputs, tools, validators, confidence rubric, escalation/abstention) **plus**,
for every merge, the specific reason the merge is safe (shared evidence pack, same
cognitive verb) and for every non-merge in Tier 7, the specific reason it must stay
separate (separation-of-powers / legal / adversarial-independence).

---

## 2. The anti-hallucination / anti-failure architecture ("full-proof" design)

Five independent, stacked defenses. No single one is sufficient to trust alone — that
is the point of defense in depth.

### 2.1 Defense 1 — Grounding is a schema constraint, not a prompt instruction
Every agent's output schema requires `evidence_refs` for every material claim
(already true of the `AgentRunResult` envelope, `docs/data_contracts.md`). This is
enforced **in code**, not by asking the model nicely: if `evidence_refs` don't resolve
to a real `Fact`/`EvidenceItem` id already in state, the claim is rejected before it
ever reaches a human. This is Tier 7's Verification Agent's entire job (§2.5.3).

### 2.2 Defense 2 — Deterministic-first: nothing that can be computed is ever generated
Per §1.1, arithmetic/statistics/reconciliation never touch a model. This is not a
style preference — it is the reason the Numerical-Auditor function inside the
Verification Agent can catch 100% of arithmetic errors: it *recomputes independently
from raw facts in code*, it does not "check the model's math with another model."

### 2.3 Defense 3 — Calibration is measured, not assumed
An agent's `confidence` field is worthless unless it is empirically calibrated: a
population of "70% confidence" claims should resolve correctly ~70% of the time. This
is tracked as a first-class production metric (Brier score / reliability curve) inside
`evaluation_service`, fed by the outcome-reconciliation logic that used to be its own
agent (`feedback_active_learning`) and is now a deterministic aggregation job (§4).
**A confidence score that has never been checked against outcomes is a hallucination
about the system's own reliability**, which is exactly the failure mode this guards
against.

### 2.4 Defense 4 — Separation of powers for the five governance roles (Tier 7)
`thesis_synthesizer`, `devils_advocate`, `verification_agent`,
`investment_committee_adjudicator`, and `compliance_mnpi_guardrail` are five
**structurally independent** agents, and this is the one place in the whole roster
where "could this merge?" has a firm **no**:
- **Thesis Synthesizer vs. Devil's Advocate**: a model cannot reliably self-critique its
  own synthesis (confirmation bias is a property of the generation process, not
  something a follow-up instruction removes). These must be separate calls, ideally
  different model families (`docs/adr/0004`), so failure modes are not correlated.
- **Verification vs. Adjudicator**: verification is a fact-checker (did the citations
  and numbers hold up), adjudication is a judge (given that fact-check, what's the
  final confidence and is this publishable). Conflating them lets a run "grade its own
  homework."
- **Compliance vs. everything else**: this is a **legal**, not architectural,
  requirement. A real fund's compliance/legal-risk function must be independent of the
  research-quality function — the same reason information barriers exist between desks.
  It cannot be a mode of the Adjudicator; it must be able to block publication for
  reasons that have nothing to do with research quality.

### 2.5 Defense 5 — Process guarantees (resumability, idempotency, testing)
Unchanged from the existing architecture: LangGraph checkpointing
(`docs/adr/0001-orchestration-langgraph.md`), the quality-gate list
(`docs/evaluation_plan.md`), and the testing pyramid (unit → contract → golden →
property-based → adversarial → regression). What changes with 22 agents instead of 50
is that there are now 22 contract-test surfaces instead of 50 — less to keep green,
same rigor per surface.

---

## 3. The 22-agent roster

Same output-envelope convention as before: every agent returns
`status, result, evidence_refs, calculations, assumptions, conflicts, missing_data,
confidence, quality_checks, warnings, next_actions`; the tables below describe only the
agent-specific `result` payload.

### Tier 1 — Planning & Identity

#### 1. Research Planner (`research_planner`)
**Depends on:** — · **Merge status:** unchanged from original (#1)

**Role:** Converts the mandate into an execution plan: which of the other 21 agents
run, in what order, under what budget, with which human-approval gates.

**Inputs:** `mandate` (str), `raw_query` (str), `workspace_id` (str),
`user_preferences` (dict, optional).
**Outputs:** `execution_plan` (list[str]), `selected_agent_ids` (list[str]), `output_contract`
(list[str]), `budget` (dict), `approval_gates` (list[str]).
**Tools:** none (registry lookup + rule-based mode classification).
**Validators:** every id in `execution_plan`/`selected_agent_ids` must exist in the
registry. **Confidence:** high unless the mandate is genuinely ambiguous between two
product modes (then surfaced as a clarifying question, not a low-confidence guess).
**Escalation/abstention:** none.

#### 2. Entity & Universe Resolver (`entity_universe_resolver`)
**Depends on:** 1 · **Merges:** `entity_resolution` (#2) + `peer_universe_curation` (#4)

**Why this merge is safe:** both are "resolve exactly which securities we are talking
about" — the target company *and* its comparison set are one identity-resolution task
with two outputs, not two different cognitive tasks. Splitting them only doubled the
context needed (both need the same `Issuer`/`Security` reference data) without adding
distinguishing judgment.

**Role:** Resolves ticker/company/identifier → canonical `Issuer`+`Security`
(escalating on ambiguity), *and* curates the approved peer/comparable-company universe
with a recorded reason per peer.

**Inputs:** `security_id` or `raw_query` (str), `exchange_hint` (str, optional),
`manual_peer_overrides` (list[dict], optional).
**Outputs:** `issuer` (`Issuer`), `security` (`Security`), `candidate_matches`
(list[`Security`]), `disambiguation_required` (bool), `peer_security_ids` (list[str]),
`peer_inclusion_reasons` (dict[str,str]).
**Tools:** `identity_service.resolve_issuer/resolve_security`, a deterministic
peer-similarity scorer (sector/industry/size/geography — this scoring itself is a
*service* the agent calls, not something the agent computes by "feel").
**Validators:** `peer_reason_recorded` (every peer has a non-empty reason); identifier
format validation.
**Confidence:** 1.0 for exact single match, scaled down by candidate count when
ambiguous; peer-set confidence from the similarity-score distribution.
**Escalation:** `ambiguous_identifier` → human disambiguation gate.
**Abstention:** if fewer than 2 peers can be found, abstain on the peer set (not on
identity) and flag `missing_data`.

### Tier 2 — Acquisition

#### 3. Acquisition Orchestrator (`acquisition_orchestrator`)
**Depends on:** 2 · **Merges:** `ir_regulatory_acquisition` (#5) + `web_news_acquisition`
(#6) + `webcast_audio` (#7) + `alternative_data` (#8); absorbs `source_strategist`'s
(#3) policy as a service call rather than a separate agent.

**Why this merge is safe:** the actual judgment call across all four original agents is
identical — *"given the source-authority policy, decide what to fetch, in what order,
and whether a fallback is good enough"* — while the fetching itself (HTTP calls, hashing,
versioning) was already 100% deterministic connector code, never agentic. One
orchestrating agent choosing among many deterministic connectors is the correct shape;
four agents each wrapping one connector was not.

**Role:** Builds the source manifest (via the deterministic authority-policy service),
directs the connector layer (SEC/EDGAR, IR sites, news, webcast/audio, alt-data panels)
to acquire artifacts, judges whether coverage/fallback is sufficient, and reports gaps
explicitly rather than silently proceeding.

**Inputs:** `issuer_id`, `event_type`, `region` (optional).
**Outputs:** `source_artifacts` (list[`SourceArtifact`]), `source_versions`
(list[`SourceVersion`]), `coverage_score` (float), `fallbacks_used` (list[dict]),
`access_blocked` (list[dict]).
**Tools:** `sec_edgar_connector`, `ir_website_connector`, `web_news_connector`,
`webcast_audio_connector`, `audio_transcriber`, `alt_data_connector`, plus the
deterministic `source_authority_policy` service (formerly agent #3).
**Validators:** content-hash + versioning enforced by the connector layer (never
overwrite); coverage-score computed by formula, not estimated.
**Confidence:** derived from `coverage_score`.
**Escalation:** none. **Abstention:** none — gaps go to `missing_data`, per the
blueprint's "never fail silently, never block the whole run over one missing doc"
principle.

#### 4. Expert Call & Internal Notes Ingestion (`expert_notes_ingestion`)
**Depends on:** 2 · **Merge status:** unchanged from original (#9), kept separate

**Why this stays separate from Acquisition Orchestrator:** it ingests human-authored,
permissioned, compliance-sensitive prose (not machine-downloaded public documents) and
must apply MNPI-marker screening and a lower default authority score *at ingestion
time* — a materially different risk profile that deserves its own narrow, carefully
tested surface (defense-in-depth with Compliance & MNPI Guardrail at Tier 7).

**Inputs/Outputs/Tools/Validators:** unchanged from the original spec.

### Tier 3 — Document & Fact Intelligence

#### 5. Document Intelligence (`document_intelligence`)
**Depends on:** 3 · **Merges:** `document_classifier` (#10) + `pdf_presentation_intelligence`
(#11) + `table_reconstruction` (#12)

**Why this merge is safe:** classify → parse → reconstruct-tables is one continuous
pipeline over the same document, mostly deterministic layout/OCR/table-structure models
with only a thin LLM step for ambiguous classification — three agents were wrapping one
pipeline.

**Role:** Classifies each acquired document, extracts text/tables/images/coordinates,
and reconstructs financial tables with headers/units/periods/merged-cell handling.

**Inputs:** `source_versions` (list[`SourceVersion`]).
**Outputs:** `classifications` (dict), `document_elements` (list[`DocumentElement`]),
`low_confidence_pages` (list[dict]), `reconciliation_candidates` (list[dict]).
**Tools:** `pdf_parser`, `table_reconstruction_parser`, small classifier model
(`TaskType.CLASSIFICATION`).
**Validators:** every element has non-null coordinates; detected subtotal rows flagged
(not silently corrected) if they don't sum within tolerance.
**Confidence:** per-element parser confidence. **Escalation/abstention:** none
(low-confidence pages routed to OCR/vision fallback, not blocked).

#### 6. Financial & KPI Fact Extraction (`financial_fact_extraction`)
**Depends on:** 5 · **Merges:** `financial_statement_extractor` (#13) + `kpi_ontology`
(#14) + `guidance_agent` (#15) + `consensus_expectation` (#18)

**Why this merge is safe:** all four are the identical cognitive verb — *"map
parsed elements or an external feed into a typed `Fact`, against a known metric
taxonomy, with units/basis/period metadata"* — differing only in which taxonomy row
(income-statement line vs. sector KPI vs. guidance range vs. consensus estimate), which
is a configuration difference, not a different kind of reasoning.

**Role:** Produces standardized financial-statement facts, non-GAAP bridges, sector KPIs,
forward guidance (with lineage), and normalized consensus/expectation snapshots, all as
typed `Fact` objects on one consistent taxonomy.

**Inputs:** `document_elements` (list[`DocumentElement`]), `issuer_id`, `period_id`.
**Outputs:** `facts` (list[`Fact`]), `non_gaap_bridges` (list[dict]),
`guidance_ranges` (list[dict]), `prior_guidance_lineage` (list[dict]),
`consensus_snapshot` (dict).
**Tools:** metric-taxonomy/ontology registry.
**Validators:** every non-GAAP fact has a bridge; guidance is append-only (never
overwritten in place); consensus always carries an explicit `basis` label — never
compare mismatched bases (blueprint principle).
**Confidence:** parsing confidence × taxonomy-match confidence.
**Escalation/abstention:** abstain (explicit "consensus unavailable") rather than
invent a number when no consensus source exists.

#### 7. Transcript & Management-Language Intelligence (`transcript_intelligence`)
**Depends on:** 5 · **Merges:** `transcript_structure` (#16) + `management_language` (#17)

**Why this merge is safe:** both operate on the same object (the earnings-call
transcript) as one continuous pipeline: structure it, then score the language on top of
that structure — there is no independent evidence pack for "language scoring" that
isn't downstream of "transcript structuring."

**Role:** Diarizes and structures prepared remarks/Q&A, then scores wording shifts,
hedging, evasiveness, and specificity against historical calls, with every score tied to
a quoted excerpt.

**Inputs:** `document_elements` (transcript), `issuer_id` (historical baseline).
**Outputs:** `structured_transcript` (dict), `unresolved_questions` (list[dict]),
`language_scores` (dict), `wording_diff_vs_prior` (list[dict]).
**Tools:** `transcript_structurer`, `memory_service` (historical language baseline).
**Validators:** every language score must cite its supporting excerpt.
**Confidence:** scaled by historical-call sample size available.
**Escalation/abstention:** abstain on language-diff scoring only (not structuring) if no
prior-call baseline exists yet.

### Tier 4 — Integrity & Context Research

#### 8. Financial Integrity (`financial_integrity`)
**Depends on:** 6 · **Merges:** `accounting_quality` (#19) + `forensic_disclosure` (#20);
absorbs `historical_delta` (#21) as a **service call**, not a merged agent (the QoQ/YoY
arithmetic itself is deterministic — see §4 — this agent *consumes* those deltas as
input rather than computing them).

**Why this merge is safe:** both are the same underlying question — *"does this
company's reported data and disclosure behavior hold up to scrutiny"* — differing only
in checklist items (accruals/cash-conversion vs. restatements/footnote changes), not in
cognitive process.

**Role:** Assesses earnings quality (accruals, cash conversion, one-offs, SBC) and
disclosure integrity (restatements, changed definitions, segment reorganizations),
using deterministically-computed deltas/ratios as input evidence.

**Inputs:** `facts` (list[`Fact`]), `issuer_id`, `deltas` (from the deterministic
comparison service).
**Outputs:** `earnings_quality_flags` (list[dict]), `disclosure_conflicts`
(list[`Conflict`]), `restatement_detected` / `segment_reorg_detected` (bool).
**Tools:** `calculator_tools` (ratios), `memory_service` (historical disclosure diff).
**Validators:** all ratios computed via `calculator_tools`, never estimated by the
model; a detected restatement creates a new `Fact` version, never overwrites.
**Confidence:** high on ratios (deterministic); flag-interpretation confidence scored
separately. **Escalation/abstention:** none.

#### 9. Industry & Competitive Context (`industry_competitive_context`)
**Depends on:** 2 · **Merges:** `industry_structure` (#22) + `competitive_intelligence`
(#23) + `supply_chain_customer` (#24)

**Why this merge is safe (and why it stops here):** all three share the same evidence
pack — the company's own and its peers' filings/news/graph edges — and the same verb,
"build the external competitive map." They do **not** merge further into Tier 4's other
agent (macro/ESG/signal, below) because that has a genuinely different evidence pack
(macro data feeds, ESG disclosures, alt-data panels) — cramming both into one call would
recreate the "context overload" failure mode the blueprint explicitly warns against.

**Role:** Maps market structure, tracks peer KPIs/pricing/strategic moves (using the
approved peer set from agent 2), and builds customer/supplier read-through via the
event/knowledge graph.

**Inputs:** `issuer_id`, `peer_security_ids` (from agent 2).
**Outputs:** `industry_map` (dict), `peer_comparison_table` (dict),
`competitive_moves` (list[dict]), `graph_edges` (list[`GraphEdge`]),
`concentration_metrics` (dict).
**Tools:** `graph_tools`, `search_news`.
**Validators:** every inferred graph edge carries `is_inferred=True` + confidence
(never presented as fact); comparison-table columns must exactly match
`peer_security_ids`.
**Confidence:** based on source coverage/completeness. **Escalation/abstention:** none.

#### 10. Macro, ESG & Alternative-Signal Context (`macro_esg_signal_context`)
**Depends on:** 2, 3 · **Merges:** `macro_policy` (#25) + `sentiment_alt_signal` (#26) +
`esg_sustainability` (#27); consumes `technical_positioning`'s (#34) market-data feed
as an optional input rather than a merged agent (see §4 — the indicator computation
itself is deterministic; only the *interpretation*, when relevant, is folded in here).

**Why this merge is safe:** macro exposure, ESG risk, and sentiment/alt-data trend all
share the same evidence pack (external data feeds + disclosures, *not* the company's own
filings) and the same verb — "quantify a context signal external to the company's own
reported numbers" — and are the correct second research group precisely because they're
evidentially distinct from Tier 4's other agent (#9).

**Role:** Maps FX/rate/commodity/regulatory sensitivities, scores news/social/alt-data
sentiment trend, and assesses environmental/social/governance risk with explicit
data-availability confidence (never fabricated when disclosure is sparse).

**Inputs:** `issuer_id`.
**Outputs:** `macro_sensitivities` (dict), `policy_watch_items` (list[dict]),
`sentiment_trend_series` (list[dict]), `alt_signal_series` (list[dict]),
`esg_scorecard` (dict), `controversy_log` (list[dict]),
`data_availability_confidence` (float).
**Tools:** macro data feed, ESG disclosure sources, `search_news`.
**Validators:** a missing ESG disclosure category lowers
`data_availability_confidence`, never back-filled with an assumption.
**Confidence:** driven directly by `data_availability_confidence`.
**Escalation/abstention:** abstain per sub-score with zero underlying disclosure,
rather than scoring it as neutral.

### Tier 5 — Modeling & Valuation

#### 11. Operating Model (`operating_model`)
**Depends on:** 6, 8 · **Merge status:** unchanged from original (#28)

**Role:** Maintains the driver-based formula graph (revenue, margin, working capital,
capex, tax, share count, cash flow), producing an auditable `EstimateChange` for every
driver update.

**Inputs/Outputs/Tools/Validators:** unchanged. `model_reconciliation` (#29) is now the
deterministic gate this agent's output must pass through as a **service call** (see
§4) — it never was a judgment task (the original spec literally said "no LLM call at
all"), so it was never really an agent.

#### 12. Valuation & Scenario (`valuation_scenario`)
**Depends on:** 11, 2 · **Merges:** `valuation_agent` (#30) + `scenario_probability` (#31)

**Why this merge is safe:** valuation *is* scenario analysis at a point estimate —
DCF/comps/SOTP under a given assumption set and base/bull/bear trees under varied
assumption sets are the same underlying task (produce value given assumptions),
executed twice instead of framed as two agents.

**Role:** Runs DCF/SOTP/comps/sector-specific valuation and builds probability-weighted
base/bull/bear scenarios, all against the reconciled model.

**Inputs:** `model_version_id` (post-reconciliation), peer set (agent 2).
**Outputs:** `valuation` (`Valuation`), `scenarios` (list[`Scenario`]),
`probability_weighted_outcome` (dict).
**Tools:** `valuation_service` (`dcf.py`, `comps.py`, `sotp.py`),
`formula_graph.run_scenario`.
**Validators:** scenario probabilities sum to 1.0; method selection follows the
sector table (blueprint §6.4) rather than free choice.
**Confidence:** based on sensitivity-range width relative to price.
**Escalation/abstention:** none.

### Tier 6 — Strategy & Differentiated Insight

#### 13. Risk & Catalyst (`risk_catalyst`)
**Depends on:** 2, 8, 9, 10 · **Merges:** `catalyst_agent` (#32) + `risk_agent` (#33)

**Why this merge is safe:** both are "enumerate what could change the outcome, and how,
using the same upstream evidence (integrity + context agents' flags)" — an analyst
thinks about upside/downside catalysts and risks as one dated, probability-weighted
list, not two disconnected documents.

**Role:** Builds the dated catalyst calendar and the risk taxonomy (operational,
financial, accounting, regulatory, macro, thesis-specific), each item probability- and
severity-weighted and linked to thesis pillars.

**Inputs:** `issuer_id` + Tier 4 agent outputs (8, 9, 10).
**Outputs:** `catalysts` (list[`Catalyst`]), `risks` (list[`Risk`]).
**Tools:** calendar/event sources. **Validators:** every risk cites at least one
upstream evidence_ref; catalyst dates are valid future dates or explicitly marked
completed.
**Confidence:** based on dependency-chain/severity-probability clarity.
**Escalation/abstention:** none.

#### 14. Variant Perception & Ideation (`variant_perception_ideation`)
**Depends on:** 8, 9, 10 · **Merges:** `variant_perception` (#35) + `idea_generation_screening`
(#36); consumes `technical_positioning`'s (#34) feed and `backtest_signal_validation`'s
(#37) service output as inputs rather than merged/separate agents.

**Why this merge is safe:** both are the identical competency — "find non-consensus,
differentiated hypotheses with a stated falsification test" — parameterized by scope
(single name, in depth, vs. a screened universe, ranked). Same cognitive verb, same
validator (mandatory falsification test), different `scope` input.

**Role:** Generates non-consensus hypotheses (single-name deep dive or universe-wide
screen) from cross-source triangulation, each with a stated falsification test and, when
requested, backed by a historical backtest via the deterministic
`backtest_signal_validation` service before being trusted.

**Inputs:** `facts`, `comparisons`, context-agent outputs (9, 10), `scope`
(`single_name` | `universe`), optional `universe_filter`.
**Outputs:** `variant_hypotheses` (list[{claim, evidence_refs, falsification_test,
backtest_ref}]), `ranked_candidates` (list[dict], only when `scope=universe`).
**Tools:** `graph_tools`, `search_news`, `backtest_service` (deterministic stats,
§4).
**Validators:** every hypothesis must include a falsification test — reject any that
doesn't (mandatory, not advisory).
**Confidence:** based on evidence-source diversity/independence and, when available,
backtest significance.
**Escalation/abstention:** abstain on any hypothesis lacking a falsification test.

### Tier 7 — Synthesis, Verification & Governance (the anti-hallucination core — no further merges, ever)

#### 15. Thesis Synthesizer (`thesis_synthesizer`)
**Depends on:** 12, 13, 14 · **Merge status:** unchanged (#38)

Combines facts and specialist conclusions into a probabilistic `Thesis`. **No new
facts may be introduced here** — only interpretation of facts already frozen upstream.
Every `ThesisPillar.evidence_refs` must resolve to a real id in state or the pillar is
rejected. Abstains (`insufficient_evidence`) below a minimum well-supported-pillar
count.

#### 16. Devil's Advocate (`devils_advocate`)
**Depends on:** 15 · **Merge status:** unchanged (#39) — **structurally
non-mergeable, see §2.4**

Constructs the strongest opposing case using a different model family than agent 15
where possible. Every claim requires a citation. Reviewer is always the Adjudicator —
never self-adjudicates.

#### 17. Verification Agent (`verification_agent`)
**Depends on:** 15 · **Merges:** `evidence_auditor` (#40) + `numerical_auditor` (#41)

**Why this merge is safe (and why it's still Tier-7-rigor, not a Tier-3-style
convenience merge):** both are fact-checking functions over the *same* frozen thesis —
one checks citations resolve and support the claim, the other independently recomputes
every number. They are almost entirely deterministic (id-resolution, independent
recomputation via `valuation_service`/`calculator_tools`) with only a thin semantic-
entailment check ("does this citation's text actually support this specific claim")
needing a model call at all. Merging them avoids paying for two separate LLM calls to
do what is ~90% one deterministic verification pass.

**Role:** Resolves every claim's evidence linkage (rejecting unresolvable refs into
`unsupported_claims`), runs a semantic-entailment check on resolved citations, and
independently recomputes every material number/valuation output from raw facts —
never trusting agent 12's cached result.

**Inputs:** `thesis`, `valuation`, `estimate_changes`.
**Outputs:** `unsupported_claims` (list), `citation_precision`/`citation_recall`
(float), `numerical_discrepancies` (list[dict]), `pass` (bool).
**Tools:** `evidence_service`, `calculator_tools`, `valuation_service` (re-invoked
fresh).
**Validators:** this agent *is* the deterministic validator layer for the thesis; the
one LLM call (entailment check) is bounded and schema-constrained.
**Confidence:** n/a — reports counts/rates. **Escalation/abstention:** feeds directly
into the Adjudicator's `unsupported_claim_rate_too_high` / discrepancy-blocks-approval
logic.

#### 18. Investment Committee Adjudicator (`investment_committee_adjudicator`)
**Depends on:** 16, 17 · **Merge status:** unchanged (#42) — **structurally
non-mergeable, see §2.4**

Resolves agent disagreement via the normalized-claim/adjudication-matrix protocol
(blueprint §4.2), assigns final confidence, and gates publishability. Abstains on
`unresolved_high_severity_conflict` or `unsupported_claim_rate_too_high`.

#### 19. Compliance & MNPI Guardrail (`compliance_mnpi_guardrail`)
**Depends on:** 18 · **Merge status:** unchanged (#43) — **legally non-mergeable, see §2.4**

Screens the thesis/evidence/source-manifest (especially agent 4's internal-notes
content) for MNPI risk, information-barrier violations, and personal-trading conflicts.
Can only *flag*; a human compliance officer clears. Blocks publication
(`unresolved_compliance_flag`) until cleared — independent of research quality.

### Tier 8 — Decision, Output & Operations

#### 20. Portfolio Sizing Advisor (`portfolio_sizing_advisor`)
**Depends on:** 18 · **Merge status:** unchanged (#44)

Advisory-only position-size/stop-loss/hedge recommendation, hard-capped by portfolio
risk limits computed deterministically by `portfolio_service`. `requires_approval` is
always `True` — no code path may set it `False` (no autonomous trading, ever).

#### 21. Report & Notebook Agent (`report_and_notebook_agent`)
**Depends on:** 18, 19 · **Merges:** `report_artifact_agent` (#45) + `conversational_research_assistant`
(#48)

**Why this merge is safe:** both are the identical competency — "generate grounded,
citation-required natural-language output from the frozen evidence/thesis store" —
differing only in output shape (a formal document/export vs. a chat answer to an ad-hoc
question). Same guardrail (citation required), same evidence store, same model-router
task type.

**Role:** Generates the cockpit payload, PDF/DOCX/Excel/PPT exports and evidence pack
(only after `compliance_report.cleared=True`), *and* answers multi-turn natural-language
follow-up questions grounded in the same run's evidence, without re-running the
pipeline per question.

**Inputs:** `adjudication`, `compliance_report`, and, for chat mode, `question` (str).
**Outputs:** `cockpit_payload`, `pdf_bytes`/`excel_diff_bytes`/`pptx_bytes`,
`evidence_pack_json`, or (chat mode) `answer_text` + `evidence_refs`.
**Tools:** `report_service`, `excel_tools`, `evidence_service`/`fact_service`
retrieval.
**Validators:** refuses any publication-facing export if not compliance-cleared;
`citation_required` on every factual sentence in `answer_text`.
**Confidence:** n/a for exports; retrieval-relevance-based for chat answers.
**Escalation:** `approval_required_for_publication`. **Abstention:** chat mode responds
"not answerable from this run's evidence" rather than fabricating.

#### 22. Continuous Monitoring Agent (`continuous_monitoring_agent`)
**Depends on:** 3 · **Merge status:** unchanged (#46), scope narrowed to the one
genuine judgment call

**Why this stays a thin, standalone agent (not a service):** polling sources on a
schedule is pure deterministic infrastructure (a service), but *"is this new filing/
price-move/news item actually material enough to trigger a full ResearchRun"* is a
real judgment call — get it wrong one way and you spam the user with noise runs, get it
wrong the other way and you miss a real event. It deserves a narrow, dedicated,
heavily-tested surface rather than being folded into the polling service's code or into
Alerting (a delivery concern, now a pure service — see §4).

**Inputs:** `workspace_id`, candidate trigger events from the polling service.
**Outputs:** `detected_triggers` (list[{issuer_id, trigger_type, materiality_score,
detected_at}]).
**Tools:** reuses Acquisition Orchestrator's connectors in "poll" mode.
**Validators:** a trigger must exceed a configured materiality threshold to fire.
**Confidence:** the materiality score itself. **Escalation/abstention:** none.

---

## 4. The deterministic services layer (everything that is *not* an agent, and why)

| Former "agent" | Why it was never really an agent | Now lives in |
|---|---|---|
| `source_strategist` (#3) | Pure policy-table lookup (blueprint's own source-authority hierarchy is a static table, not a judgment call) | `acquisition_service` — consulted by Agent 3 |
| `historical_delta` (#21) | QoQ/YoY/vs-prior arithmetic — pure subtraction/division with a "not meaningful" guard | `fact_service` comparison routines — consumed by Agent 8 |
| `model_reconciliation` (#29) | Explicitly zero-LLM balance/formula/circularity checks (this was stated outright in the original spec) | `model_service` — a hard gate before Agent 12 runs |
| `technical_positioning` (#34) | Price/short-interest/ownership indicators are computed, not interpreted, by default | A market-data feed consumed by Agent 14 when relevant |
| `backtest_signal_validation` (#37) | Hit-rate/lead-time/significance testing is a statistics routine, not language reasoning | `evaluation_service` (a `backtest_service` submodule) — called by Agent 14 |
| `alerting_notification` (#47) | Channel routing, de-duplication, and rate-limiting are pure delivery logic | A `notification_service` — called by Agent 22's downstream trigger handling |
| `feedback_active_learning` (#49) | Aggregating `UserOverride`s and computing calibration metrics is deterministic aggregation | `evaluation_service` — the same calibration tracking described in §2.3 |
| `workflow_supervisor_governor` (#50) | Budget/latency tracking against `AgentSpec.max_cost/max_latency` is accounting, and re-planning is a rule ("retry once, downgrade model, or skip-and-flag"), never a generative task | Platform middleware inside `agent/src/agents/graph.py`'s node-wrapping layer — infrastructure, not a registry entry |

None of these lose functionality. All of them get **more** reliable by moving from "an
LLM call that is supposed to be deterministic anyway" to "code that is actually
deterministic."

---

## 5. Updated build order & dependency graph

Build order follows the same "one agent, fully working, before the next" discipline as
before. Tier 7 (governance) should be built and hardened **before** Tiers 5-6's outputs
are trusted for anything user-facing, since Tier 7 is what makes the rest of the
pipeline trustworthy at all — it is deliberately not last in practice even though later
in numbering.

| Build order | Agent | Tier |
|---|---|---|
| 1 | `research_planner` | 1 |
| 2 | `entity_universe_resolver` | 1 |
| 3 | `acquisition_orchestrator` | 2 |
| 4 | `expert_notes_ingestion` | 2 |
| 5 | `document_intelligence` | 3 |
| 6 | `financial_fact_extraction` | 3 |
| 7 | `transcript_intelligence` | 3 |
| 8 | `financial_integrity` | 4 |
| 9 | `industry_competitive_context` | 4 |
| 10 | `macro_esg_signal_context` | 4 |
| 11 | `operating_model` | 5 |
| 12 | `valuation_scenario` | 5 |
| 13 | `risk_catalyst` | 6 |
| 14 | `variant_perception_ideation` | 6 |
| 15 | `thesis_synthesizer` | 7 |
| 16 | `devils_advocate` | 7 |
| 17 | `verification_agent` | 7 |
| 18 | `investment_committee_adjudicator` | 7 |
| 19 | `compliance_mnpi_guardrail` | 7 |
| 20 | `portfolio_sizing_advisor` | 8 |
| 21 | `report_and_notebook_agent` | 8 |
| 22 | `continuous_monitoring_agent` | 8 |

Build the 8 deterministic services (§4) alongside the tier that first depends on them
(e.g. `source_authority_policy` before Agent 3, `model_reconciliation` before Agent 12),
not as an afterthought — they are on the critical path even though they're not agents.

---

## 6. Full traceability — every one of the original 50, accounted for

| Original # | Original agent | Disposition |
|---|---|---|
| 1 | Research Planner | → **1. `research_planner`** (kept) |
| 2 | Entity Resolution | → **2. `entity_universe_resolver`** (merged) |
| 3 | Source Strategist | → **service**: `acquisition_service` policy |
| 4 | Peer Universe Curation | → **2. `entity_universe_resolver`** (merged) |
| 5 | IR/Regulatory Acquisition | → **3. `acquisition_orchestrator`** (merged) |
| 6 | Web/News Acquisition | → **3. `acquisition_orchestrator`** (merged) |
| 7 | Webcast/Audio | → **3. `acquisition_orchestrator`** (merged) |
| 8 | Alternative Data | → **3. `acquisition_orchestrator`** (merged) |
| 9 | Expert Call & Internal Notes Ingestion | → **4. `expert_notes_ingestion`** (kept, renamed) |
| 10 | Document Classifier | → **5. `document_intelligence`** (merged) |
| 11 | PDF/Presentation Intelligence | → **5. `document_intelligence`** (merged) |
| 12 | Table Reconstruction | → **5. `document_intelligence`** (merged) |
| 13 | Financial Statement Extractor | → **6. `financial_fact_extraction`** (merged) |
| 14 | KPI Ontology | → **6. `financial_fact_extraction`** (merged) |
| 15 | Guidance Agent | → **6. `financial_fact_extraction`** (merged) |
| 16 | Transcript Structure | → **7. `transcript_intelligence`** (merged) |
| 17 | Management Language | → **7. `transcript_intelligence`** (merged) |
| 18 | Consensus/Expectation | → **6. `financial_fact_extraction`** (merged) |
| 19 | Accounting Quality | → **8. `financial_integrity`** (merged) |
| 20 | Forensic Disclosure | → **8. `financial_integrity`** (merged) |
| 21 | Historical Delta | → **service**: `fact_service` comparison routines |
| 22 | Industry Structure | → **9. `industry_competitive_context`** (merged) |
| 23 | Competitive Intelligence | → **9. `industry_competitive_context`** (merged) |
| 24 | Supply-Chain/Customer | → **9. `industry_competitive_context`** (merged) |
| 25 | Macro/Policy | → **10. `macro_esg_signal_context`** (merged) |
| 26 | Sentiment & Alt Signal | → **10. `macro_esg_signal_context`** (merged) |
| 27 | ESG & Sustainability | → **10. `macro_esg_signal_context`** (merged) |
| 28 | Operating Model | → **11. `operating_model`** (kept) |
| 29 | Model Reconciliation | → **service**: `model_service` deterministic gate |
| 30 | Valuation Agent | → **12. `valuation_scenario`** (merged) |
| 31 | Scenario & Probability | → **12. `valuation_scenario`** (merged) |
| 32 | Catalyst Agent | → **13. `risk_catalyst`** (merged) |
| 33 | Risk Agent | → **13. `risk_catalyst`** (merged) |
| 34 | Technical/Positioning | → **service** (data feed) consumed by 14 |
| 35 | Variant Perception | → **14. `variant_perception_ideation`** (merged) |
| 36 | Idea Generation & Screening | → **14. `variant_perception_ideation`** (merged) |
| 37 | Backtest & Signal Validation | → **service**: `evaluation_service` stats |
| 38 | Thesis Synthesizer | → **15. `thesis_synthesizer`** (kept) |
| 39 | Devil's Advocate | → **16. `devils_advocate`** (kept, non-mergeable) |
| 40 | Evidence Auditor | → **17. `verification_agent`** (merged) |
| 41 | Numerical Auditor | → **17. `verification_agent`** (merged) |
| 42 | Investment Committee Adjudicator | → **18. `investment_committee_adjudicator`** (kept, non-mergeable) |
| 43 | Compliance & MNPI Guardrail | → **19. `compliance_mnpi_guardrail`** (kept, non-mergeable) |
| 44 | Portfolio Sizing Advisor | → **20. `portfolio_sizing_advisor`** (kept) |
| 45 | Report/Artifact Agent | → **21. `report_and_notebook_agent`** (merged) |
| 46 | Continuous Monitoring / Event Detection | → **22. `continuous_monitoring_agent`** (kept, narrowed) |
| 47 | Alerting & Notification | → **service**: `notification_service` |
| 48 | Conversational Research Assistant | → **21. `report_and_notebook_agent`** (merged) |
| 49 | Feedback & Active-Learning | → **service**: `evaluation_service` calibration |
| 50 | Workflow Supervisor / Cost-Latency Governor | → **infra**: `graph.py` middleware |

**Bookkeeping check:** 9 kept as their own agent + 33 absorbed into 13 merge-groups (→
13 new agents) + 8 reclassified as services/infra = 50. New agent total: 9 + 13 = **22**.

---

## 7. Production hardening checklist ("full-proof" gates before this ships)

These are unchanged in spirit from `docs/evaluation_plan.md` but restated here against
the 22-agent shape specifically:

1. **Every agent's contract test** asserts `required_inputs` enforcement and output
   schema shape — 22 surfaces, not 50, but zero exceptions.
2. **Verification Agent (17) must have 100% recall on an adversarial corpus** of
   intentionally corrupted numbers and intentionally unsupported claims before Tier 7
   is considered production-ready — this is the single highest-leverage test in the
   whole system.
3. **Calibration curve tracked continuously** (Defense 3, §2.3): if confidence-70%
   claims resolve correctly less than ~60% or more than ~80% of the time in production,
   that is a release-blocking regression, not a metric to watch passively.
4. **Determinism/idempotency test**: replaying the same frozen source snapshot through
   the full graph twice must produce materially the same `Thesis`/`Valuation` (allowing
   for explicitly-scoped stochastic synthesis variance, not silent drift).
5. **Tier 7 model-family diversity enforced by config, not convention**: CI should fail
   if `devils_advocate` and `thesis_synthesizer` resolve to the same underlying model
   for a given run (per `docs/adr/0004-model-routing-policy.md`).
6. **Compliance gate is fail-closed**: if `compliance_mnpi_guardrail` errors or times
   out, the run blocks publication — it must never fail open.
7. **No autonomous trading, structurally enforced**: `portfolio_sizing_advisor`'s
   `requires_approval` is not a default value anywhere in the code path — it should not
   even be a settable field the agent can flip.

---

## 8. Codebase status — refactor complete; package convention per agent

The refactor described in the previous revision of this section is **done**.
`agent/src/agents/specialists/` now matches this document exactly: 8 tier folders,
22 agent packages, and the 8 reclassified services live in `agent/src/services/`
(`notification_service.py`, `evaluation_service.py`'s `run_backtest`/`record_feedback`/
`calibration_curve`, `fact_service.py`'s `compute_comparisons`,
`model_service/formula_graph.py`'s `reconcile`).

### 8.1 Per-agent package convention

Every agent is a Python package, not a single file, so its contract, prompts, and
implementation can evolve independently and be reviewed/tested in isolation:

```
agent/src/agents/specialists/<tier>/<agent_id>/
├── __init__.py   # re-exports the Agent class + SPEC; registers on import
├── spec.py       # AgentSpec: mandate, tier, build_order, depends_on, timeout_s, ...
├── schemas.py    # Pydantic Input/Output models — the typed contract from §5 above
├── agent.py      # BaseAgent subclass; execute() is the only method to implement
└── prompts.py    # Versioned prompt templates (V1, V2, ...) for the agent's model calls
```

### 8.2 Low-latency execution scheduling (new)

`AgentSpec.depends_on` is the single source of truth for execution order —
orchestration stage files no longer hand-write sequential await chains.
`agents/registry.resolve_execution_waves()` topologically sorts a set of agent ids
into "waves" (agents with no dependency on each other run concurrently via
`agents/orchestration/_wave_runner.run_waves()`); a cycle raises `ValueError` at
test time, never at run time. Concretely: Tier 4's three context agents run
concurrently, Tier 6's two agents run concurrently after Tier 4, and Tier 7's
`devils_advocate`/`verification_agent` run concurrently before the adjudicator —
all derived automatically, not hardcoded per stage file.

### 8.3 Resilience (new)

`agents/resilience.py` wraps every agent call (via `BaseAgent.__call__`) with a hard
per-call timeout (`AgentSpec.timeout_s`, default from `Settings.default_agent_timeout_s`),
bounded retry with exponential backoff + jitter (`AgentSpec.retryable`), and a
per-agent circuit breaker (opens after 5 consecutive failures, half-opens after 60s).
`AgentRunResult.latency_ms`/`attempts` record the outcome for observability. This is
what makes the concurrent waves in §8.2 safe in production: one slow/failing agent
cannot silently stall an entire wave or trigger a retry storm against a struggling
provider.

### 8.4 Remaining implementation work (unchanged from before)

Every `agent.py`'s `execute()` still raises `NotImplementedError` — the contracts,
schemas, prompts, and scheduling are now fixed and tested (see
`agent/tests/contract/test_agent_spec_schema.py`, `agent/tests/unit/test_resilience.py`,
`agent/tests/unit/test_registry_waves.py`, and one stub per agent under
`agent/tests/unit/specialists/`), but the actual model calls and deterministic-service
implementations are the next phase of work, per the build checklist in each agent's
§5 entry above.

