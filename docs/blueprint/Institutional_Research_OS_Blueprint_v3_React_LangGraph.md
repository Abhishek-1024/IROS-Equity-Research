# Institutional Research Operating System (IROS)
### Master Product Blueprint — v3 (React + LangGraph Edition)

> **Revision notes (v2 → v3):** This version supersedes the technology ambiguity in the
> v2 blueprint. Two decisions are now final and apply everywhere in this document and in
> the codebase:
> 1. **Frontend is React (Next.js + TypeScript), full stop.** Streamlit is removed from
>    every mention, including "internal prototype" — the admin/developer workbench is a
>    gated route inside the same React app, not a second tool.
> 2. **LangGraph is the single orchestration engine** for the entire research lifecycle
>    (Stage 0 → Stage 12) *and* every specialist-agent subgraph — not just the inner
>    agent-reasoning subgraphs as v2 suggested. Temporal is removed as a separate
>    production-workflow layer; durability/resumability come from LangGraph's Postgres
>    checkpointer plus idempotent node design. See `docs/adr/0001-orchestration-langgraph.md`
>    and `docs/adr/0002-frontend-react-nextjs.md` for the full rationale and trade-offs.
>
> All other product scope, agent mandates, data contracts, and phasing are unchanged
> from v2 and are restated below for a single source of truth.

Purpose: automate the end-to-end workflow of a senior institutional equity researcher
and hedge-fund analyst while preserving evidence, numerical integrity, repeatability,
and human-grade judgment.

Designed for a local-first, hybrid-model, enterprise-ready research super-app.

## Document Map
1. Product definition and hedge-fund operating philosophy
2. Final user experience and research cockpit
3. End-to-end research lifecycle
4. Multi-agent organization: 36 specialist agents
5. Data acquisition, normalization, provenance, and period resolution
6. Financial statements, KPIs, modeling, valuation, and scenario analysis
7. Earnings, transcripts, management behavior, and expectation deltas
8. Company memory, event graph, industry graph, and portfolio context
9. Thesis formation, differentiated insight, debate, and decision support
10. Sector-specific research ontologies
11. AI limitations and engineered mitigations
12. Technical architecture, data schemas, APIs, orchestration, and deployment *(edited for React + LangGraph)*
13. UI/UX system and analyst workflows
14. Reliability, security, observability, testing, and evaluation
15. Edge cases and exception handling
16. Delivery roadmap and team design
17. Master build prompt *(edited for React + LangGraph)*
18. Phased implementation prompts and acceptance criteria — see `docs/product_spec.md` for the **condensed 5-step / 5-prompt** version used in this repository

---

## 1. Product Definition and Hedge-Fund Operating Philosophy

The product is not a chatbot, a transcript summarizer, or a collection of disconnected
dashboards. It is an institutional research operating system that continuously
discovers information, converts raw materials into structured facts, reconciles
numerical and narrative evidence, maintains a persistent company and sector memory,
updates forecasts and valuation implications, challenges its own conclusions, and
presents an auditable decision package to an investor.

The target is to automate the repeatable work of a senior buy-side or sell-side analyst
while preserving the parts of the job that require judgment: data engineer, accounting
analyst, industry analyst, earnings analyst, valuation analyst, forensic reviewer,
catalyst tracker, risk analyst, model reviewer, portfolio-context analyst, and
investment-committee skeptic — as one coordinated system.

### 1.1 Core product promise
- Enter a ticker, company name, portfolio, industry, theme, or research question; the
  system determines the necessary workflow automatically.
- For earnings workflows, select Latest or a fiscal quarter; the platform detects
  available periods and maps fiscal calendars correctly.
- Automatically obtain filings, earnings releases, presentations, webcast audio,
  transcripts, conference appearances, investor-day materials, regulatory disclosures,
  news, industry evidence, and user-authorized internal material.
- Produce a source-cited output answering: what happened, what changed, why, what the
  market expected, what matters for forecasts/valuation, what contradicts the thesis,
  and what to investigate next.
