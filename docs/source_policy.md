# Source Policy — Authority Hierarchy & Conflict Rules

Verbatim mapping of blueprint §5.1, implemented in `agent/src/services/identity_service.py`
(period/entity) and `agent/src/services/acquisition_service/` (source ranking).

| Data field | Preferred authority | Secondary source | Conflict rule |
|---|---|---|---|
| Reported GAAP actuals | Regulatory filing / audited release | Company presentation / data vendor | Filing wins unless amended; preserve release variance |
| Non-GAAP actuals | Company reconciliation table | Transcript / presentation | Require explicit reconciliation and definition |
| Guidance | Latest official earnings release / filing | Transcript clarification | Track timestamp and basis; do not overwrite prior range |
| Management commentary | Official transcript/webcast | Third-party transcript | Keep speaker and timestamp; compare wording historically |
| Consensus | Licensed vendor or user model | Public estimates | Store vendor, timestamp, contributor count, and basis |
| Internal forecast | Approved user model | AI-generated forecast | Never silently replace an approved analyst estimate |
| News/event facts | Primary source or top-tier outlet | Secondary outlets / social | Triangulate material claims; rank source reliability |
| Industry data | Regulator, association, specialist vendor | Consulting/news estimates | Store methodology, geography, period, and definition |

## Acquisition engine requirements

- Connector registry: each connector declares region, source type, authentication,
  robots/licensing policy, rate limit, parser, freshness, and health.
- Artifact preservation: original bytes, content hash, download URL, resolved URL,
  HTTP headers, timestamp, parser version, access policy — never delete superseded
  versions.
- Coverage score: expected vs. acquired documents per event; never claim completion
  when a critical source is missing.
- Fallback sequence: official transcript → webcast audio transcription → filing/
  release/deck-only analysis → explicit data-gap result with manual fallback.

## Period resolution rules

A single `CanonicalPeriod` service is the only source of fiscal period truth (see
`docs/data_contracts.md`). No other module may invent Q1/Q2 formatting. If a requested
period is unavailable, return the latest available period plus an explicit suggested
substitution. If sources disagree on period, the workflow pauses before extraction.
