# Data Contracts — Canonical Objects

Source of truth for `agent/src/domain/*.py`. Mirrors the master blueprint §12.4, plus the
explicit schemas from §5.3 (`CanonicalPeriod`), §5.4 (`EvidenceItem`), §6.3
(`EstimateChange`), §9.1 (`InvestmentThesis`), and §4.1 (`AgentSpec`).

## Identity (`domain/identity.py`)
- **Issuer**: `issuer_id, legal_name, country, sector, industry, identifiers{cik,isin,lei}, parent_issuer_id`
- **Security**: `security_id, issuer_id, ticker, exchange, share_class, currency, is_adr`
- **CanonicalPeriod**: `issuer_id, fiscal_year, fiscal_quarter, period_type, start_date, end_date, earnings_date, company_label, normalized_label, calendar_label, comparison_period_ids[], source_evidence[], confidence`

## Events & sources (`domain/events.py`, `domain/sources.py`)
- **ResearchEvent**: `event_id, issuer_id, period_id, event_type, occurred_at, status`
- **SourceArtifact**: `source_id, event_id, source_type, url, authority_score, access_policy`
- **SourceVersion**: `source_version_id, source_id, content_hash, downloaded_at, http_headers, parser_version`
- **DocumentElement**: `element_id, source_version_id, page, slide, section, table, cell, timestamp_start, timestamp_end, raw_text, coordinates, parser_confidence`

## Facts & evidence (`domain/facts.py`)
- **Fact**: `fact_id, issuer_id, period_id, metric_id, value, units, currency, accounting_basis, dimensions{}, source_refs[], confidence`
- **MetricDefinition**: `metric_id, name, formula, unit, frequency, sector_ontology_id, comparability_rules`
- **EvidenceItem** *(verbatim from blueprint §5.4)*:
  `evidence_id, issuer_id, event_id, period_id, source_id, source_version_id, source_type, authority_score, page, slide, section, table, cell, timestamp_start, timestamp_end, raw_text, normalized_fact, units, currency, accounting_basis, claim_supported, support_direction, materiality, confidence, extractor_version, validator_results[], conflicts[], created_at`
- **Claim**: `claim_id, statement, supporting_evidence_refs[], contradicting_evidence_refs[], confidence`
- **Conflict**: `conflict_id, field, source_a_ref, source_b_ref, severity, resolution_status`

## Modeling & valuation (`domain/modeling.py`)
- **Model / ModelVersion**: `model_id, issuer_id, version, layers{historical,driver,forecast,scenario,valuation,audit}`
- **Assumption**: `assumption_id, model_version_id, name, value, unit, rationale, evidence_refs[]`
- **EstimateChange** *(verbatim from blueprint §6.3)*:
  `model_version_before, model_version_after, line_item, period_id, old_value, new_value, absolute_delta, percent_delta, driver_change, rationale, evidence_refs[], agent_id, user_override, approval_status, timestamp`
- **Scenario**: `scenario_id, model_version_id, name, probability, assumption_overrides{}`
- **Valuation**: `valuation_id, model_version_id, method, range_low, range_mid, range_high, sensitivities{}`

## Strategy (`domain/strategy.py`)
- **Catalyst**: `catalyst_id, issuer_id, description, expected_date, probability, expected_direction, expected_magnitude, dependencies[]`
- **Risk**: `risk_id, issuer_id, category, description, probability, severity, mitigations[], thesis_refs[]`
- **Thesis** (`InvestmentThesis`, verbatim from blueprint §9.1):
  `issuer_id, security_id, version, horizon, one_sentence_view, market_view, variant_view, pillars[{claim,evidence_refs,assumption_refs,confidence}], contradicting_evidence[], catalysts[], risks[], scenario_probabilities, valuation_range, expected_return_distribution, falsification_conditions[], unresolved_questions[], portfolio_context, status, approved_by`

## Runs & audit (`domain/runs.py`)
- **AgentSpec** *(verbatim from blueprint §4.1)*:
  `id, version, mandate, domain, allowed_tools, required_inputs[], optional_inputs[], output_schema, deterministic_validators[], confidence_rubric, escalation_conditions[], abstention_conditions[], max_cost, max_latency, reviewer_agent, prompt_template_id`
- **AgentRun**: `agent_run_id, agent_id, research_run_id, inputs, outputs, evidence_refs[], cost, latency_ms, confidence, validation_results[]`
- **ResearchRun**: `research_run_id, mandate, security_id, period_id, workspace_id, state, checkpoint_id, outputs[], errors[], approvals[]`
- **UserOverride**: `override_id, target_object_type, target_object_id, field, old_value, new_value, user_id, reason, timestamp`
- **Approval**: `approval_id, research_run_id, gate, approved_by, decision, comment, timestamp`
- **AuditEvent**: `audit_event_id, actor, action, target_object_type, target_object_id, timestamp, metadata{}`

## Portfolio (`domain/portfolio.py`)
- **PortfolioExposure**: `portfolio_id, position_id, security_id, benchmark, factor_exposures{}, direct_event_refs[], indirect_event_refs[], risk_contribution`

## Agent output envelope

Every agent node returns (per blueprint §4.1):
`status, result, evidence_refs, calculations, assumptions, conflicts, missing_data, confidence, quality_checks, warnings, next_actions`