- Preserve every source, fact, calculation, assumption, model revision, agent
  conclusion, reviewer objection, and user edit in a versioned audit trail.
- Deterministic software for calculations/accounting relationships; AI for
  interpretation, synthesis, hypothesis generation, and critique.
- Minimize manual ingestion; manual upload/URL entry/overrides are controlled fallbacks
  only.

### 1.2 Product modes

| Mode | Trigger | Primary output | Typical latency |
|---|---|---|---|
| Earnings Review | Ticker + quarter or Latest | Post-earnings review, estimate bridge, thesis delta, questions | Minutes |
| Initiation / Deep Dive | Ticker + mandate | Business model, industry, historical model, valuation, risks, catalysts, thesis | Hours |
| Continuous Coverage | Watchlist or portfolio | Event alerts, source-linked deltas, model-impact queue, daily/weekly brief | Continuous |
| Idea Generation | Universe + constraints | Ranked candidates, factor/quality screens, variant-perception hypotheses | Minutes-hours |
| Management / Conference Prep | Company + event | Question bank, contradiction log, unresolved issues, incentive map | Minutes |
| Model Update | Company + new event | Reconciled actuals, forecast revisions, scenario changes, valuation update | Minutes |
| Portfolio Context | Portfolio + event | Exposure map, cross-holdings read-through, concentration/factor implications | Minutes |
| Forensic / Red-Team | Company + concern | Accounting quality, disclosure changes, inconsistency map, downside case | Hours |

### 1.3 Non-negotiable product principles
- Evidence before prose: every material claim traces to a source coordinate or
  deterministic computation.
- No silent failure: missing sources, unavailable quarters, blocked webcasts,
  conflicting units, or weak confidence must be surfaced.
- No raw LLM arithmetic: formulas, aggregations, currency conversion, period bridges,
  valuation, and reconciliation run in code.
- Facts, estimates, management claims, market expectations, analyst hypotheses, and
  final conclusions are separate typed object types.
- Reported, adjusted, non-GAAP, constant-currency, organic, pro forma, and
  continuing-operations metrics may never be mixed without an explicit bridge.
- Retain negative evidence and contradictory interpretations rather than smoothing them
  into balanced prose.
- The final user sees a unified research cockpit; specialist pages exist only in an
  administrator/developer workspace **inside the same React app** (gated route, not a
  separate tool).
- Every workflow is resumable, idempotent, observable, testable, and versioned —
  guaranteed structurally by LangGraph checkpoints, not by a separate durability layer.

## 2. Final User Experience and Research Cockpit

The visible product should feel like a single senior analyst who understands the
user's coverage universe, investment style, model conventions, existing thesis,
historical debates, and current portfolio context — never 36 agents or dozens of
technical tabs.

### 2.1 Primary screen

| Area | Function |
|---|---|
| Universal command bar | Accept ticker, company, event, question, portfolio, theme, uploaded model, or natural-language mandate. |
| Context selector | Choose portfolio, strategy, sector ontology, currency, fiscal convention, benchmark, and internal workspace. |
| Workflow suggestion | System proposes Earnings Review, Initiation, Model Update, Conference Prep, Risk Review, or Custom Research Plan. |
| Run plan | Shows sources to acquire, agents to invoke, expected cost/latency, missing permissions, and confidence prerequisites. |
| Research cockpit | Presents thesis delta, KPI scorecard, estimate bridge, valuation, catalysts, risks, source coverage, debates, confidence. |
| Evidence drawer | Click any number/claim to open the exact filing page, slide, transcript timestamp, table cell, formula, or internal note. |
| Action queue | Approve model changes, assign diligence, save thesis revision, publish note, export Excel/PDF/PPT, or create watch alerts. |

