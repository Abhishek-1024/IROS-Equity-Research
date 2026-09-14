# ADR 0002: React (Next.js + TypeScript) as the only frontend

## Status
Accepted

## Context
The blueprint listed Next.js/React/TypeScript as the production frontend and allowed
Streamlit "only for an internal prototype/admin workbench". The user wants React only,
with no Streamlit anywhere (including prototyping), and one unified cockpit for normal
users plus a hidden admin/developer workbench route for agent diagnostics.

## Decision
- Use **Next.js (App Router) + React 18 + TypeScript** for the single frontend
  application in `frontend/`.
- The **Company/Event/Portfolio/Notebook** routes are the unified analyst cockpit.
- The **Admin route** (`/admin`) is the developer workbench (connector health, agent
  traces, prompts, evaluations, source conflicts) — same codebase, gated by role,
  not a separate Streamlit app.
- Communicate with the backend via typed REST (`src/lib/apiClient.ts`) for
  request/response calls and WebSockets (`src/hooks/useRunWebSocket.ts`) for
  streaming `ResearchRun` progress from LangGraph node/stage events.

## Consequences
- One deployable frontend, one design system, one accessibility/testing pipeline
  (Playwright E2E), instead of maintaining a second Streamlit app.
- The admin workbench must implement its own access control instead of getting it
  "for free" from a separate internal tool — handled via the shared auth/role layer.

## Alternatives considered
- **Streamlit for admin/prototype**: rejected per explicit user direction — removes an
  entire second tech stack and duplicated auth/data-fetching logic.
- **Plain Vite SPA instead of Next.js**: viable, but Next.js's file-based routing and
  API-route colocation better match the blueprint's "Company/Event/Portfolio/Notebook/
  Admin workspace" information architecture and future SSR/streaming needs.
