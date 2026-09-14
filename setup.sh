#!/usr/bin/env bash
# IROS — one-command local environment setup (macOS / Linux).
#
# Safe to re-run any time: every step is idempotent and NEVER overwrites a
# .env file you've already customized. What it does:
#   1. Checks for the required tools (python3.12, node, ollama) and tells you
#      exactly what to install if one is missing — never installs system
#      packages on your behalf.
#   2. Creates agent/.venv (if missing) and installs the backend in it.
#   3. Creates agent/.env / frontend/.env.local from the .example files (only
#      if they don't already exist) and switches the backend on to real local
#      Ollama + real live market data by default, instead of the deterministic
#      mock/fixture-only defaults .env.example ships with.
#   4. Pulls the two local Ollama models IROS uses (no-ops if already pulled).
#   5. Runs `npm install` for the frontend.
#
# Usage:  ./setup.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }
step() { echo -e "\n${BOLD}── $1 ──${NC}"; }

step "1/5 — Checking prerequisites"

PYTHON_BIN=""
for candidate in python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    version="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [ "$version" = "3.12" ]; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  err "Python 3.12 not found. Install it first (e.g. 'brew install python@3.12' on macOS), then re-run this script."
  exit 1
fi
ok "Python 3.12 found ($PYTHON_BIN)"

if ! command -v node >/dev/null 2>&1; then
  err "Node.js not found. Install Node 18+ first (e.g. 'brew install node' or https://nodejs.org), then re-run this script."
  exit 1
fi
ok "Node.js found ($(node --version))"

OLLAMA_AVAILABLE=false
if command -v ollama >/dev/null 2>&1; then
  OLLAMA_AVAILABLE=true
  ok "Ollama found"
else
  warn "Ollama not found (https://ollama.com). You can still run everything with the deterministic mock LLM" \
       "(CLOUD_MODEL_PROVIDER left blank), but AI narratives/notebook answers won't be real LLM output until you install it and re-run this script."
fi

step "2/5 — Backend: Python virtual environment + dependencies"
if [ -d "agent/.venv" ]; then
  ok "agent/.venv already exists — skipping creation"
else
  "$PYTHON_BIN" -m venv agent/.venv
  ok "Created agent/.venv"
fi
agent/.venv/bin/pip install --quiet --upgrade pip
agent/.venv/bin/pip install --quiet -e "./agent[dev]"
ok "Backend package installed (editable, with dev/test extras)"

step "3/5 — Backend: .env"
if [ -f "agent/.env" ]; then
  ok "agent/.env already exists — leaving it untouched"
else
  cp agent/.env.example agent/.env
  # Switch on real local Ollama + real live market data by default, instead of
  # .env.example's deterministic-mock/fixture-only defaults — this is the one
  # opinionated change setup.sh makes, so a fresh clone gets the full real
  # experience out of the box. Re-run with these left blank/false any time by
  # hand-editing agent/.env if you'd rather start in offline/mock mode.
  #
  # NOTE: agent/.env.example ships with CRLF line endings, so each line ends
  # in \r before the \n — matching bare "...=$" would silently never fire.
  # ".*" instead of a "$" anchor absorbs that trailing \r (and anything else)
  # regardless of the file's line-ending convention.
  sed -i.bak 's/^CLOUD_MODEL_PROVIDER=.*/CLOUD_MODEL_PROVIDER=ollama/' agent/.env
  sed -i.bak 's/^USE_REAL_DATA_SOURCES=false.*/USE_REAL_DATA_SOURCES=true/' agent/.env
  rm -f agent/.env.bak
  ok "Created agent/.env (real Ollama + real market data enabled by default)"
fi

step "4/5 — Ollama models"
if [ "$OLLAMA_AVAILABLE" = true ]; then
  echo "Pulling llama3.1 (chat) — a no-op if you already have it..."
  ollama pull llama3.1
  echo "Pulling nomic-embed-text (embeddings) — a no-op if you already have it..."
  ollama pull nomic-embed-text
  ok "Ollama models ready"
else
  warn "Skipped (Ollama not installed) — install it and re-run: ollama pull llama3.1 && ollama pull nomic-embed-text"
fi

step "5/5 — Frontend: npm install + .env.local"
(cd frontend && npm install --silent)
ok "Frontend dependencies installed"
if [ -f "frontend/.env.local" ]; then
  ok "frontend/.env.local already exists — leaving it untouched"
else
  cp frontend/.env.example frontend/.env.local
  ok "Created frontend/.env.local"
fi

echo -e "\n${BOLD}${GREEN}Setup complete!${NC}\n"
echo "Start the backend  (terminal 1): cd agent && .venv/bin/python main.py"
echo "Start the frontend (terminal 2): cd frontend && npm run dev"
echo -e "Then open ${BOLD}http://localhost:3000${NC} and type ${BOLD}ACME${NC} (offline demo) or a real ticker like ${BOLD}AAPL${NC} into the command bar.\n"