### 2.2 One-click earnings workflow
Ticker/company → resolve identity and fiscal calendar → detect available reporting
periods → acquire official earnings package → parse and reconcile actuals → compare
with consensus, prior guidance, prior quarter, internal model → analyze transcript and
Q&A → update company memory → run sector/peer read-through → generate thesis and
model-impact deltas → red-team the conclusion → present analyst cockpit → export
note/model/evidence pack. **Every arrow above is a LangGraph stage subgraph.**

### 2.3 Cockpit modules
Executive decision card · What changed · Financial scorecard · Estimate bridge ·
Variant perception · Bull/bear debate · Management credibility · Catalyst calendar ·
Risk map · Provenance and quality. Each maps 1:1 to a React component in
`frontend/src/components/cockpit/`.

## 3. End-to-End Research Lifecycle

Stage 0 — Mandate interpretation. Stage 1 — Entity, security, and period resolution.
Stage 2 — Source planning and acquisition. Stage 3 — Document intelligence.
Stage 4 — Structured fact extraction. Stage 5 — Reconciliation and validation.
Stage 6 — Historical and expectation comparison. Stage 7 — Specialized analysis.
Stage 8 — Model and valuation update. Stage 9 — Investment thesis synthesis.
Stage 10 — Critique and adjudication. Stage 11 — Output generation.
Stage 12 — Continuous memory and learning.

Each stage is implemented as a LangGraph subgraph in
`agent/src/agents/orchestration/stage*.py`, composed into the single top-level
`StateGraph` in `agent/src/agents/graph.py`. See `docs/workflow_state_machine.md` for
per-stage detail and human-approval gates.

## 4. Multi-Agent Organization: 36 Specialist Agents

Agents are not independent chatbots. Each has a narrow mandate, typed inputs, allowed
tools, deterministic checks, output schema, confidence rubric, stop conditions, and
reviewer — implemented as a LangGraph node/subgraph. The orchestration graph invokes
only the agents needed for the research mandate.

