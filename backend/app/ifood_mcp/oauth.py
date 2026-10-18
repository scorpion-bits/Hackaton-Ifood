"""OAuth do MCP do consumidor do iFood: Authorization Code + PKCE (S256) + client secret.

Verificado ao vivo (17/10/2026) em `https://id.ifood.com.br/.well-known/openid-configuration`:
- autorização `https://id.ifood.com.br/authorize`, token `https://id.ifood.com.br/token`,
  revogação `https://id.ifood.com.br/revoke`;
- `authorization_code` + `refresh_token`; `code_challenge_methods_supported: ["S256"]`;
- `client_secret_basic` e `client_secret_post`; sem registro dinâmico (client_id/secret vêm do Portal).
O recurso protegido (`/.well-known/oauth-protected-resource/marketplace`) é
`https://consumer-mcp.ifood.com.br/marketplace`; mandamos `resource=` no authorize e no token (RFC 8707).

Regras: token, refresh, secret e code NUNCA vão para log, exceção ou resposta HTTP. Os tokens ficam em
`backend/.tokens_ifood.json` (no `.gitignore`).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import httpx

from ..config import BACKEND, Config

URL_AUTORIZACAO = "https://id.ifood.com.br/authorize"
URL_TOKEN = "https://id.ifood.com.br/token"
URL_REVOGACAO = "https://id.ifood.com.br/revoke"
RECURSO_MCP = "https://consumer-mcp.ifood.com.br/marketplace"

ARQUIVO_TOKENS = BACKEND / ".tokens_ifood.json"
VALIDADE_ESTADO_S = 10 * 60  # state + code_verifier valem 10 min
MARGEM_RENOVACAO_S = 5 * 60  # renova 5 min antes de expirar
VALIDADE_PADRAO_S = 3600  # se o iFood não mandar expires_in (doc: ~1 h)
MAX_ESTADOS = 50
TIMEOUT_HTTP_S = 20.0

MSG_SEM_CREDENCIAIS = (
    "Preencha IFOOD_MCP_CLIENT_ID e IFOOD_MCP_CLIENT_SECRET no .env (Portal do iFood → seu agente) "
    "e reinicie o app. Já preencheu? Veja se a mesma linha não aparece de novo, vazia, mais abaixo no .env "
    "(vale a última) e se o .env está na pasta raiz do projeto."
)
MSG_SEM_TOKEN = "Conecte o iFood primeiro (botão Conectar iFood)."
MSG_SESSAO_EXPIRADA = "Sua sessão do iFood expirou. Conecte o iFood de novo (botão Conectar iFood)."
MSG_ESTADO_INVALIDO = (
    "Este retorno do login não é válido ou já expirou (passa de 10 min ou foi usado). "
    "Comece de novo pelo botão Conectar iFood."
)

# Transporte HTTP opcional (os testes trocam por httpx.MockTransport).
_transporte: httpx.AsyncBaseTransport | None = None
# Método de autenticação no /token que funcionou por último ("basic" ou "post").
_metodo_auth: str = "basic"
# state → (code_verifier, criado_em, redirect_uri). Só em memória.
_estados: dict[str, tuple[str, float, str]] = {}
# RFC 8707: mandamos `resource=`; se o iFood recusar (`invalid_target`), paramos de mandar (só em memória).
_enviar_resource: bool = True
# Uma trava de renovação por event loop (evita 2 refresh simultâneos com o mesmo refresh_token).
_travas: dict[int, asyncio.Lock] = {}


class ErroOAuth(Exception):
    """Falha no login/renovação, com mensagem legível (nunca contém token, secret ou code)."""


class SemCredenciais(ErroOAuth):
    def __init__(self) -> None:
        super().__init__(MSG_SEM_CREDENCIAIS)


class SemToken(ErroOAuth):
    """Não há login salvo (ou ele não pode mais ser renovado)."""

    def __init__(self, mensagem: str = MSG_SEM_TOKEN) -> None:
        super().__init__(mensagem)


class EstadoInvalido(ErroOAuth):
    def __init__(self) -> None:
        super().__init__(MSG_ESTADO_INVALIDO)


class ErroOAuthToken(ErroOAuth):
    """O /token recusou (guarda o código de erro OAuth para decidir se o login morreu)."""

    def __init__(self, erro: str, descricao: str, status: int) -> None:
        self.erro = erro
        explicacoes = {
            "invalid_client": "client_id/secret recusados. Confira IFOOD_MCP_CLIENT_ID/SECRET no .env.",
            "invalid_grant": "o código/renovação não vale mais (expirou ou já foi usado).",
            "unauthorized_client": "este agente não pode usar esse tipo de login. Confira o cadastro no Portal.",
            "invalid_request": "pedido inválido (confira a Redirect URL cadastrada no Portal).",
            "invalid_target": "o parâmetro resource não foi aceito. Tente conectar de novo.",
            "invalid_scope": "scopes recusados. Deixe IFOOD_MCP_SCOPE vazio no .env.",
        }
        detalhe = explicacoes.get(erro) or descricao or f"HTTP {status}"
        super().__init__(f"O login do iFood recusou: {detalhe}")


@dataclass
class Tokens:
    access_token: str = field(repr=False)
    refresh_token: str | None = field(default=None, repr=False)
    expires_at: float = 0.0
    token_type: str = "Bearer"
    scope: str | None = None
    conta: str | None = None  # só o primeiro nome (para o selo "Conectado como ...")

    def segundos_restantes(self, agora: float | None = None) -> float:
        return self.expires_at - (time.time() if agora is None else agora)


# ---------- credenciais e PKCE ----------
def _credenciais(cfg: Config) -> tuple[str, str]:
    client_id = (cfg.ifood_mcp_client_id or "").strip()
    secret = (cfg.ifood_mcp_client_secret or "").strip()
    if not client_id or not secret:
        raise SemCredenciais()
    return client_id, secret


def configurado(cfg: Config) -> bool:
    try:
        _credenciais(cfg)
    except SemCredenciais:
        return False
    return True


def desafio_pkce(verifier: str) -> str:
    """code_challenge S256 = base64url(sha256(verifier)) sem '='."""
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def _limpar_estados(agora: float) -> None:
    for chave in [k for k, (_, criado, _) in _estados.items() if agora - criado > VALIDADE_ESTADO_S]:
        _estados.pop(chave, None)
    while len(_estados) >= MAX_ESTADOS:  # mais antigo sai primeiro
        _estados.pop(min(_estados, key=lambda k: _estados[k][1]))


def url_login(cfg: Config) -> str:
    """Gera state + code_verifier (guardados em memória por 10 min) e devolve a URL do login oficial."""
    client_id, _ = _credenciais(cfg)
    agora = time.time()
    _limpar_estados(agora)
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)  # 86 caracteres do alfabeto permitido (43–128)
    _estados[state] = (verifier, agora, cfg.ifood_mcp_redirect)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": cfg.ifood_mcp_redirect,
        "code_challenge": desafio_pkce(verifier),
        "code_challenge_method": "S256",
        "state": state,
    }
    if _enviar_resource:
        params["resource"] = RECURSO_MCP
    if cfg.ifood_mcp_scope:
        params["scope"] = cfg.ifood_mcp_scope
    return f"{URL_AUTORIZACAO}?{urlencode(params)}"


def desligar_resource() -> None:
    """Chamado quando o authorize volta com `invalid_target`: o próximo login vai sem `resource`."""
    global _enviar_resource
    _enviar_resource = False


def _consumir_estado(state: str | None) -> tuple[str, str]:
    if not state:
        raise EstadoInvalido()
    guardado = _estados.pop(state, None)
    if guardado is None:
        raise EstadoInvalido()
    verifier, criado, redirect = guardado
    if time.time() - criado > VALIDADE_ESTADO_S:
        raise EstadoInvalido()
    return verifier, redirect


# ---------- armazenamento ----------
def carregar_tokens() -> Tokens | None:
    try:
        dados = json.loads(Path(ARQUIVO_TOKENS).read_text(encoding="utf-8"))
        if not isinstance(dados, dict) or not dados.get("access_token"):
            return None
        campos = Tokens.__dataclass_fields__
        return Tokens(**{k: v for k, v in dados.items() if k in campos})
    except (OSError, ValueError, TypeError):
        return None


def salvar_tokens(tokens: Tokens) -> None:
    caminho = Path(ARQUIVO_TOKENS)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(asdict(tokens), ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(temporario, 0o600)
    except OSError:  # Windows: sem permissões POSIX, segue
        pass
    # Windows: antivírus/editor/outro processo segurando o arquivo → PermissionError; tenta de novo 1 vez.
    for tentativa in range(2):
        try:
            os.replace(temporario, caminho)
            return
        except PermissionError:
            if tentativa == 0:
                time.sleep(0.1)
    try:
        temporario.unlink()
    except OSError:
        pass
    raise ErroOAuth(
        f"Não consegui gravar o login do iFood em {caminho.name}: o arquivo está em uso. "
        f"Feche o arquivo {caminho.name} (editor, antivírus ou outra janela do app) e conecte o iFood de novo.")


def apagar_tokens() -> None:
    try:
        Path(ARQUIVO_TOKENS).unlink()
    except FileNotFoundError:
        pass


def guardar_conta(primeiro_nome: str | None) -> None:
    tokens = carregar_tokens()
    if tokens and primeiro_nome:
        tokens.conta = primeiro_nome
        salvar_tokens(tokens)


# ---------- chamadas ao /token ----------
def _cliente_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=_transporte, timeout=TIMEOUT_HTTP_S)


def _erro_do_corpo(resposta: httpx.Response) -> tuple[str, str]:
    try:
        corpo = resposta.json()
    except ValueError:
        return "", ""
    if not isinstance(corpo, dict):
        return "", ""
    return str(corpo.get("error") or ""), str(corpo.get("error_description") or "")[:200]


async def _post_token(cfg: Config, dados: dict[str, str]) -> dict:
    """Como `_post_token_auth`, mas se o iFood recusar o `resource` (`invalid_target`), repete 1 vez sem ele."""
    global _enviar_resource
    if not _enviar_resource:
        dados = {k: v for k, v in dados.items() if k != "resource"}
    try:
        return await _post_token_auth(cfg, dados)
    except ErroOAuthToken as e:
        if e.erro != "invalid_target" or "resource" not in dados:
            raise
        _enviar_resource = False
        return await _post_token_auth(cfg, {k: v for k, v in dados.items() if k != "resource"})


async def _post_token_auth(cfg: Config, dados: dict[str, str]) -> dict:
    """POST no /token com client_secret_basic; se o iFood disser `invalid_client`, tenta `_post` uma vez."""
    global _metodo_auth
    client_id, secret = _credenciais(cfg)
    ordem = [_metodo_auth] + [m for m in ("basic", "post") if m != _metodo_auth]
    async with _cliente_http() as http:
        for i, metodo in enumerate(ordem):
            corpo = dict(dados)
            auth = None
            if metodo == "basic":
                auth = httpx.BasicAuth(client_id, secret)
            else:
                corpo |= {"client_id": client_id, "client_secret": secret}
            try:
                resposta = await http.post(URL_TOKEN, data=corpo, auth=auth, headers={"Accept": "application/json"})
            except httpx.HTTPError as e:
                raise ErroOAuth(f"Não consegui falar com o login do iFood ({type(e).__name__}). "
                                "Confira a internet e tente de novo.") from None
            if resposta.status_code == 200:
                try:
                    resultado = resposta.json()
                except ValueError:
                    raise ErroOAuth("O login do iFood respondeu algo que não é JSON.") from None
                if not isinstance(resultado, dict) or not resultado.get("access_token"):
                    raise ErroOAuth("O login do iFood não devolveu access_token.")
                _metodo_auth = metodo
                return resultado
            erro, descricao = _erro_do_corpo(resposta)
            if erro == "invalid_client" and i == 0:
                continue  # tenta o outro método de autenticação do cliente uma vez
            raise ErroOAuthToken(erro, descricao, resposta.status_code)
    raise ErroOAuthToken("invalid_client", "", 401)


def _tokens_da_resposta(dados: dict, anterior: Tokens | None = None) -> Tokens:
    try:
        validade = float(dados.get("expires_in") or VALIDADE_PADRAO_S)
    except (TypeError, ValueError):
        validade = VALIDADE_PADRAO_S
    return Tokens(
        access_token=str(dados["access_token"]),
        refresh_token=dados.get("refresh_token") or (anterior.refresh_token if anterior else None),
        expires_at=time.time() + validade,
        token_type=str(dados.get("token_type") or "Bearer"),
        scope=dados.get("scope") or (anterior.scope if anterior else None),
        conta=anterior.conta if anterior else None,
    )


async def trocar_codigo(cfg: Config, code: str, state: str) -> Tokens:
    """Valida o state, troca o code por tokens e salva. EstadoInvalido se o state não confere/expirou."""
    _credenciais(cfg)
    verifier, redirect = _consumir_estado(state)
    if not code:
        raise ErroOAuth("O iFood não devolveu o código de login. Tente de novo.")
    dados = await _post_token(cfg, {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "code_verifier": verifier,
        "resource": RECURSO_MCP,
    })
    tokens = _tokens_da_resposta(dados)
    salvar_tokens(tokens)
    return tokens


def _trava() -> asyncio.Lock:
    laco = id(asyncio.get_running_loop())
    if laco not in _travas:
        _travas.clear()  # laços antigos (testes) não voltam
        _travas[laco] = asyncio.Lock()
    return _travas[laco]


async def renovar(cfg: Config) -> Tokens:
    """Usa o refresh_token. Se o iFood disser que ele morreu, apaga o login salvo e pede para conectar de novo."""
    atual = carregar_tokens()
    if atual is None:
        raise SemToken()
    if not atual.refresh_token:
        raise SemToken(MSG_SESSAO_EXPIRADA)
    try:
        dados = await _post_token(cfg, {
            "grant_type": "refresh_token",
            "refresh_token": atual.refresh_token,
            "resource": RECURSO_MCP,
        })
    except ErroOAuthToken as e:
        if e.erro == "invalid_grant":
            apagar_tokens()
            raise SemToken(MSG_SESSAO_EXPIRADA) from None
        raise
    novos = _tokens_da_resposta(dados, anterior=atual)
    salvar_tokens(novos)
    return novos


async def token_valido(cfg: Config, forcar_renovacao: bool = False) -> str:
    """Access token pronto para uso; renova 5 min antes de expirar (ou já, com `forcar_renovacao`)."""
    tokens = carregar_tokens()
    if tokens is None:
        raise SemToken()
    if not forcar_renovacao and tokens.segundos_restantes() > MARGEM_RENOVACAO_S:
        return tokens.access_token
    async with _trava():
        recarregado = carregar_tokens()  # outra tarefa pode ter renovado enquanto esperávamos
        if recarregado is None:
            raise SemToken()
        if recarregado.access_token != tokens.access_token and recarregado.segundos_restantes() > MARGEM_RENOVACAO_S:
            return recarregado.access_token
        if not recarregado.refresh_token:
            if not forcar_renovacao and recarregado.segundos_restantes() > 0:
                return recarregado.access_token  # sem refresh: usa até expirar
            raise SemToken(MSG_SESSAO_EXPIRADA)
        return (await renovar(cfg)).access_token


async def sair(cfg: Config) -> None:
    """Apaga o login salvo e tenta revogar o refresh_token no iFood (melhor esforço, sem travar)."""
    tokens = carregar_tokens()
    apagar_tokens()
    _estados.clear()
    if not tokens or not configurado(cfg):
        return
    client_id, secret = _credenciais(cfg)
    alvo, dica = (tokens.refresh_token, "refresh_token") if tokens.refresh_token else (tokens.access_token, "access_token")
    try:
        async with _cliente_http() as http:
            await http.post(URL_REVOGACAO, data={"token": alvo, "token_type_hint": dica},
                            auth=httpx.BasicAuth(client_id, secret), timeout=5.0)
    except Exception:  # revogação é cortesia; o arquivo local já foi apagado
        pass


def status(cfg: Config) -> dict:
    """Estado do login para a tela. Nunca inclui token."""
    tokens = carregar_tokens()
    resposta: dict = {
        "modo": getattr(cfg, "ifood_mcp_modo", "demo") or "demo",
        "configurado": configurado(cfg),
        "conectado": False,
    }
    if not resposta["configurado"]:
        resposta["mensagem"] = MSG_SEM_CREDENCIAIS
    if tokens is None:
        return resposta
    restante = tokens.segundos_restantes()
    resposta["conectado"] = restante > 0 or bool(tokens.refresh_token)
    resposta["expira_em"] = datetime.fromtimestamp(tokens.expires_at, tz=timezone.utc).isoformat(timespec="seconds")
    resposta["renovavel"] = bool(tokens.refresh_token)
    if tokens.conta:
        resposta["conta"] = tokens.conta
    return resposta


def primeiro_nome(dados_get_user: object) -> str | None:
    """Primeiro nome a partir da resposta do getUser (formato real ainda não verificado: tenta chaves comuns)."""
    pilha = [dados_get_user]
    while pilha:
        atual = pilha.pop(0)
        if isinstance(atual, dict):
            for chave in ("firstName", "name", "fullName", "displayName"):
                valor = atual.get(chave)
                if isinstance(valor, str) and valor.strip():
                    return valor.strip().split()[0][:30]
            pilha.extend(v for v in atual.values() if isinstance(v, (dict, list)))
        elif isinstance(atual, list):
            pilha.extend(atual)
    return None
