"""Rotas do login OAuth do iFood (contrato C9).

- `GET /oauth/login` → 302 para o login oficial (`id.ifood.com.br/authorize`).
- `GET /oauth/callback?code&state` → troca o code, salva os tokens e volta para `/#/conectado`
  (erro do iFood ou da troca → `/#/conectado?erro=<mensagem>`; state inválido → 400 com página legível).
- `GET /api/ifood/status` → `{modo, configurado, conectado, expira_em?, renovavel?, conta?, mensagem?}`.
- `POST /api/ifood/sair` → apaga o login salvo.
Nenhuma resposta contém token, refresh, code ou secret.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import replace
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from . import config
from .ifood_mcp import oauth

router = APIRouter()

_RE_CODE = re.compile(r"([?&](?:code|state)=)[^&\s]+")


class _SemCodigoNoLog(logging.Filter):
    """O uvicorn registra o caminho com a query: tira `code`/`state` do /oauth/callback antes de logar."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and any("/oauth/callback" in str(a) for a in record.args):
            record.args = tuple(_RE_CODE.sub(r"\1***", a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.msg, str) and "/oauth/callback" in record.msg:
            record.msg = _RE_CODE.sub(r"\1***", record.msg)
        return True


logging.getLogger("uvicorn.access").addFilter(_SemCodigoNoLog())

DESTINO_OK = "/#/conectado"
TIMEOUT_CONTA_S = 15.0

ERROS_DO_PROVEDOR = {
    "access_denied": "Você cancelou o login no iFood (ou não autorizou o agente).",
    "invalid_request": "O iFood recusou o pedido de login. Confira a Redirect URL cadastrada no Portal.",
    "unauthorized_client": "Este agente ainda não pode fazer login. Confira o cadastro no Portal do iFood.",
    "invalid_scope": "O iFood recusou os scopes pedidos. Ajuste IFOOD_MCP_SCOPE no .env (vazio = não envia).",
    "invalid_target": "O iFood recusou o parâmetro resource. Já ajustei: clique em Conectar iFood de novo.",
    "server_error": "O login do iFood teve um erro interno. Tente de novo em instantes.",
    "temporarily_unavailable": "O login do iFood está indisponível agora. Tente de novo em instantes.",
}


def _voltar_com_erro(mensagem: str) -> RedirectResponse:
    return RedirectResponse(f"{DESTINO_OK}?erro={quote(oauth.sem_segredos(mensagem)[:300])}", status_code=302)


def _falha_inesperada(e: BaseException) -> str:
    """Nada de traceback nem texto cru da exceção (pode ter o code/token): só o tipo e o que fazer."""
    return f"Não consegui concluir o login do iFood ({type(e).__name__}). Clique em Conectar iFood de novo."


def _pagina(titulo: str, mensagem: str, status: int) -> HTMLResponse:
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(titulo)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:32rem;margin:3rem auto;padding:0 16px;color:#3e3e3e}}
h1{{color:#ea1d2c;font-size:1.3rem}}a{{color:#ea1d2c}}</style></head><body>
<h1>{html.escape(titulo)}</h1><p>{html.escape(mensagem)}</p>
<p><a href="/oauth/login">Tentar de novo</a> · <a href="/">Voltar ao app</a></p></body></html>"""
    return HTMLResponse(corpo, status_code=status)


async def _descobrir_conta(cfg: config.Config) -> None:
    """Depois do login, guarda só o primeiro nome do getUser (melhor esforço; falha não atrapalha o login)."""
    from .ifood_mcp.cliente import abrir_cliente  # import tardio: evita ciclo na importação do app

    real = replace(cfg, ifood_mcp_modo="real")

    async def buscar() -> None:
        async with abrir_cliente(real) as cliente:
            oauth.guardar_conta(oauth.primeiro_nome(await cliente.chamar("getUser")))

    try:
        await asyncio.wait_for(buscar(), TIMEOUT_CONTA_S)
    except Exception:  # inclusive ExceptionGroup e timeout: o nome é só enfeite, nunca derruba o callback
        pass


@router.get("/oauth/login")
def login():
    cfg = config.carregar()
    try:
        return RedirectResponse(oauth.url_login(cfg), status_code=302)
    except oauth.ErroOAuth as e:
        return _voltar_com_erro(str(e))
    except Exception as e:
        logging.getLogger(__name__).warning("Falha ao montar o login do iFood: %s", type(e).__name__)
        return _voltar_com_erro(_falha_inesperada(e))


@router.get("/oauth/callback")
async def callback(code: str | None = None, state: str | None = None,
                   error: str | None = None):
    cfg = config.carregar()
    if error:
        if error == "invalid_target":
            oauth.desligar_resource()
        mensagem = ERROS_DO_PROVEDOR.get(error) or f"O iFood não concluiu o login ({error[:60]})."
        return _voltar_com_erro(mensagem)
    try:
        await oauth.trocar_codigo(cfg, code or "", state or "")
    except oauth.EstadoInvalido as e:
        return _pagina("Login do iFood não confirmado", str(e), 400)
    except oauth.ErroOAuth as e:
        return _voltar_com_erro(str(e))
    except Exception as e:  # erro inesperado na troca: mensagem legível, sem traceback para a pessoa
        logging.getLogger(__name__).warning("Falha inesperada no callback do iFood: %s", type(e).__name__)
        return _voltar_com_erro(_falha_inesperada(e))
    await _descobrir_conta(cfg)
    return RedirectResponse(DESTINO_OK, status_code=302)


@router.get("/api/ifood/status")
def status_ifood():
    return oauth.status(config.carregar())


@router.post("/api/ifood/sair")
async def sair_ifood():
    cfg = config.carregar()
    try:
        await oauth.sair(cfg)
    except oauth.ErroOAuth as e:  # ex.: arquivo de login preso no Windows
        return JSONResponse({"detail": str(e)}, status_code=409)
    return oauth.status(cfg)