| # | Agent | Mandate |
|---|---|---|
| 1 | Research Planner | Converts user intent into an execution graph, source requirements, output contract, budget, approval gates. |
| 2 | Entity Resolution | Resolves ticker, issuer, share class, fiscal calendar, corporate actions, ADRs, subsidiaries, identifier history. |
| 3 | Source Strategist | Constructs source priority and field-level authority policy for company/region/event/data type. |
| 4 | IR/Regulatory Acquisition | Discovers/downloads official IR materials, SEC/EDGAR, NSE/BSE, exchange and regulatory documents. |
| 5 | Web/News Acquisition | Collects reputable news, industry sources, press releases, blogs, newsletters, podcasts, event material. |
| 6 | Webcast/Audio Agent | Finds webcast assets, resolves embedded players, downloads permitted media, transcribes locally, aligns timestamps. |
| 7 | Document Classifier | Classifies filing, release, presentation, transcript, model, note, conference material, or irrelevant document. |
| 8 | PDF/Presentation Intelligence | Extracts text, charts, tables, slide hierarchy, images, captions, footnotes, source coordinates. |
| 9 | Table Reconstruction | Rebuilds financial tables with headers, units, periods, dimensions, merged cells, math relationships. |
| 10 | Financial Statement Extractor | Produces standardized IS/BS/CF, segment and non-GAAP bridges. |
| 11 | KPI Ontology Agent | Selects/extracts sector/company-specific operational KPIs, definitions, denominators, comparability. |
| 12 | Guidance Agent | Extracts ranges, midpoint, units, basis, exclusions, FX assumptions, organic/reported basis, prior guidance lineage. |
| 13 | Transcript Structure Agent | Separates prepared remarks, Q&A, speakers, roles, questions, answers, follow-ups, unresolved questions. |
| 14 | Management Language Agent | Tracks wording shifts, confidence, hedging, evasiveness, specificity, incentives, guidance credibility. |
| 15 | Consensus/Expectation Agent | Normalizes consensus, whisper numbers, internal estimates, prior guidance, market-implied expectations. |
| 16 | Accounting Quality Agent | Analyzes accruals, cash conversion, capitalized costs, reserves, one-offs, SBC, leases, tax, earnings quality. |
| 17 | Forensic Disclosure Agent | Detects restatements, changed definitions, missing disclosures, footnote changes, segment reorganizations. |
| 18 | Historical Delta Agent | Builds QoQ, YoY, prior-guidance, prior-language, prior-model, prior-thesis comparisons. |
| 19 | Industry Structure Agent | Maps market size, value chain, economics, cycles, regulation, bottlenecks, structural drivers. |
| 20 | Competitive Intelligence Agent | Tracks peer KPIs, pricing, share, product launches, customer wins, capacity, strategic moves. |
| 21 | Supply-Chain/Customer Agent | Builds customer/supplier exposure, read-through, channel inventory, lead times, capacity, concentration. |
| 22 | Macro/Policy Agent | Maps rates, FX, commodities, regulation, geopolitics, policy changes into company-specific sensitivities. |
| 23 | Operating Model Agent | Maintains driver-based revenue, margin, working-capital, capex, tax, share-count, cash-flow forecasts. |
| 24 | Model Reconciliation Agent | Checks formulas, historicals, statement links, circularities, scenario integrity, balance, change ledger. |
| 25 | Valuation Agent | Runs DCF, SOTP, trading comps, precedent, or sector-specific valuation with transparent assumptions/sensitivities. |
| 26 | Scenario and Probability Agent | Builds base/bull/bear and event trees, assigns probabilities, tests nonlinear downside/upside. |
| 27 | Catalyst Agent | Maintains dated catalysts, dependencies, probabilities, expected impact, monitoring signals, outcomes. |
| 28 | Risk Agent | Builds risk taxonomy, leading indicators, exposure, probability, severity, mitigation, thesis linkage. |
| 29 | Technical/Positioning Agent | Optionally analyzes price action, liquidity, short interest, ownership, flows, positioning, event setup. |
| 30 | Variant Perception Agent | Searches non-consensus interpretations, indirect signals, underappreciated drivers, falsification tests. |
| 31 | Thesis Synthesizer | Combines facts and specialist conclusions into an explicit probabilistic thesis and decision tree. |
| 32 | Devil's Advocate | Constructs the strongest opposing case, alternate causal explanations, conditions under which the thesis fails. |
| 33 | Evidence Auditor | Verifies claim-to-source linkage, source coordinates, support direction, freshness, authority, unsupported claims. |
| 34 | Numerical Auditor | Recomputes every material number, unit, bridge, percentage, multiple, and valuation output independently. |
| 35 | Investment Committee Adjudicator | Resolves agent disagreements, assigns final confidence, enforces abstention rules, determines publishability. |
| 36 | Report/Artifact Agent | Generates cockpit, note, memo, Excel model, PDF, PowerPoint, evidence pack, alerts, machine-readable outputs. |

### 4.1 Agent contract (`AgentSpec`, `agent/src/domain/runs.py`)
```
AgentSpec {
  id, version, mandate, domain, allowed_tools,
  required_inputs[], optional_inputs[], output_schema,
  deterministic_validators[], confidence_rubric,
  escalation_conditions[], abstention_conditions[],
  max_cost, max_latency, reviewer_agent, prompt_template_id
}
```
Every agent returns a typed object: `status, result, evidence_refs, calculations,
assumptions, conflicts, missing_data, confidence, quality_checks, warnings, next_actions`.

### 4.2 Agent disagreement protocol
1. Normalize each conclusion into claim, direction, magnitude, horizon, confidence,
   evidence set.
2. Detect direct contradiction, different time horizon, different scenario assumption,
   or different data basis.
3. Ask each agent to state its decisive assumption and the evidence that would
   falsify it.
4. Run source and numerical audits on disputed inputs.
5. Generate an adjudication matrix showing which conclusion holds under which
   assumptions.
6. If disagreement remains material, present multiple conditional conclusions rather
   than forcing consensus.
