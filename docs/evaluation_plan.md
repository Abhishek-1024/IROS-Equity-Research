# Evaluation Plan

Verbatim mapping of blueprint §14.1 (quality gates) and §14.2 (evaluation dimensions),
implemented in `agent/src/services/evaluation_service.py` and exercised by
`agent/tests/golden/` + `agent/tests/property/`.

## Quality gates before publication (all enforced in `stage10_adjudication.py` / `stage11_output_generation.py`)

1. Critical source coverage threshold met or explicit waiver recorded.
2. Entity and canonical period confidence above threshold.
3. Financial statements and model pass deterministic reconciliation.
4. Every material number has source/formula lineage.
5. Every material claim has support; contradicting evidence is attached.
6. No unresolved high-severity source conflict.
7. Unsupported-claim rate below configured threshold.
8. Numerical auditor and evidence auditor pass.
9. Devil's advocate completed and adjudicator approved.
10. Human approval required for external publication, model overwrite, or
    trade-related output unless policy allows automation.

## Evaluation dimensions

| Dimension | Metric |
|---|---|
| Acquisition | Expected-source coverage, freshness, time-to-availability, duplicate rate, amendment detection |
| Extraction | Cell accuracy, header association, units, period mapping, table reconstruction, transcript speaker/timestamp accuracy |
| Numerical | Reconciliation pass rate, formula accuracy, valuation reproducibility, estimate-bridge accuracy |
| Grounding | Citation precision/recall, unsupported-claim rate, source-authority correctness, conflict visibility |
| Analytical | Material omission rate, thesis-impact accuracy, causal reasoning score, alternative-explanation quality |
| Consistency | Repeated-run agreement, agent disagreement rate, workflow determinism given fixed snapshot |
| Usefulness | Analyst rating, edits required, time saved, questions generated, decisions improved |
| Outcome learning | Forecast error, catalyst calibration, probability calibration, management-credibility prediction |
| Product | Latency, cost, failure recovery, user completion, approval time, export success |
| Security | Permission violations, data leakage tests, deletion verification, audit completeness |

## Testing pyramid

Unit → contract (every agent schema, connector, service API, model provider) → golden
document (known filings/decks/transcripts/Excel models) → property-based (accounting
identities, sign conventions, currency/unit conversion) → end-to-end (ticker → sources →
facts → model → note → evidence click-through) → adversarial (missing guidance,
restatement, changed units, conflicting sources, blocked webcast, mislabeled quarter,
duplicate documents, prompt injection) → regression (every production failure becomes a
permanent test case) → human benchmark (senior analysts score factuality, insight,
omissions, actionability).
