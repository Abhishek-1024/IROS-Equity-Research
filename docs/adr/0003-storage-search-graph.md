# ADR 0003: Storage, search, and graph layer

## Status
Accepted

## Decision
- **PostgreSQL**: system of record for all canonical objects, immutable audit tables,
  row-level security for tenant isolation, and the LangGraph checkpoint store.
- **S3-compatible object storage (MinIO for local/dev)**: original and derived source
  artifacts (filings, decks, audio, transcripts), content-hashed and versioned.
- **OpenSearch**: lexical/metadata search over documents, facts, and transcripts.
- **pgvector (default) / Qdrant (optional at scale)**: semantic retrieval over chunked,
  coordinate-preserving document elements.
- **Event/company knowledge graph**: modeled in Postgres initially (edge/node tables)
  behind a graph-service interface; migrate to Neo4j only if graph traversal scale
  justifies the operational cost, per blueprint guidance.

## Consequences
Keeps the local-first deployment story simple (Postgres + MinIO + OpenSearch, all
dockerizable) while leaving a clean seam to introduce Qdrant/Neo4j later without
changing service interfaces (`agent/src/services/memory_service`, `evidence_service.py`).
