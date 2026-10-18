#!/usr/bin/env bash
# Regera as telas do pitch (pitch/img/app/) com o app em modo demonstração. Linux/container; Playwright fora do repo.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
DEPS="${E2E_DEPS:-/tmp/e2e-deps}"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
if [ ! -d "$DEPS/node_modules/playwright" ]; then
  mkdir -p "$DEPS" && (cd "$DEPS" && npm init -y >/dev/null && npm i --silent playwright@1.48.2 >/dev/null)
fi
(cd "$RAIZ/frontend" && npm run build >/dev/null)
cd "$RAIZ/backend"
IFOOD_MCP_MODO=demo LLM_PROVIDER=mock DB_PATH="$(mktemp -d)/pitch.db" \
  .venv/bin/python -m uvicorn app.main:app --port 8000 >/tmp/pitch-uvicorn.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do curl -sf http://localhost:8000/api/saude >/dev/null && break; sleep 0.5; done
NODE_PATH="$DEPS/node_modules" node "$RAIZ/pitch/scripts/capturar_telas.cjs"
