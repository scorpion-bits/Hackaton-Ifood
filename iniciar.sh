#!/usr/bin/env bash
# Sobe tudo no Linux/macOS.
#   ./iniciar.sh          instala o que faltar, compila o frontend e abre http://localhost:8000
#   ./iniciar.sh --dev    backend com reload (8000) + Vite com hot reload (5173)
#   ./iniciar.sh --testes roda os testes do backend e a checagem de tipos do frontend
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ"

command -v python3 >/dev/null || { echo "Falta Python 3.11+"; exit 1; }
command -v npm >/dev/null || { echo "Falta Node.js 20+"; exit 1; }

[ -f .env ] || { cp .env.example .env; echo "Criei .env a partir de .env.example (modo mock)."; }

if [ ! -x backend/.venv/bin/python ]; then
  echo "Criando ambiente Python em backend/.venv ..."
  python3 -m venv backend/.venv
fi
PY="$RAIZ/backend/.venv/bin/python"
"$PY" -m pip install -q -r backend/requirements.txt

[ -d frontend/node_modules ] || (cd frontend && npm install --no-fund --no-audit)

case "${1:-}" in
  --testes)
    (cd backend && "$PY" -m pytest -q)
    (cd frontend && npm run typecheck)
    ;;
  --dev)
    (cd backend && "$PY" -m uvicorn app.main:app --reload --port 8000) &
    trap 'kill 0' EXIT
    (cd frontend && npm run dev)
    ;;
  *)
    (cd frontend && npm run build)
    echo "Abrindo em http://localhost:8000  (Ctrl+C para parar)"
    cd backend && exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    ;;
esac