7. Persist the disagreement so future outcomes can evaluate which agent/assumption was
   more reliable.

*(Sections 5–11 — data acquisition/provenance, financial modeling/valuation, earnings/
transcript intelligence, company memory/event graph, thesis formation, sector
ontologies, and AI-limitation mitigations — are unchanged from v2 and fully detailed in
`docs/data_contracts.md`, `docs/source_policy.md`, and `docs/evaluation_plan.md`, which
are the maintained, code-adjacent source of truth going forward.)*

## 12. Technical Architecture, Data Schemas, APIs, Orchestration, and Deployment *(edited)*

### 12.1 Recommended architecture
```
Clients: React (Next.js) research cockpit | Admin workbench (gated route, same app) | API | Alerts
API Gateway / Auth / Workspace / Entitlements
LangGraph Orchestrator (single StateGraph; Postgres-checkpointed; resumable; human-in-the-loop gates)
Agent Runtime + Tool Registry + Model Router  (also LangGraph)
------------------------------------------------------------
Acquisition services | Document intelligence | Transcription | Search
Fact store | Evidence store | Time-series DB | Object storage
Company memory | Event/knowledge graph | Vector + keyword indexes
Financial model service | Valuation service | Portfolio analytics
Evaluation | Observability | Audit log | Policy/security layer
------------------------------------------------------------
Deployment: local desktop, single-tenant server, VPC/private cloud, managed SaaS
```

### 12.2 Technology choices (final)

| Capability | Implementation |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, async workers |
| **Workflow orchestration** | **LangGraph only** — one top-level `StateGraph` for the full research lifecycle (Stage 0–12) plus every specialist-agent subgraph, checkpointed to PostgreSQL for durability/resumability. No Temporal layer. |
| Transactional database | PostgreSQL with row-level security and immutable audit tables (also hosts LangGraph checkpoints) |
| Object storage | S3-compatible storage/MinIO for original and derived artifacts |
| Search | OpenSearch/Elasticsearch for keyword/metadata; pgvector/Qdrant for semantic retrieval |
| Graph | PostgreSQL graph model initially; Neo4j only if graph scale justifies it |
| Cache/queue | Redis for caching, locks, rate limits; Kafka/Redpanda for event streams at scale |
| Document parsing | PyMuPDF/pdfplumber, Apache Tika, Unstructured, Camelot/Tabula, OCR/vision fallback |
| Browser acquisition | httpx/requests first; Playwright for dynamic IR sites and authenticated connectors |
| Audio | FFmpeg + faster-whisper/whisper.cpp; diarization where licensing permits |
| Calculation/model engine | Python/NumPy/Pandas/Polars plus a typed formula graph; openpyxl/xlsxwriter for Excel export |
| **Frontend** | **React via Next.js + TypeScript, only.** Server events/WebSockets for live run streaming. **No Streamlit anywhere, including prototyping.** |
| Artifacts | DOCX/PDF via HTML templates/WeasyPrint or Playwright; PowerPoint via python-pptx/PptxGenJS |
| Models | Hybrid router across local models and permitted cloud providers; provider abstraction and model policy by data sensitivity |
| Observability | OpenTelemetry, structured logs, traces, cost/latency dashboards, Sentry, workflow replay |
| Testing | pytest, contract tests, golden datasets, snapshot tests, property-based numeric tests, UI E2E with Playwright |

### 12.3 Service boundaries
Identity · Acquisition · Document · Fact · Evidence · Memory · Model · Analysis
(LangGraph agents) · Report · Evaluation services — see `docs/architecture.md` for full
detail and folder mapping.

### 12.4 Canonical objects
Issuer, Security, CanonicalPeriod, ResearchEvent, SourceArtifact, SourceVersion,
DocumentElement, Fact, MetricDefinition, EvidenceItem, Claim, Conflict, Model,
ModelVersion, Assumption, EstimateChange, Scenario, Valuation, Catalyst, Risk, Thesis,
AgentRun, ResearchRun, PortfolioExposure, UserOverride, Approval, AuditEvent — full field
lists in `docs/data_contracts.md`.

