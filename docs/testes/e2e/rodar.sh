#!/usr/bin/env bash
# Smoke de interface automático (Linux/container dos agentes): sobe o app em modo demonstração na porta 8000, roda
# docs/testes/e2e/smoke_ui.cjs e derruba o app. Sai com o código do smoke (0 = tudo certo).
# O Playwright é instalado FORA do repositório (em $E2E_DEPS, padrão /tmp/e2e-deps), sem baixar navegador.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../../.." && pwd)"
DEPS="${E2E_DEPS:-/tmp/e2e-deps}"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
if [ ! -d "$DEPS/node_modules/playwright" ]; then
  mkdir -p "$DEPS" && (cd "$DEPS" && npm init -y >/dev/null && npm i --silent playwright@1.48.2 >/dev/null)
fi
[ -f "$RAIZ/frontend/dist/index.html" ] || (cd "$RAIZ/frontend" && npm run build >/dev/null)
cd "$RAIZ/backend"
IFOOD_MCP_MODO=demo LLM_PROVIDER=mock DB_PATH="$(mktemp -d)/e2e.db" \
  .venv/bin/python -m uvicorn app.main:app --port 8000 >/tmp/e2e-uvicorn.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for _ in $(seq 1 40); do curl -sf http://localhost:8000/api/saude >/dev/null && break; sleep 0.5; done
NODE_PATH="$DEPS/node_modules" node "$RAIZ/docs/testes/e2e/smoke_ui.cjs"
