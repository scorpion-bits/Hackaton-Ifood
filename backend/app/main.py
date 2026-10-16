"""API FastAPI. Também serve o frontend compilado (frontend/dist) em http://localhost:8000."""

import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import acoes, config, db
from .agente import responder
from .ifood import ErroIFood, obter_cliente

FRONT_DIST = config.RAIZ / "frontend" / "dist"


@asynccontextmanager
async def ciclo(_app: FastAPI):
    db.inicializar()
    yield


app = FastAPI(title="Comércio com Agentes — Hackathon iFood", lifespan=ciclo)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


class PedidoChat(BaseModel):
    mensagem: str
    lado: Literal["vendedor", "comprador"] = "comprador"
    conversa_id: str | None = None


@app.get("/api/saude")
def saude():
    cfg = config.carregar()
    return {
        "ok": True, "llm_provedor": cfg.llm_provedor, "llm_modelo": cfg.llm_modelo,
        "ifood_modo": cfg.ifood_modo, "demonstracao": cfg.ifood_modo != "real",
    }


@app.post("/api/chat")
async def chat(pedido: PedidoChat):
    conversa_id = pedido.conversa_id or uuid.uuid4().hex[:12]
    with db.conectar() as con:
        historico = [dict(r) for r in con.execute(
            "SELECT papel, texto FROM mensagens WHERE conversa_id = ? ORDER BY id", (conversa_id,)
        ).fetchall()]
    try:
        resposta = await responder(pedido.mensagem, pedido.lado, historico[-20:])
    except Exception as e:  # erro de provedor (chave, modelo, rede) vira mensagem legível
        raise HTTPException(502, f"Falha no agente ({type(e).__name__}): {e}") from e
    with db.conectar() as con:
        con.execute("INSERT INTO mensagens (conversa_id, papel, texto, criado_em) VALUES (?, 'usuario', ?, ?)",
                    (conversa_id, pedido.mensagem, db.agora()))
        con.execute("INSERT INTO mensagens (conversa_id, papel, texto, criado_em) VALUES (?, 'agente', ?, ?)",
                    (conversa_id, resposta["texto"], db.agora()))
    return resposta | {"conversa_id": conversa_id}


@app.get("/api/acoes")
def listar_acoes(status: str | None = None):
    return acoes.listar(status)


@app.post("/api/acoes/{acao_id}/confirmar")
def confirmar_acao(acao_id: str):
    try:
        return acoes.confirmar(acao_id)
    except ErroIFood as e:
        raise HTTPException(409, str(e)) from e


@app.post("/api/acoes/{acao_id}/recusar")
def recusar_acao(acao_id: str):
    try:
        return acoes.recusar(acao_id)
    except ErroIFood as e:
        raise HTTPException(409, str(e)) from e


@app.get("/api/lojas")
def lojas():
    try:
        return obter_cliente().listar_lojas()
    except ErroIFood as e:
        raise HTTPException(502, str(e)) from e


@app.post("/api/demo/resetar")
def resetar_demo():
    db.resetar_demo()
    return {"ok": True}


if FRONT_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONT_DIST, html=True), name="front")
else:
    @app.get("/", response_class=HTMLResponse)
    def sem_front():
        return "<p>Frontend não compilado. Rode o script iniciar ou <code>npm run build</code> em frontend/.</p>"