### 12.5 API examples
```
POST /v1/research-runs
{
  "mandate": "post_earnings_review",
  "security": "AAPL",
  "period": "latest",
  "workspace_id": "fund_alpha",
  "outputs": ["cockpit", "pdf", "excel_model_diff"],
  "approval_policy": "human_before_publish"
}

GET  /v1/research-runs/{run_id}
GET  /v1/issuers/{issuer_id}/periods
GET  /v1/events/{event_id}/evidence
POST /v1/models/{model_id}/apply-change-set
POST /v1/theses/{thesis_id}/review
GET  /v1/portfolios/{portfolio_id}/event-impact/{event_id}
```
A WebSocket channel (`/v1/research-runs/{run_id}/stream`) streams LangGraph node/stage
progress to the React cockpit.

### 12.6 Model routing policy
Deterministic code for identity/dates/formulas/reconciliation; small structured-output
model for classification; specialized vision/document model for tables; keyword +
semantic + graph retrieval for long documents; strong reasoning model for thesis
synthesis; an independent model family for critique/adjudication; local/private
endpoint only for confidential data; strong model for final prose only after facts are
frozen. See `docs/adr/0004-model-routing-policy.md`.

## 13–16. UI/UX, Reliability/Security/Testing, Edge Cases, Roadmap

Unchanged from v2 in substance; see `docs/evaluation_plan.md` (§14 quality gates and
testing pyramid) and `docs/product_spec.md` (roadmap, condensed to 5 steps for this
repository). The UI information architecture (Home/Command Center, Company Workspace,
Event Workspace, Portfolio Workspace, Research Notebook, Admin/Developer Workbench) maps
directly onto the React routes in `frontend/src/app/`.

## 17. Master Build Prompt *(edited for React + LangGraph)*

> You are the principal architect and founding engineer for IROS. Build a
> production-minded, local-first/hybrid AI research platform that automates the
> end-to-end workflow of institutional equity research and hedge-fund analysts. The
> final user interacts with **one unified React (Next.js + TypeScript) research
> cockpit**, never Streamlit and never dozens of disconnected agent pages. Specialist
> agents and diagnostics live in an **admin/developer route inside the same React app**.
>
> Orchestrate the entire research lifecycle (Stage 0–12) and every specialist-agent
> subgraph using **LangGraph only**, with a PostgreSQL checkpointer for durability,
> resumability, and human-in-the-loop approval gates. Do not introduce Temporal or any
> second orchestration layer.
>
> All other core principles, required agents, mandatory canonical objects, mandatory
> quality gates, and the "first implementation wedge" (institutional earnings decision
> engine, built before portfolio management/universal initiation/autonomous trading)
> are unchanged from the v2 blueprint and are restated in `docs/product_spec.md`
> §"Hand-off prompts", which contains the condensed, ready-to-run 5-prompt build
> sequence for this specific repository.

## 18. Phased Implementation Prompts

See `docs/product_spec.md` for the **5-step / 5-prompt** condensed build sequence used
in this repository (Foundations & Contracts → Acquisition & Document Intelligence →
Comparisons/Agents/Critique → React Cockpit → Memory/Model/Valuation/Portfolio), and its
acceptance criteria (identical bar to the original blueprint §18.1).

## Closing Product Definition

The system should be thought of as an AI-native investment research firm encoded as
software: it reads, remembers, extracts, calculates, compares, challenges, updates,
explains, and learns. Its competitive advantage will not come from a single model — it
comes from source acquisition quality, canonical data contracts, a deterministic
financial engine, persistent context, sector-specific workflows, adversarial review, a
user-centered React cockpit, and measurable reliability over hundreds of real investment
decisions, orchestrated end-to-end by a single LangGraph workflow.
