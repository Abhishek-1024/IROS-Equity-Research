<div align="center">

# 📊 IROS — Institutional Research Operating System

### An 8-desk, 25-agent AI equity-research pipeline that works like a real investment committee — propose, attack, verify, judge, clear — never the same voice twice.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-teal.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](agent/pyproject.toml)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)](frontend/package.json)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C)](docs/adr/0001-orchestration-langgraph.md)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](agent/src/api/main.py)
[![Local-first LLM](https://img.shields.io/badge/LLM-Ollama%20%2F%20local--first-8A2BE2)](agent/src/agents/routing.py)
[![Tests](https://img.shields.io/badge/backend%20tests-178%20passed-brightgreen)](agent/tests)
[![Zero-hallucination policy](https://img.shields.io/badge/citations-required%20on%20every%20claim-critical)](docs/AGENTS_MASTER_REFERENCE.md)

**Repository maintainer:** [Abhishek Maheshwari](https://github.com/Abhishek-1024)  
**Provenance:** Imported from [tejaskhadke3103/IROS_Equity_Research](https://github.com/tejaskhadke3103/IROS_Equity_Research); original contributor attribution is retained under the Apache 2.0 licence.

**No paid data feeds. No cloud LLM required. Runs entirely on your machine.**

[Quick Start](#-quick-start) · [Live Features](#-live-features) · [The 25 Agents](#-the-8-desk--25-agent-pipeline) · [Screens](#-what-it-looks-like) · [Tech Stack](#-tech-stack) · [Docs](#-documentation)

</div>

---

## 🧠 What is this?

IROS automates the actual, end-to-end workflow of a senior institutional equity-research
analyst — the kind of work a hedge fund associate does by hand across a dozen browser
tabs and three spreadsheets:

```
ticker in  →  pull real filings  →  extract typed facts  →  5 specialist analysts
           →  build/value a real 3-statement + DCF model  →  bull case vs. devil's
           advocate vs. independent verification  →  a single, evidence-linked,
           citation-required decision  ← human approves before anything publishes
```

Every number in the final decision traces back to a real source (SEC EDGAR filing,
live Yahoo Finance quote, or an earlier agent's own cited output) — **never a fabricated
figure.** If an agent doesn't have enough real evidence to answer, it says so
(`status: "abstained"`) instead of guessing.

## ✨ Live Features

This isn't a static demo — every one of these is a real, working feature backed by
real data and a real local LLM, right now, on your laptop:

| | Feature | What makes it "live" |
|---|---|---|
| 📈 | **Real-time ticker dashboard** | Live Yahoo Finance quotes, ratios, peer comps, 52-week range, analyst targets — for *any* real ticker, not a fixture |
| 🤖 | **Grounded AI analyst summaries** | Generated on-demand by a local LLM, with a **fact-check counter** showing exactly how many of the provided real figures were actually cited |
| ✅ | **207-point data-quality validation** | Deterministic Python checks (traceability, determinism, citation, plausibility) re-run live, every time, against whatever ticker you ask for |
| 🔄 | **8-desk staged workflow** | Watch the pipeline move desk-to-desk in real time over a WebSocket, or run it fully autonomously end-to-end |
| 🧮 | **Live-formula Excel export** | Downloads a real `.xlsx` DCF/3-statement model — every forecast cell is an actual Excel formula (not a static number), cross-sheet linked, with a self-auditing "Formula Audit" sheet |
| 📡 | **Continuous monitoring daemon** | Polls your watchlist for material price moves / earnings dates and autonomously kicks off a fresh research run when something real happens |
| 💬 | **Evidence-grounded Notebook** | Ask a follow-up question about any completed run — every answer cites the exact fact/claim it came from, or honestly says "not answerable" |
| 🚦 | **Live connector health board** | One click probes real Yahoo Finance / SEC EDGAR / Ollama endpoints and reports actual latency, not a canned status |

## 🏛️ The 8-Desk / 25-Agent Pipeline

Every research run moves through 8 desks. Four collaboration patterns govern how
agents on the same desk work together — sequential handoff, parallel wave, gated
parallel, and (for the one desk where it matters most) a deliberately
non-parallelizable adversarial chain:

```mermaid
flowchart TD
    D1["🎯 Desk 1 — Mandate & Coverage<br/><i>Research Planner → Entity Resolver</i>"]
    D2["📥 Desk 2 — Data Acquisition<br/><i>SEC EDGAR + IR/news connectors (parallel)</i>"]
    D3["📄 Desk 3 — Document & Fact Extraction<br/><i>Parse → typed facts → transcript intel</i>"]
    D4["🔬 Desk 4 — Fundamental & Context Research<br/><i>5 specialist analysts, one frozen fact base</i>"]
    D5["💡 Desk 5 — Strategy & Idea Generation<br/><i>Risk/catalyst map + variant-perception ideation</i>"]
    D6["📐 Desk 6 — Modeling & Valuation<br/><i>3-statement model → DCF / comps</i>"]
    D7["⚖️ Desk 7 — Investment Committee<br/><i>Thesis → Devil's Advocate → Verify → Adjudicate → Compliance</i>"]
    D8["🚀 Desk 8 — Decision, Distribution & Monitoring<br/><i>Size it → publish it → watch for what happens next</i>"]

    D1 --> D2 --> D3 --> D4 --> D5 --> D6 --> D7 --> D8
    D8 -.->|"material trigger detected"| D1
```

**Desk 7 is the heart of the anti-hallucination design** — a real investment
committee's separation of powers, never merged or parallelized:

```mermaid
sequenceDiagram
    participant TS as Thesis Synthesizer
    participant DA as Devil's Advocate
    participant VA as Verification Agent
    participant AD as Adjudicator
    participant CG as Compliance Guardrail

    TS->>AD: Proposes probabilistic thesis (facts only, no new claims)
    par independent attack
        TS-->>DA: frozen thesis
        DA->>AD: Strongest opposing case + alternate explanations
    and independent fact-check
        TS-->>VA: frozen thesis
        VA->>AD: Recomputes every number from raw facts
    end
    AD->>AD: Weighs both, sets final confidence + publishable flag
    AD->>CG: Adjudicated verdict
    CG->>CG: MNPI / information-barrier screen — can OVERRIDE a clean verdict
    Note over CG: A human must still explicitly approve before publication
```

Every one of the 25 agents routes its LLM-backed step through the exact same
`ModelRouter` (`agent/src/agents/routing.py`) — Ollama locally by default, a
deterministic `MockLLMClient` if no provider is configured at all (so the full
pipeline is always exercisable with zero setup), never a direct provider call
from inside an agent. Most agents keep that step thin and narrowly scoped
(classification, a short synthesis paragraph over already-computed/validated
numbers) — every ratio, fact, and score an agent reasons *about* is still
produced by deterministic Python first (calculators, connectors, the shared
formula graph); the LLM step never invents the underlying numbers, only
narrates or classifies over them. Every agent declares a machine-checked
`AgentSpec` (mandate, `depends_on`, required/optional inputs,
`deterministic_validators`, `confidence_rubric`, `escalation_conditions`,
`abstention_conditions`, `timeout_s`) — the table and paragraphs below are
drawn directly from those specs, not a marketing summary of them.

### Quick reference — all 25 agents

| # | Agent | Desk | What it does |
|---|---|---|---|
| 1 | Research Planner | 1 · Mandate & Coverage | Converts the raw mandate into a concrete execution plan — which agents run, in what order, under what budget, with which approval gates |
| 2 | Entity & Universe Resolver | 1 · Mandate & Coverage | Resolves a ticker/company to one canonical Issuer + Security; curates the approved peer set with a recorded reason for every peer |
| 3 | Acquisition Orchestrator | 2 · Data Acquisition | Directs SEC EDGAR / IR / news / webcast connectors to build the source manifest; scores whether coverage is actually sufficient |
| 4 | Expert Notes Ingestion | 2 · Data Acquisition | Parses human-sourced diligence notes / expert-call transcripts into typed facts, flagged for MNPI at ingestion time |
| 5 | Document Intelligence | 3 · Document & Fact Extraction | Classifies and parses every acquired document into structured text/table/image elements with coordinates |
| 6 | Financial Fact Extraction | 3 · Document & Fact Extraction | Extracts typed financial-statement facts, non-GAAP bridges, forward guidance (full lineage), consensus snapshots |
| 7 | Transcript Intelligence | 3 · Document & Fact Extraction | Structures the earnings-call transcript; scores management-language shifts vs. prior calls, every score tied to a quoted excerpt |
| 8 | Financial Integrity | 4 · Fundamental & Context Research | Assesses earnings quality — accruals, cash conversion, one-off items, disclosure integrity |
| 9 | Industry & Competitive Context | 4 · Fundamental & Context Research | Maps market structure, peer KPIs/pricing/strategic moves against the *approved* peer set, supply-chain read-through |
| 10 | Filing Narrative Analyst | 4 · Fundamental & Context Research | Citation-grounded hybrid-RAG (BM25 + embeddings) analysis over the company's real MD&A / Risk Factors filing text |
| 11 | Macro, ESG & Alt-Signal Context | 4 · Fundamental & Context Research | FX/rate/commodity/regulatory sensitivity, news/alt-data sentiment trend, ESG risk with explicit data-availability confidence |
| 12 | Market Data Validation | 4 · Fundamental & Context Research | The 207-point deterministic check — independently re-verifies every market-data fact/ratio and flags anything untraceable or implausible |
| 13 | Risk & Catalyst | 5 · Strategy & Idea Generation | Builds the dated catalyst calendar and a probability/severity-weighted risk taxonomy, every item linked to a thesis pillar |
| 14 | Variant Perception Ideation | 5 · Strategy & Idea Generation | Generates non-consensus hypotheses from cross-source triangulation, each with a mandatory, stated falsification test |
| 15 | Operating Model | 6 · Modeling & Valuation | Maintains the driver-based 3-statement formula graph; every driver change logged as an auditable `EstimateChange` |
| 16 | Valuation Scenario | 6 · Modeling & Valuation | Runs DCF/comps/SOTP valuation; builds probability-weighted base/bull/bear scenarios (probabilities must sum to 1) |
| 17 | Thesis Synthesizer | 7 · Investment Committee | Combines facts + every specialist's conclusions into one explicit, probabilistic `InvestmentThesis` — introduces no new facts |
| 18 | Devil's Advocate | 7 · Investment Committee | Builds the strongest opposing case, alternate explanations, and the conditions under which the thesis fails |
| 19 | Verification Agent | 7 · Investment Committee | Independently recomputes every material number from raw facts and resolves every citation — never trusts a cached result |
| 20 | Investment Committee Adjudicator | 7 · Investment Committee | Weighs thesis vs. Devil's Advocate vs. Verification via a real disagreement-adjudication protocol; sets final confidence + publishability |
| 21 | Compliance & MNPI Guardrail | 7 · Investment Committee | Screens for MNPI risk / information-barrier violations; can override an otherwise-clean verdict; fail-closed on its own error |
| 22 | Portfolio Sizing Advisor | 8 · Decision, Distribution & Monitoring | Advisory position-size/stop-loss/hedge recommendation from thesis + conviction + risk budget — never executes a trade |
| 23 | Report & Notebook Agent | 8 · Decision, Distribution & Monitoring | Generates the cockpit payload + PDF/DOCX/Excel/PPT exports; answers evidence-grounded follow-up questions or abstains honestly |
| 24 | IC Memo Writer | 8 · Decision, Distribution & Monitoring | Assembles the ~10-15 page Investment Committee memo purely from evidence every earlier desk already computed and cited |
| S1 | Continuous Monitoring Agent | 8 · standing (not per-run) | Polls a workspace's watchlist for material triggers and autonomously starts a fresh research run when one is judged significant |

<div align="right"><a href="docs/TESTING.md">↳ Full test &amp; 207-point data-quality breakdown</a></div>

<details>
<summary><b>📋 Desk 1 — Mandate & Coverage</b> (sequential handoff, 2 agents)</summary>

Nothing else can run until this desk produces an unambiguous identity — the
cheapest possible point to catch a wrong-ticker mistake.

**1. Research Planner** (`agent_01_research_planner`) — *no dependencies, first agent in the graph.*
Converts the user's raw mandate (`mandate`, `raw_query`, `workspace_id`) into a
concrete execution plan: which of the other 24 agents actually run, in what
order, under what budget, with which human-approval gates. Validator:
`execution_plan_ids_exist_in_registry` — it can never plan a run around an
agent id that isn't actually registered. Timeout 10s.

**2. Entity & Universe Resolver** (`agent_02_entity_universe_resolver`) — *depends on Research Planner.*
Resolves a ticker/company/identifier to one canonical Issuer + Security
(escalating rather than guessing if genuinely ambiguous), and curates the
approved peer/comparable-company universe with **a recorded reason for every
peer** (validator: `peer_reason_recorded` — an unexplained peer list is
rejected outright). For the built-in `TXN` fixture this is an instant
dictionary lookup; for any real ticker it calls the same live Yahoo Finance
service backing the standalone Ticker Dashboard. Escalates on
`ambiguous_identifier`; abstains on `insufficient_peer_candidates`.

</details>

<details>
<summary><b>📋 Desk 2 — Data Acquisition</b> (parallel wave, 2 agents)</summary>

Both agents depend only on Desk 1's resolved identity, not on each other, so
they run side by side — deliberately kept as two separate surfaces even
though they run concurrently, because they carry very different risk profiles.

**3. Acquisition Orchestrator** (`agent_03_acquisition_orchestrator`) — *depends on Entity & Universe Resolver.*
Directs the connector layer (SEC EDGAR, IR website, web news, webcast/audio,
alt-data — the source-authority-policy service decides what to fetch and in
what order) to build the source manifest, and judges whether the resulting
coverage is sufficient rather than proceeding silently on a gap. Real SEC
EDGAR + news connectors are live today; IR-website/webcast/alt-data remain
fixture-only. Validator: `coverage_score_computed`. Timeout 120s (real
network fetches).

**4. Expert Notes Ingestion** (`agent_04_expert_notes_ingestion`) — *depends on Entity & Universe Resolver.*
Parses analyst-authored diligence notes and expert-network call transcripts —
**human-sourced, permissioned, compliance-sensitive prose**, not machine-
downloaded public documents — into the same typed Fact schema, tagged with a
lower default authority score and an MNPI-marker flag at ingestion time. This
is defense-in-depth with the Compliance & MNPI Guardrail five desks later:
catching a risk marker as early and as cheaply as possible, not relying on
one single downstream gate. Escalates on `possible_mnpi_marker_detected`.

</details>

<details>
<summary><b>📋 Desk 3 — Document & Fact Extraction</b> (gated parallel, 3 agents)</summary>

Document Intelligence must finish parsing before the other two can start —
you can't extract facts from tables that haven't been reconstructed yet.

**5. Document Intelligence** (`agent_05_document_intelligence`) — *depends on Acquisition Orchestrator.*
Classifies every acquired document and parses it into structured text/table/
image elements with coordinates — mostly deterministic layout/OCR/table-
structure processing, with only a thin LLM step for genuinely ambiguous
classification. Validators: `elements_have_coordinates`,
`subtotal_consistency_flagged`.

**6. Financial Fact Extraction** (`agent_06_financial_fact_extraction`) — *depends on Document Intelligence.*
Reads the parsed tables into typed, standardized financial-statement facts,
non-GAAP bridges (with a required bridge for every non-GAAP figure —
validator `non_gaap_fact_has_bridge`), sector KPIs, forward guidance with
full lineage (`guidance_append_only` — a company revising guidance creates a
*new* linked record, it never silently overwrites history), and normalized
analyst-consensus snapshots. Abstains explicitly on `consensus_unavailable`
rather than inventing a number free data sources don't provide.

**7. Transcript Intelligence** (`agent_07_transcript_intelligence`) — *depends on Document Intelligence, runs concurrently with #6.*
Diarizes and structures the earnings-call transcript, then scores wording
shifts, hedging, evasiveness, and specificity against the company's own
historical calls — **every single score is tied to a quoted excerpt**
(validator: `language_score_has_excerpt`), never a bare number. Abstains on
`no_historical_baseline`. Timeout 150s — a
single local Ollama call routinely needs more than a naive 60s once several
agents queue up behind the same local model (all real Ollama calls
serialize through one semaphore in `llm_client.py` — a local single-GPU/CPU
model gets no real speedup from concurrent requests, and past experience
showed concurrent local-Ollama calls can silently drop rather than queue
cleanly, so this codebase deliberately serializes instead).

</details>

<details>
<summary><b>📋 Desk 4 — Fundamental & Context Research</b> (parallel wave, 5 agents)</summary>

Five specialist analysts read the *same frozen fact base* from Desk 3 and
work entirely independently — "five analysts, five angles." Deliberately
**not** further merged into fewer, broader agents: mixing evidence packs
(e.g. company filings with macro feeds) was an explicitly identified failure
mode ("context overload") from the design process, not an oversight.

**8. Financial Integrity** (`agent_08_financial_integrity`) — *depends on Financial Fact Extraction.*
Assesses earnings quality (accruals, cash conversion, one-off items,
stock-based comp) and disclosure integrity (restatements, changed metric
definitions, segment reorganizations) using deterministically pre-computed
ratios/deltas as its input, never computing raw ratios itself in-agent.
Validator: `ratios_via_calculator_tools` — a ratio that didn't come from the
shared calculator tool is rejected.

**9. Industry & Competitive Context** (`agent_09_industry_competitive_context`) — *depends on Entity & Universe Resolver + Financial Fact Extraction.*
Maps market structure, tracks peer KPIs/pricing/strategic moves using the
*approved* peer set from Desk 1 (validator: `comparison_table_matches_peer_set`
— it cannot quietly substitute its own peer list), and builds supply-chain/
customer read-through via the knowledge graph, with an LLM-authored
competitive-position narrative layered on top of the deterministic
peer-comparison table (real Ollama call, ~6-12s typical for a real ticker).

**10. Filing Narrative Analyst** (`agent_10_filing_narrative_analyst`) — *depends on Entity & Universe Resolver only (its own independent real-data fetch).*
Runs a real, citation-grounded hybrid-RAG pipeline (BM25 + embedding
cosine-similarity) directly over the company's own real SEC 10-K/10-Q MD&A
and Risk Factors text, extracting sentiment-tagged (positive/negative/
neutral), citation-grounded highlights — and explicitly abstains rather than
inventing a point when the retrieved text doesn't actually support one
(validator: `every_highlight_has_a_real_citation`). Deliberately placed
here (not gated behind Document Intelligence) so its several-minutes-on-a-
cold-cache RAG cost overlaps with the other four analysts' faster work
instead of sitting on the run's critical path. Results are cached 24h per
ticker. Feeds the IC Memo, not the numeric model.

**11. Macro, ESG & Alternative-Signal Context** (`agent_11_macro_esg_signal_context`) — *depends on Entity & Universe Resolver + Acquisition Orchestrator.*
Maps FX/rate/commodity/regulatory sensitivities and scores news/alt-data
sentiment trend and ESG risk — with **explicit data-availability confidence**
rather than a fabricated score when disclosure is sparse (validator:
`missing_esg_category_lowers_confidence`; abstains per-subscore on
`zero_esg_disclosure_for_subscore` instead of assuming a neutral score).

**12. Market Data Validation** (`agent_12_market_data_validation`) — *depends on Financial Fact Extraction.*
A governance check on the *data itself*, running alongside the research
rather than trusting it blindly: independently re-verifies every real
market-data fact and derived ratio the extraction agent relied on, confirms
every fact traces to a real source citation, recomputes every derived ratio
independently from raw inputs, and flags anything that can't be traced or
looks statistically implausible. 100% deterministic Python (the same shared
`data_quality.py` implementation backing the Ticker Dashboard's "Validate
this data" button and the `scripts/verify_market_data_provenance.py` CLI) —
the one LLM call it makes only turns findings into a plain-English summary,
never judges a number itself. Distinct from `verification_agent` (Desk 7),
which audits the *thesis*, much later, after a lot more has been built on
top of this same data.

</details>

<details>
<summary><b>📋 Desk 5 — Strategy & Idea Generation</b> (parallel wave, 2 agents)</summary>

**13. Risk & Catalyst** (`agent_13_risk_catalyst`) — *depends on Financial Integrity + Industry & Competitive Context + Macro/ESG Signal Context.*
Builds the dated catalyst calendar and the risk taxonomy (operational,
financial, accounting, regulatory, macro, thesis-specific) — every item
probability- and severity-weighted and linked back to a thesis pillar.
Validator: `risk_has_evidence_ref`.

**14. Variant Perception Ideation** (`agent_14_variant_perception_ideation`) — *depends on the same 3 Desk-4 agents as #13.*
Generates non-consensus hypotheses from cross-source triangulation — each
one carrying **a mandatory, stated falsification test** (validator:
`hypothesis_has_falsification_test`; abstains entirely on
`hypothesis_missing_falsification_test` — a hypothesis this system can't
imagine being proven wrong is rejected outright, not published with lower
confidence).

</details>

<details>
<summary><b>📋 Desk 6 — Modeling & Valuation</b> (sequential handoff, 2 agents)</summary>

**15. Operating Model** (`agent_15_operating_model`) — *depends on Financial Fact Extraction + Financial Integrity.*
Maintains the driver-based 3-statement formula graph (revenue, margin,
working capital, capex, tax, share count, cash flow) and produces an
auditable `EstimateChange` for **every single driver update** — validator:
`every_driver_change_has_estimate_change`, so nothing shifts silently.
Confidence is scored by how many drivers are actuals-anchored vs. assumed,
not a flat number.

**16. Valuation Scenario** (`agent_16_valuation_scenario`) — *depends on Operating Model + Entity & Universe Resolver.*
Runs DCF/comps/SOTP/sector-specific valuation against the reconciled model
and builds probability-weighted base/bull/bear scenarios (validator:
`scenario_probabilities_sum_to_one` — a literal arithmetic check, not
advisory). This is the agent behind the Investment Committee's DCF-based
"implied upside/downside vs. current price" figure.

</details>

<details>
<summary><b>📋 Desk 7 — Investment Committee</b> (adversarial chain — the one desk deliberately never parallelized, 5 agents)</summary>

A real investment committee's separation of powers, not a performance
choice — see the sequence diagram above. Three of these five agents are
explicitly documented as **structurally or legally non-mergeable**, on
purpose:

**17. Thesis Synthesizer** (`agent_17_thesis_synthesizer`) — *depends on Valuation Scenario + Risk & Catalyst + Variant Perception Ideation.*
Combines facts and every specialist's conclusions into one explicit
probabilistic `InvestmentThesis` and decision tree. **Introduces no new
facts** — only interpretation of what's already frozen upstream (validator:
`pillar_evidence_refs_resolve`). Not retryable by design (a synthesis step
re-run with slightly different sampling shouldn't silently replace the
thesis being critiqued downstream).

**18. Devil's Advocate** (`agent_18_devils_advocate`) — *depends on Thesis Synthesizer.*
Builds the strongest opposing case, alternate causal explanations, and the
conditions under which the thesis fails — **structurally non-mergeable**
with the synthesizer: a model cannot reliably self-critique its own output,
since confirmation bias lives in the generation process itself, not
something a follow-up instruction removes. Ideally a different model family
than the synthesizer, so failure modes aren't correlated. Validator:
`every_claim_has_citation`.

**19. Verification Agent** (`agent_19_verification_agent`) — *depends on Thesis Synthesizer, runs concurrently with #18.*
Independently resolves every claim's citation (rejecting unresolvable refs)
and **recomputes every material number from raw facts** — it never trusts a
cached result. ~90% deterministic (id-resolution + recomputation via the
shared calculator/valuation tools), with only a thin semantic-entailment
check needing a model call. Documented as the single highest-leverage test
surface in the whole system.

**20. Investment Committee Adjudicator** (`agent_20_investment_committee_adjudicator`) — *depends on Devil's Advocate + Verification Agent.*
Weighs the thesis against the devil's-advocate case and the verification
report, and sets the final, authoritative confidence and publishability
flag — via a real disagreement-adjudication protocol: verification failures
and every unresolved Devil's-Advocate claim each *discount* the thesis's own
confidence (multiplicatively, capped), rather than being averaged away or
ignored, and a numerical discrepancy is outright disqualifying (confidence
forced to 0). **Structurally non-mergeable** with Verification: a
fact-checker and a judge conflated would let a run "grade its own homework."
Abstains on `unresolved_high_severity_conflict` or too high an
`unsupported_claim_rate`.

**21. Compliance & MNPI Guardrail** (`agent_21_compliance_mnpi_guardrail`) — *depends on the Adjudicator, has the final word.*
Screens the thesis, evidence, and source manifest (especially any
Desk-2 Expert Notes content) for MNPI risk, information-barrier violations,
and personal-trading conflicts — **can override an otherwise-clean research
verdict**, because this is a *legal* requirement, not a research-quality
one; it must be independent of the Adjudicator the same way real information
barriers exist between research and compliance desks. **Fail-closed by
design** (validator: `fail_closed_on_error`) — if this agent errors or times
out, the run blocks publication; it must never fail open. Can only flag; a
human compliance officer actually clears a run.

</details>

<details>
<summary><b>📋 Desk 8 — Decision, Distribution & Monitoring</b> (gated parallel + one standing agent, 4 agents)</summary>

Once Compliance clears (or blocks) the thesis, sizing and reporting read
that same verdict and run concurrently.

**22. Portfolio Sizing Advisor** (`agent_22_portfolio_sizing_advisor`) — *depends on Compliance & MNPI Guardrail.*
Translates thesis + conviction + valuation range + a portfolio risk budget
into an advisory position-size/stop-loss/hedge recommendation — **never
executes a trade**. `requires_approval` is hard-coded `True` unconditionally
(validator: `requires_approval_always_true`), and weights are capped by
deterministic concentration limits. Gated on compliance clearance because a
sizing recommendation is itself a "publication" that could leak
MNPI-tainted information.

**23. Report & Notebook Agent** (`agent_23_report_and_notebook_agent`) — *depends on the Adjudicator + Compliance, runs concurrently with #22.*
Generates the unified cockpit payload and PDF/DOCX/Excel/PPT exports (only
once compliance clears — validator: `blocked_if_not_compliance_cleared`),
**and** answers multi-turn natural-language follow-up questions grounded in
that same run's own frozen evidence (bull-thesis pillars, Devil's-Advocate
claims and alternate explanations, risks, catalysts) — every answer must
cite the evidence it came from (validator: `citation_required_in_answers`),
or it explicitly abstains (`not_answerable_from_evidence`) rather than
guessing. This is the agent behind the `/notebook` page.

**24. IC Memo Writer** (`agent_24_ic_memo_writer`) — *depends on nearly everything: Thesis Synthesizer, Devil's Advocate, Verification Agent, the Adjudicator, Compliance, Filing Narrative Analyst, and Portfolio Sizing.*
Assembles a comprehensive ~10-15 page Investment Committee memo (executive
summary, business overview, financial/valuation analysis, bull/bear thesis,
MD&A/Risk-Factors highlights, peer comps, governance/compliance findings,
sized recommendation) purely from evidence every earlier desk already
computed and cited, rendered to an actual PDF on demand. Its LLM step is
deliberately scoped to narrative prose only (section wording/transitions)
layered on top of data every earlier desk already computed and cited — like
the Thesis Synthesizer, it introduces no new facts, numbers, or claims of
its own, keeping the fabrication surface on the single most important
document the system produces as small as possible. Same compliance
publish-gate as #22/#23.

**S1. Continuous Monitoring Agent** (`agent_S1_continuous_monitoring_agent`) — *standing member, not part of the linear per-run pipeline.*
Runs on its own schedule via `agents/orchestration/continuous_ops_graph.py`
(triggered manually from `/admin` in this local-first build, since there's
no external scheduler wired up yet), polling a workspace's watchlist for
candidate triggers (a filing, a price move, a news item) and judging whether
one is *materially* significant enough to justify starting a brand-new
`ResearchRun` — get it wrong one way and it spams the user, get it wrong the
other way and a real event gets missed.

</details>

## 🖥️ What It Looks Like

<table>
<tr>
<td width="34%"><b>Home</b><br/>Search any ticker, or launch the full 8-desk pipeline in staged or full auto-run mode. Recent runs update live.</td>
<td width="33%"><b>Ticker Dashboard</b><br/>Real Yahoo Finance quote, ratios, ownership, analyst targets, on-demand grounded AI summary and 207-point data validation.</td>
<td width="33%"><b>Research Cockpit</b><br/>Live desk-by-desk progress rail, per-agent status, and every cockpit module for a completed run.</td>
</tr>
<tr>
<td><img src="docs/screenshots/home.png" width="100%"/></td>
<td><img src="docs/screenshots/ticker.png" width="100%"/></td>
<td><img src="docs/screenshots/cockpit.png" width="100%"/></td>
</tr>
<tr>
<td colspan="3"><b>Live Decision Dashboard (Graphs & Ratios)</b><br/>PowerBI-style charts showing scenario probabilities, implied valuation, research confidence, and key financial ratios.</td>
</tr>
<tr>
<td colspan="3"><img src="docs/screenshots/decision-dashboard.png" width="100%"/></td>
</tr>
</table>

<details>
<summary><b>See more — real peer-performance/ratio charts, evidence-grounded Notebook, and live connector health board</b></summary>

**Fundamental charts, real data** — relative price performance vs. the approved
peer set (NVDA vs. AMD/AVGO/INTC/MU/SKHY/TXN, rebased to 0%) flowing straight
into the annual ratio-trend charts, all on the Ticker Dashboard's Overview tab:

<img src="docs/screenshots/overview-charts.png" width="80%"/>

| | |
|---|---|
| **Research Notebook** — a real grounded answer (with its evidence citation) to *"what's the biggest risk to the bull thesis?"* against a completed AAPL run | **Admin / Connector Health** — live, on-demand reachability probes against real Yahoo Finance, SEC EDGAR, and the local Ollama instance, never a simulated status |
| <img src="docs/screenshots/notebook.png" width="100%"/> | <img src="docs/screenshots/admin.png" width="100%"/> |

</details>

## ⚡ Quick Start

**Prerequisites:** Python 3.12+, Node 18+, [Ollama](https://ollama.com) installed (macOS/Linux — Windows users, see the note below).

> **Copying or cloning this project onto a new machine?** `agent/.venv`,
> `frontend/node_modules`, and `frontend/.next` are intentionally excluded
> from Git (see `.gitignore`) and from any manual copy/transfer of this
> repository — they are large (over 1GB combined), machine-specific
> dependency/build artifacts, not source code. Nothing is missing if a copy
> of this project arrives without them; `./setup.sh` (Option A below), or the
> manual commands in Option B, regenerate all three:
>
> | Excluded artifact | Regenerated by |
> |---|---|
> | `agent/.venv` | `python3.12 -m venv agent/.venv` then `.venv/bin/pip install -e "./agent[dev]"` — done automatically by `./setup.sh` |
> | `frontend/node_modules` | `npm install` inside `frontend/` — done automatically by `./setup.sh` |
> | `frontend/.next` | Next.js's build cache. Created automatically the first time `npm run dev` runs; no manual build step is required for local use |

### Option A — one command

```bash
./setup.sh
```

This creates the backend virtual environment, installs everything, pulls the
two local Ollama models, sets up both `.env` files (defaulting to **real**
Ollama + **real** live market data, not the deterministic mock), and runs
`npm install` for the frontend. It's fully idempotent — safe to re-run any
time, and it **never overwrites a `.env` file you've already customized.**

Then, in two separate terminals:

```bash
# Terminal 1 — backend  (→ http://localhost:8000)
cd agent && .venv/bin/python main.py

# Terminal 2 — frontend (→ http://localhost:3000)
cd frontend && npm run dev
```

### Option B — manual, step by step

<details>
<summary>Click to expand the equivalent manual commands</summary>

```bash
# 1. Pull the two local models IROS uses (one-time)
ollama pull llama3.1
ollama pull nomic-embed-text

# 2. Backend — FastAPI + LangGraph (SQLite by default, zero containers needed)
cd agent
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
# IMPORTANT: .env.example ships with CLOUD_MODEL_PROVIDER blank and
# USE_REAL_DATA_SOURCES=false, i.e. the deterministic-mock/offline-fixture
# defaults. Open agent/.env and set:
#   CLOUD_MODEL_PROVIDER=ollama
#   USE_REAL_DATA_SOURCES=true
# to get the full real-LLM / real-market-data experience (setup.sh does this
# for you automatically).
.venv/bin/python main.py        # → http://localhost:8000

# 3. Frontend — Next.js cockpit (new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                     # → http://localhost:3000
```

**Windows:** use WSL2 (Ubuntu) and follow the Linux steps above — the codebase
assumes a Unix-like shell (Ollama, `.venv/bin/...`, etc.).

</details>

## 🚶 First Run Walkthrough

1. Open **http://localhost:3000** — you should see a green **"Backend online"**
   indicator in the header within a couple of seconds.
2. Type **`TXN`** into the command bar (a built-in, zero-network demo company
   — no filings download, no API calls, completes in seconds) and click
   **Run**. Watch the 8 desks complete live.
3. Once it finishes, the **Decision Card** on Desk 8 shows a one-sentence
   thesis, a confidence score, and a **Publishable** / **Not publishable**
   flag — click through the earlier desks to see the Bull/Bear debate, the
   risk map, and the estimate bridge that fed into it.
4. Now try a **real ticker** — go to the home page, type `AAPL` (or any real
   ticker) and click one of the quick-shortcut chips, or submit it through the
   command bar. This runs the exact same 8-desk pipeline against **live** SEC
   EDGAR filings and real market data (takes longer — a couple of minutes on
   the first run per ticker, since real filings get chunked and embedded;
   results are cached for 24h).
5. Visit `/ticker/AAPL` directly for the standalone dashboard — click
   **"Generate grounded AI summary"** and **"Validate this data"** to see the
   local LLM and the 207-point deterministic validator in action.
6. Visit `/notebook` once a run has completed and ask it a question like
   *"what's the biggest risk to the bull thesis?"* — the answer will cite the
   exact evidence it came from.
7. Visit `/admin` and click **"Re-check now"** to see live reachability probes
   against Yahoo Finance, SEC EDGAR, and your local Ollama instance.

<details>
<summary>🐳 Optional: Postgres / Redis / MinIO via Docker Compose</summary>

Nothing above requires it — SQLite + local disk is the default and fully
supported path. If you want a real shared Postgres instead:

```bash
docker compose up -d
# then set DATABASE_URL=postgresql+asyncpg://iros:iros@localhost/iros in agent/.env
```

</details>

## 🩺 Troubleshooting

<details>
<summary><b>Backend won't start: <code>the greenlet library is required</code></b></summary>

SQLAlchemy's async engine needs `greenlet`, which only installs automatically
via the `sqlalchemy[asyncio]` extra. Already fixed in `pyproject.toml` — if you
still hit this, run `.venv/bin/pip install -e ".[dev]"` again.
</details>

<details>
<summary><b><code>pip install</code> fails with an SSL certificate error</b></summary>

Some sandboxed/managed environments intercept pip's certificate store. Try
`pip install --upgrade pip` first, or run pip from a plain, unrestricted
terminal rather than an IDE-embedded/sandboxed one.
</details>

<details>
<summary><b>Ollama error: <code>model 'llama3.1' not found</code></b> (even though you pulled a tagged version)</summary>

Ollama does **not** alias a bare model name to a differently-tagged one — e.g.
having `llama3.1:8b` pulled does not satisfy a request for bare `llama3.1`.
Run `ollama pull llama3.1` (no tag) explicitly; it reuses the same blob if you
already have an equivalent tag, so it's cheap.
</details>

<details>
<summary><b>AI narrative / notebook answers look generic or the same every time</b></summary>

Check `agent/.env`: if `CLOUD_MODEL_PROVIDER` is blank, every LLM-backed agent
silently uses a deterministic mock client instead of real Ollama (by design,
so the whole pipeline is exercisable with zero setup). Set
`CLOUD_MODEL_PROVIDER=ollama` (done automatically by `./setup.sh`).
</details>

<details>
<summary><b>Frontend dev server: routes 404 / <code>EMFILE: too many open files, watch</code> in the console</b></summary>

Some sandboxed environments hit native file-watcher limits. Restart with:

```bash
WATCHPACK_POLLING=true npm run dev
```
</details>

<details>
<summary><b>A stray <code>iros.db</code> / <code>data/filings_cache/</code> shows up at the repo root</b></summary>

The backend's SQLite path and filings cache directory are resolved relative
to the current working directory. Always run the backend **from inside
`agent/`** (`cd agent && .venv/bin/python main.py`) — running it from the repo
root creates duplicate database/cache files there instead.
</details>

<details>
<summary><b>A real ticker's research run seems slow or times out</b></summary>

The first research run for any new real ticker chunks and embeds its actual
SEC filings against your local Ollama instance sequentially (deliberately not
parallelized — concurrent requests to one local model can silently drop
calls). This can take a couple of minutes on a first run; results are cached
for 24 hours per ticker afterward. The built-in `TXN` ticker has no such cost
and always completes in seconds — use it for quick iteration.
</details>

<details>
<summary><b>Running the backend test suite shows a SOCKS proxy import error</b></summary>

Some sandboxed terminals set `ALL_PROXY=socks5h://...` by default, and
`httpx` refuses SOCKS proxies without the `httpx[socks]` extra. This is an
environment artifact, not a code issue — run the tests from a plain terminal,
or unset the proxy env vars for that shell.
</details>

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | **LangGraph** (`StateGraph`) — no separate workflow engine, no Temporal |
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy (async) |
| Database | SQLite (default, zero-config) or PostgreSQL (`docker-compose.yml`) |
| LLM routing | Local-first `ModelRouter` → Ollama (`llama3.1`, `nomic-embed-text`) with a deterministic mock fallback |
| Retrieval | Hybrid BM25 + embedding cosine-similarity RAG over real SEC filing text |
| Frontend | Next.js 14 (App Router) · React 18 · TypeScript · Zustand · Recharts |
| Real data | `yfinance` (live quotes/fundamentals) · `sec-edgar-downloader` (real filings) |
| Modeling | `openpyxl` (live-formula Excel export) · `formulas` (independent formula re-verification) |
| Testing | pytest + Hypothesis (backend, 178 passing) · Vitest + Playwright (frontend) |

## 🔒 Private & Local-First

- Runs entirely on your machine — the only outbound calls are to SEC EDGAR, Yahoo
  Finance, and your own local Ollama instance.
- No account, no signup, no telemetry.
- Secrets live in a gitignored `.env` — only `.env.example` (no real values) is tracked.
- Every export/publication action is gated behind an explicit compliance clearance
  and human approval — nothing auto-publishes.

## 🧪 Quality Bar

- **178 backend tests passing** (pytest + Hypothesis property tests), 2 intentional `xfail` — see
  **[the full breakdown by category, plus the complete 207-point data-quality check reference, in docs/TESTING.md](docs/TESTING.md)**.
- Full frontend suite: Vitest unit tests + a real Playwright end-to-end test that
  drives the actual browser through submit → 8-desk run → populated decision card.
- Deterministic validators run *inside* several agents themselves (e.g.
  `every_claim_has_citation`, `blocked_if_not_compliance_cleared`,
  `disagreement_protocol_applied`) — not just external test assertions.
- A dedicated `verification_agent` independently recomputes every material number
  from raw facts before the Adjudicator ever sees the thesis — it never trusts a
  cached result.

## 📁 Project Structure

The codebase is organized **one folder per agent, grouped one folder per desk**
— the folder tree itself is the agent roster. Every agent folder follows the
same internal shape (`agent.py` the implementation, `spec.py` the machine-
checked `AgentSpec`, `prompts.py` for its LLM-backed step):

```
Equity_Research/
├── setup.sh                       One-command local setup (idempotent, see Quick Start)
├── docker-compose.yml              Optional Postgres/Redis/MinIO for production-scale runs
│
├── agent/                          Python backend — FastAPI + LangGraph
│   ├── src/agents/
│   │   ├── graph.py                 Compiles the LangGraph StateGraph from every registered agent
│   │   ├── base_agent.py            Shared BaseAgent: validates required_inputs, timing, error handling
│   │   ├── registry.py              Agent registration + dependency-graph topological sort
│   │   ├── routing.py               ModelRouter — Ollama vs. mock-LLM selection (see Tech Stack)
│   │   ├── state.py                 The typed ResearchState every agent reads/writes
│   │   │
│   │   ├── orchestration/           Desk-level wave runners + the standing continuous-ops graph
│   │   ├── checkpointing/           LangGraph checkpoint persistence (SQLite/Postgres)
│   │   │
│   │   └── specialists/             ← the 25-agent roster, one folder per desk
│   │       ├── desk1_mandate_coverage/
│   │       │   ├── agent_01_research_planner/
│   │       │   └── agent_02_entity_universe_resolver/
│   │       ├── desk2_data_acquisition/
│   │       │   ├── agent_03_acquisition_orchestrator/
│   │       │   └── agent_04_expert_notes_ingestion/
│   │       ├── desk3_document_fact_extraction/
│   │       │   ├── agent_05_document_intelligence/
│   │       │   ├── agent_06_financial_fact_extraction/
│   │       │   └── agent_07_transcript_intelligence/
│   │       ├── desk4_fundamental_context_research/
│   │       │   ├── agent_08_financial_integrity/
│   │       │   ├── agent_09_industry_competitive_context/
│   │       │   ├── agent_10_filing_narrative_analyst/
│   │       │   ├── agent_11_macro_esg_signal_context/
│   │       │   └── agent_12_market_data_validation/
│   │       ├── desk5_strategy_idea_generation/
│   │       │   ├── agent_13_risk_catalyst/
│   │       │   └── agent_14_variant_perception_ideation/
│   │       ├── desk6_modeling_valuation/
│   │       │   ├── agent_15_operating_model/
│   │       │   └── agent_16_valuation_scenario/
│   │       ├── desk7_investment_committee/
│   │       │   ├── agent_17_thesis_synthesizer/
│   │       │   ├── agent_18_devils_advocate/
│   │       │   ├── agent_19_verification_agent/
│   │       │   ├── agent_20_investment_committee_adjudicator/
│   │       │   └── agent_21_compliance_mnpi_guardrail/
│   │       └── desk8_decision_distribution_monitoring/
│   │           ├── agent_22_portfolio_sizing_advisor/
│   │           ├── agent_23_report_and_notebook_agent/
│   │           ├── agent_24_ic_memo_writer/
│   │           └── agent_S1_continuous_monitoring_agent/    (standing, not per-run)
│   │
│   ├── src/api/                     FastAPI app — REST routers (routers/) + WebSocket (websocket.py)
│   ├── src/core/                    Settings/config, structured errors, observability, security
│   ├── src/db/                      SQLAlchemy async engine, ORM models, migrations
│   ├── src/domain/                  Shared typed schemas (facts, runs, portfolio, strategy, sources…)
│   ├── src/fixtures/                The built-in "TXN" demo company fixture
│   │
│   ├── src/services/                 Deterministic, non-agent business logic
│   │   ├── market_data/               Real Yahoo Finance + SEC EDGAR: quotes, ratios, DCF/3-statement
│   │   │                              model, Excel export, sector-specific archetypes (bank/REIT/etc.)
│   │   ├── filings_rag/               Hybrid BM25 + embedding retrieval over real SEC filing text
│   │   ├── connectors/                Real SEC EDGAR + news connectors
│   │   ├── model_service/             FormulaGraph — the shared 3-statement formula graph engine
│   │   ├── memory_service/            Cross-run thesis-version history
│   │   ├── evaluation_service.py      Calibration-curve scoring for past predictions vs. outcomes
│   │   └── reporting/                 PDF export (IC memo, cockpit reports)
│   │
│   ├── src/cli/                     Operator CLI (validate_research_run.py, etc.)
│   ├── scripts/                     One-off ops scripts (provenance verification, Excel model gen…)
│   └── tests/                       unit / contract / e2e / property / adversarial / golden / calibration
│
├── frontend/                        Next.js 14 research cockpit (App Router + TypeScript)
│   └── src/
│       ├── app/                      Routes: /, /ticker/[symbol], /company/[ticker]/run/[runId]/…,
│       │                             /notebook, /portfolio, /admin, /events
│       ├── components/
│       │   ├── cockpit/               Decision Card, Bull/Bear Debate, Risk Map, Estimate Bridge…
│       │   ├── deskworkflow/           Per-desk agent grid, status pills, desk rail navigation
│       │   ├── command/                Command bar, recent runs, run-progress WebSocket display
│       │   └── market/                 Ticker Dashboard tabs (statements, financial model, ratios…)
│       ├── hooks/                    useDeskWorkflow, useRunWebSocket, useResearchRun(Result)
│       ├── lib/                      apiClient, chart-domain math, formatting helpers, shared types
│       └── state/                    Zustand stores (workspace, run progress, ticker-dashboard cache)
│
└── docs/                            Product spec, architecture, ADRs, master agent reference
```

## 📖 Documentation

| Document | What's in it |
|---|---|
| [docs/TESTING.md](docs/TESTING.md) | **Full test & data-quality reference** — every one of the 180 backend tests (178 passing + 2 intentional `xfail`) explained by category, plus exactly what the 207-point live data-quality validation checks and why |
| [docs/AGENTS_MASTER_REFERENCE.md](docs/AGENTS_MASTER_REFERENCE.md) | Exhaustive, one-agent-at-a-time reference: role, dependencies, inputs/outputs, tools, validators |
| [docs/architecture.md](docs/architecture.md) | System architecture and data flow |
| [docs/data_contracts.md](docs/data_contracts.md) | The typed `ResearchState` every agent reads/writes |
| [docs/workflow_state_machine.md](docs/workflow_state_machine.md) | Staged vs. auto run-mode semantics, approval gates |
| [docs/source_policy.md](docs/source_policy.md) | What counts as a citable source, MNPI/compliance policy |
| [docs/evaluation_plan.md](docs/evaluation_plan.md) | How agent output quality is scored |
| [docs/adr/](docs/adr/) | Architecture Decision Records (orchestration, frontend, storage, model routing) |
| `agent/README.md` / `frontend/README.md` | Per-app setup details |

## 🤝 Contributing

Issues and PRs welcome. Please run the backend suite (`cd agent && pytest -q`) and
the frontend suite (`cd frontend && npm run test && npm run test:e2e`) before
opening a PR — every agent has a `deterministic_validators` contract that real
tests exercise, not just linting.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

Built for analysts who want a research pipeline they can actually audit —
every number cited, every abstention explained, every publish gated on a human.

</div>

