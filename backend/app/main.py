"""API FastAPI. Também serve o frontend compilado (frontend/dist) em http://localhost:8000."""

import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .ifood_mcp import resetar_demo as resetar_demo_mcp
from .match import salas as salas_match
from .rotas_match import router as router_match
from .rotas_oauth import router as router_oauth

FRONT_DIST = config.RAIZ / "frontend" / "dist"


@asynccontextmanager
async def ciclo(_app: FastAPI):
    db.inicializar()
    yield


app = FastAPI(title="Match — Hackathon iFood", lifespan=ciclo)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router_match)
app.include_router(router_oauth)


@app.get("/api/saude")
def saude(request: Request):
    cfg = config.carregar()
    return {
        "ok": True, "llm_provedor": cfg.llm_provedor, "llm_modelo": cfg.llm_modelo,
        "ifood_modo": cfg.ifood_mcp_modo, "demonstracao": cfg.ifood_mcp_modo != "real",
        # `submitOrder` liberado? No demo sempre (pedido simulado); no real só com IFOOD_MCP_PERMITIR_ENVIO=true
        "envio_real_permitido": cfg.ifood_mcp_modo != "real" or bool(cfg.ifood_mcp_permitir_envio),
        "ip_local": ip_local(request.url.port or 8000),
    }


def _ip_da_interface() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # UDP: só escolhe a interface, nada é enviado
            return s.getsockname()[0]
    except OSError:
        return None


def ip_local(porta: int) -> str | None:
    """URL da máquina na rede local (para o celular dos convidados abrir o link). None se não achar."""
    ip = _ip_da_interface()
    if not ip or ip.startswith("127.") or ip == "0.0.0.0":
        return None
    return f"http://{ip}:{porta}"


@app.post("/api/demo/resetar")
def resetar_demo():
    salas_match.limpar()  # salas do Match
    resetar_demo_mcp()  # carrinhos e pedidos do MCP de demonstração
    return {"ok": True}


if FRONT_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONT_DIST, html=True), name="front")
else:
    @app.get("/", response_class=HTMLResponse)
    def sem_front():
        return "<p>Frontend não compilado. Rode o script iniciar ou <code>npm run build</code> em frontend/.</p>"
