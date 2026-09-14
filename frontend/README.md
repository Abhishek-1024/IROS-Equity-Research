# IROS Frontend

React (Next.js App Router) + TypeScript research cockpit. No Streamlit anywhere —
see [../docs/adr/0002-frontend-react-nextjs.md](../docs/adr/0002-frontend-react-nextjs.md).

## Layout

```
src/
├── app/            Routed pages: home, company/[ticker], events/[eventId],
│                   portfolio, notebook, admin (gated developer workbench)
├── components/
│   ├── cockpit/    Decision card, what-changed, scorecard, estimate bridge,
│   │               variant perception, bull/bear debate, management credibility,
│   │               catalyst calendar, risk map, provenance/quality
│   ├── evidence/   Evidence drawer + citation rendering
│   └── command/    Command bar, context selector, run plan, action queue
├── hooks/          useResearchRun (REST), useRunWebSocket (live stage progress)
├── lib/            apiClient, shared types (mirrors agent/src/domain), formatting
└── state/          Client state stores (zustand)
tests/
├── unit/           Vitest + React Testing Library
└── e2e/            Playwright
```

## Quick start

```powershell
npm install
copy .env.example .env.local
npm run dev
```

Requires the backend running at `http://localhost:8000` (see `../agent/README.md`).
