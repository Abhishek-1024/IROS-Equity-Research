# 🧪 Test & Data-Quality Reference

> Linked from the main [README](../README.md#-quality-bar). This file documents
> **every** automated check in the repository — the 180 backend pytest tests
> (178 passing + 2 intentional `xfail`) and the 207-point live data-quality
> validation pass — so a reviewer can see exactly what's actually being
> verified, not just a badge with a number on it.

```
cd agent && .venv/bin/python -m pytest -q --collect-only   # → 180 tests collected
cd agent && .venv/bin/python -m pytest -q                   # → 178 passed, 2 xfailed
```

---

## 1. Backend pytest suite — 180 tests across 7 categories

| Category | Path | Tests | What it verifies |
|---|---|---|---|
| **Unit** | `agent/tests/unit/` | 109 | Individual agents, services, and orchestration primitives in isolation |
| **Contract** | `agent/tests/contract/` | 57 | Every `AgentSpec` and connector honors its declared machine-checked contract |
| **Adversarial** | `agent/tests/adversarial/` | 6 | Deliberately hostile/edge-case inputs the pipeline must handle safely |
| **Calibration** | `agent/tests/calibration/` | 6 | Confidence-vs-accuracy calibration curve math |
| **Property** | `agent/tests/property/` | 1 (Hypothesis, hundreds of generated cases) | Universal invariants that must hold for *any* valid input |
| **E2E** | `agent/tests/e2e/` | 1 | A full ticker → 8-desk run → evidence click-through, real FastAPI `TestClient` |
| **Golden** | `agent/tests/golden/` | — | Reserved for future golden-output snapshot tests (currently empty) |

### 1.1 Unit tests (109) — `agent/tests/unit/`

**Per-agent unit tests** — `agent/tests/unit/specialists/` covers 23 of the 25 agents individually
(each file exercises that agent's `execute()` in isolation: required-input validation, its
deterministic validators, its abstention/escalation conditions, and its fixture-ticker vs.
real-ticker branching):

`test_research_planner` · `test_entity_universe_resolver` · `test_acquisition_orchestrator` ·
`test_expert_notes_ingestion` · `test_document_intelligence` · `test_financial_fact_extraction` ·
`test_transcript_intelligence` · `test_financial_integrity` · `test_industry_competitive_context` ·
`test_filing_narrative_analyst` · `test_macro_esg_signal_context` · `test_risk_catalyst` ·
`test_variant_perception_ideation` · `test_operating_model` · `test_valuation_scenario` ·
`test_thesis_synthesizer` · `test_devils_advocate` · `test_verification_agent` ·
`test_investment_committee_adjudicator` · `test_compliance_mnpi_guardrail` ·
`test_portfolio_sizing_advisor` · `test_report_and_notebook_agent` · `test_ic_memo_writer` ·
`test_continuous_monitoring_agent`

**Cross-cutting unit tests** — the shared machinery every agent runs through:

| File | What it verifies |
|---|---|
| `test_base_agent_decision_registry.py` | Every agent call appends a correctly-shaped entry to the audit-trail `decision_registry` |
| `test_context_registry.py` | Prompt-budget-aware context compilation for LLM-backed agents |
| `test_desk_status_computation.py` | Desk-level status (`pending`/`running`/`completed`/`failed`) aggregates correctly from per-agent results |
| `test_extraction_tasks.py` | The filing-RAG narrow-task extraction pipeline (MD&A/Risk-Factors) |
| `test_pdf_export.py` | IC memo / cockpit report PDF rendering |
| `test_period_resolver.py` | Fiscal-period ID resolution (quarters, fiscal-year-ends, mislabeled periods) |
| `test_rate_limit.py` | API rate-limiting middleware |
| `test_registry_waves.py` | Topological-sort dependency resolution into parallel execution waves |
| `test_resilience.py` | `run_with_resilience`'s timeout + retry + circuit-breaker behavior |
| `test_transcript_service.py` | Earnings-call transcript structuring |
| `test_wave_runner_contradictions.py` | Same-desk agents disagreeing on a fact are surfaced as a `Contradiction`, never silently dropped |

### 1.2 Contract tests (57) — `agent/tests/contract/`

Verifies the *structural* guarantees every agent and connector must hold, independent of any
one agent's specific business logic:

| File | What it verifies |
|---|---|
| `test_agent_spec_schema.py` | Every one of the 25 `AgentSpec` declarations is well-formed (valid `id`, `depends_on` references a real agent, `timeout_s` is set, etc.) |
| `test_connectors.py` | SEC EDGAR / news / market-data connectors honor their expected request/response contract |
| `test_context_fields_compaction_boundary.py` | Prompt-budget compaction never silently drops a required field |
| `test_desk_registry.py` | The 8-desk registry's metadata matches the actual agent roster 1:1 |
| `test_llm_client.py` | `MockLLMClient` / `RealLLMClient` both satisfy the same `LLMClient` protocol |

### 1.3 Adversarial tests (6) — `agent/tests/adversarial/test_adversarial_suite.py`

Deliberately hostile or malformed inputs — every one of these must be handled *safely*
(abstain, flag, or reject), never silently produce a wrong or fabricated answer:

- `test_mislabeled_quarter_guidance_keeps_its_own_future_period_id` — guidance for a future quarter
  never gets silently relabeled to the current period
- `test_missing_guidance_does_not_fabricate_a_variant_hypothesis` — no guidance data → no invented
  hypothesis
- `test_unbalanced_balance_sheet_is_never_silently_accepted` — Assets ≠ Liabilities + Equity is
  always flagged, never passed through
- `test_conflicting_reported_vs_recomputed_scenario_is_flagged` — a reported number that disagrees
  with an independent recomputation raises a `Conflict`, never picks one silently
- `test_duplicate_documents_are_deduped_by_content_hash` — the same filing fetched twice (e.g. via
  two connectors) is deduplicated by content hash, not double-counted as evidence
- `test_prompt_injection_in_uploaded_note_still_triggers_mnpi_gate` — a prompt-injection attempt
  embedded in an uploaded expert note still gets caught by the MNPI marker screen

### 1.4 Calibration tests (6) — `agent/tests/calibration/test_calibration_curve.py`

Verifies the confidence-vs-actual-accuracy calibration curve used to score whether an agent's
stated confidence is *honest* over time (fed by `evaluation_service.py` and real outcome records):

- `test_empty_outcomes_abstains_with_no_outcomes_recorded_reason`
- `test_below_min_sample_size_abstains_with_insufficient_sample_reason`
- `test_perfectly_calibrated_predictions_show_matching_confidence_and_accuracy`
- `test_overconfident_agent_shows_accuracy_below_predicted_confidence`
- `test_outcomes_are_bucketed_into_separate_deciles`
- `test_confidence_of_exactly_1_0_lands_in_the_top_bucket_not_an_eleventh_bucket`

### 1.5 Property test (1, Hypothesis) — `agent/tests/property/test_balance_sheet_identity.py`

`test_balance_sheet_identity_holds_when_assets_equal_sum` — a `@given`-generated property test
(hundreds of randomized float inputs per run, not one fixed example) asserting the fundamental
accounting identity `Assets = Liabilities + Equity` holds for *every* valid randomized
liabilities/equity pair, not just a hand-picked one.

### 1.6 E2E test (1) — `agent/tests/e2e/test_full_pipeline_smoke.py`

`test_full_pipeline_ticker_to_evidence_click_through` — drives a real FastAPI `TestClient` through
an actual ticker submission, the full 8-desk pipeline, and a click-through to a cited evidence
item, exercising the real HTTP layer end-to-end (not a mocked router).

### 1.7 The 2 intentional `xfail`

Two tests are marked `xfail` deliberately (not skipped, not broken) — they document a known,
accepted limitation rather than hiding it. Run `pytest -q -rx` to see both with their reasons.

---

## 2. Live 207-point data-quality validation

**Source of truth:** [`agent/src/services/market_data/data_quality.py`](../agent/src/services/market_data/data_quality.py)
— one implementation, three call sites (no duplicated/drifting logic):

1. `agent/scripts/verify_market_data_provenance.py` — a standalone due-diligence CLI
2. The Ticker Dashboard's **"Validate this data"** button (`/v1/market/{ticker}/validate`) — instant, on-demand
3. `agent_12_market_data_validation` — runs automatically as a real LangGraph node on every
   research run that resolves real facts, before anything downstream can build on them

Every check is **100% deterministic Python over real fetched data — zero LLM calls**. The only
LLM involvement anywhere in this path is a separate, later step that turns an already-final
`ValidationReport` into a plain-English summary; the report's PASS/FAIL/WARN content itself is
never touched by a model.

### 2.1 What gets checked, and why the count is ~207

The checker runs against **every fetched historical period** (typically 6-8 quarters/years,
ticker-dependent) **× every one of the 31 tracked ratios**, plus per-period and whole-series checks:

| Check | Runs | What it catches |
|---|---|---|
| **Traceability** | Once per ratio, per period (~31 × periods) | A ratio value exists but one of its *required raw line-item inputs* (e.g. `pe_ratio` needs `market_cap` **and** `net_income`) is missing from the real extracted data — that value cannot be traced to a real source and is rejected outright, never silently displayed |
| **Source-citation tag** | Once per period | Every period must carry a valid source tag (`yahoo`, `sec_edgar`, or `sec_edgar+yahoo`) — an untagged/unknown source fails |
| **Determinism** | Once per period | Recomputing every ratio from the exact same raw line items the original used must reproduce the *same* number — a mismatch means a non-deterministic formula bug, not real-world variance |
| **Plausible sign** | Per applicable ratio (5 ratios: current ratio, cash ratio, asset/inventory/receivables turnover) | Flags a negative value for a ratio that should structurally never be negative |
| **Plausible magnitude** | Per applicable ratio (7 ratios: margins, ROE, ROA, effective tax rate) | Flags a value outside a sane real-world cap (e.g. gross margin > 150%) — usually a unit or extraction bug |
| **Wide dynamic range** | Once, whole series | Flags any ratio whose max/min spread across fetched periods exceeds 8× — the same threshold the frontend chart uses to decide whether to switch to a log axis, so a human is told *why* a chart looks the way it does |

The 31 tracked ratios (`REQUIRED_INPUT_GROUPS` in `data_quality.py`): `pe_ratio`, `ps_ratio`,
`pb_ratio`, `ev_to_ebitda`, `ev_to_revenue`, `gross_margin`, `operating_margin`, `net_margin`,
`ebitda_margin`, `roe`, `roa`, `current_ratio`, `cash_ratio`, `debt_to_equity`, `debt_to_ebitda`,
`interest_coverage`, `equity_multiplier`, `asset_turnover`, `inventory_turnover`,
`receivables_turnover`, `eps_diluted`, `eps_basic`, `book_value_per_share`, `fcf_per_share`,
`revenue_per_share`, `dividend_per_share`, `payout_ratio`, `fcf_margin`, `fcf_yield`,
`capex_to_revenue`, `net_debt_to_ebitda`, `effective_tax_rate`.

For a real ticker with a typical 6-7 periods of historical coverage, `(31 ratios × ~6.5 periods)
+ per-period determinism/citation checks + the one whole-series dynamic-range check` lands right
around **207 total checks run** — the exact number moves slightly with how many historical
periods a given ticker's filings actually provide (that's real data, not a hardcoded constant),
which is why the dashboard always reports the *actual* `checks_run` count for whatever ticker you
validate, not a fixed label.

### 2.2 Reproducing it yourself

```bash
cd agent
.venv/bin/python scripts/verify_market_data_provenance.py AAPL
```

Or from the running app: open `/ticker/AAPL`, click **"Validate this data"**, and expand the
report — every failure/warning line names the exact ratio, period, and reason.

---

## 3. Frontend test suite

| Type | Command | What it covers |
|---|---|---|
| Unit (Vitest) | `cd frontend && npm run test` | Component logic, formatting helpers, Zustand stores |
| E2E (Playwright) | `cd frontend && npm run test:e2e` | A real browser driven through submit → live 8-desk run → populated Decision Card |

---

<div align="center">

[← Back to README](../README.md)

</div>
