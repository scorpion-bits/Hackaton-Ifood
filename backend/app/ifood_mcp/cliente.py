"""Cliente MCP do iFood (consumidor) com rastro de chamadas.

O motor e o checkout do Match só falam com o iFood por aqui. O modo vem de `IFOOD_MCP_MODO`:
- "demo": servidor de demonstração em processo (`demo_server.py`), sem rede nem credencial;
- "real": MCP oficial `https://consumer-mcp.ifood.com.br/marketplace` (Streamable HTTP) com o token do OAuth
  (`oauth.py`): `Authorization: Bearer`, 401 → renova 1 vez e reabre; sem login → `ErroMCP` legível.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from ..config import Config
from . import oauth
from .demo_server import criar_servidor_demo

URL_MCP_REAL = oauth.RECURSO_MCP
MSG_401 = "O iFood recusou o acesso (401) mesmo depois de renovar o login. Conecte o iFood de novo."

# Argumentos que nunca entram no resumo do rastro (localização e dados pessoais).
CHAVES_SENSIVEIS = {
    "latitude", "longitude", "userLocation", "coordinates", "address", "complement", "reference",
    "neighborhood", "email", "phone", "taxPayerIdentificationNumber", "candidateId",
}
TAMANHO_RESUMO = 80
TAMANHO_VALOR = 24


class ErroMCP(Exception):
    """Erro devolvido por uma tool do MCP, com mensagem legível para a pessoa (`codigo`: o code do iFood, se veio)."""

    def __init__(self, mensagem: str = "", codigo: str | None = None):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass
class ChamadaRastro:
    tool: str
    resumo: str
    ms: int
    ok: bool
    erro: str | None = None


def resumir(tool: str, args: dict[str, Any]) -> str:
    """`tool(chave=valor, ...)` curto (≤ 80 caracteres), sem dados sensíveis."""
    partes = []
    for chave, valor in args.items():
        if chave in CHAVES_SENSIVEIS or valor is None:
            continue
        if isinstance(valor, (dict, list)):
            texto = f"[{len(valor)}]" if isinstance(valor, list) else "{…}"
        else:
            texto = str(valor)
            if isinstance(valor, str):
                texto = texto if len(texto) <= TAMANHO_VALOR else texto[: TAMANHO_VALOR - 1] + "…"
                texto = f'"{texto}"'
        candidato = ", ".join([*partes, f"{chave}={texto}"])
        if len(tool) + len(candidato) + 2 > TAMANHO_RESUMO:
            partes.append("…")
            break
        partes.append(f"{chave}={texto}")
    resumo = f"{tool}({', '.join(partes)})"
    return resumo if len(resumo) <= TAMANHO_RESUMO else resumo[: TAMANHO_RESUMO - 2] + "…)"


def _texto_do_resultado(resultado: Any) -> str:
    return "\n".join(getattr(c, "text", "") for c in (resultado.content or [])).strip()


def _mensagem_legivel(texto: str) -> str:
    """Tira o prefixo técnico do SDK ("Error executing tool X: ") e deixa só a mensagem da tool.

    O MCP real às vezes manda o erro como JSON no texto (`{"error": "the value provided for contentMode…"}`):
    nesse caso fica só a mensagem (com o code, se houver).
    """
    limpo = re.sub(r"^Error executing tool \w+:\s*", "", texto).strip()
    if limpo.startswith("{"):
        try:
            dados = json.loads(limpo)
        except json.JSONDecodeError:
            return limpo
        achado = erro_na_resposta(dados)
        if achado:
            return achado[0]
    return limpo


def _texto_util(*valores: Any) -> str | None:
    """1º texto não vazio (ignora "***", que é como as amostras sanitizadas mascaram texto)."""
    for v in valores:
        if isinstance(v, str) and v.strip() and v.strip("* ").strip():
            return v.strip()
    return None


def _com_codigo(texto: str | None, codigos: list[str]) -> str:
    codigos = [c for c in dict.fromkeys(codigos) if c]
    texto = texto or "O iFood recusou a chamada sem mensagem."
    return f"{texto} (código {' / '.join(codigos)})" if codigos else texto


def erro_na_resposta(dados: Any) -> tuple[str, str | None] | None:
    """(mensagem legível, code) se a resposta "normal" (sem isError) for, na verdade, um erro do MCP real.

    Formatos vistos no MCP real (docs/mcp-real/):
    - `{"error": {"code": "MISSING_REQUIRED_FIELDS", "message": "...", "userFriendlyMessage": "..."}}` (createCart);
    - `{"error": "texto"}` (getRecommendations, no texto do isError);
    - `{"success": false, "errors": {"mcpCode": "ADDRESS_CREATION_FAILED", "code": "ADR-2001"}, ...}` (createAddress).
    Resposta válida com `error: null`, `errors: []` ou `success: true` não é erro.
    """
    if not isinstance(dados, dict):
        return None
    erro = dados.get("error")
    if erro and isinstance(erro, dict):
        codigos = [str(erro[k]) for k in ("code", "mcpCode") if erro.get(k)]
        texto = _texto_util(erro.get("userFriendlyMessage"), erro.get("message"), dados.get("message"))
        return _com_codigo(texto, codigos), (codigos[0] if codigos else None)
    if erro and isinstance(erro, str):
        return _com_codigo(erro, []), None
    if dados.get("success") is False:
        erros = dados.get("errors")
        lista = erros if isinstance(erros, list) else [erros] if isinstance(erros, dict) else []
        lista = [e for e in lista if isinstance(e, dict)]
        codigos = [str(e[k]) for e in lista for k in ("mcpCode", "code") if e.get(k)]
        texto = _texto_util(dados.get("userFriendlyMessage"), dados.get("message"),
                            *(e.get("userFriendlyMessage") for e in lista), *(e.get("message") for e in lista),
                            *(e if isinstance(e, str) else None for e in (erros if isinstance(erros, list) else [])))
        return _com_codigo(texto, codigos), (codigos[0] if codigos else None)
    return None


MSG_ENVIO_DESLIGADO = ("Envio real desligado: o pedido para no carrinho (conta de teste). "
                       "Para enviar de verdade, use IFOOD_MCP_PERMITIR_ENVIO=true no .env.")


# nomes que o campo de texto da busca pode ter no schema real, se não for `query`
CAMPOS_TEXTO_BUSCA = ("term", "q", "search", "searchTerm", "text", "keyword", "keywords")


def adaptar_args_com_ajustes(args: dict[str, Any], schema: dict | None) -> tuple[dict[str, Any], list[str]]:
    """Ajusta os argumentos ao input_schema real da tool e diz o que mudou (para o rastro).

    O motor manda `latitude`/`longitude` soltos (como a doc e o servidor de demonstração); o MCP real pede
    `userLocation: {latitude, longitude}` em algumas tools. `query` vira o campo de texto que o schema declarar
    (`term`, `q`, `search`…). Com schema conhecido, descarta argumentos que a tool não declara (ex.: `latitude` no
    `getCart`) e devolve os ajustes ("query→term", "descartados: latitude, longitude"). Sem schema, não mexe.
    """
    props = (schema or {}).get("properties") or {}
    if not props:
        return args, []
    novos = dict(args)
    ajustes: list[str] = []
    lat, lng = novos.get("latitude"), novos.get("longitude")
    usou_coordenadas = False
    if "userLocation" in props and "userLocation" not in novos and lat is not None and lng is not None:
        novos["userLocation"] = {"latitude": float(lat), "longitude": float(lng)}
        usou_coordenadas = True
    if "query" in novos and "query" not in props:
        campo = next((c for c in CAMPOS_TEXTO_BUSCA if c in props and c not in novos), None)
        if campo is not None:
            novos[campo] = novos.pop("query")
            ajustes.append(f"query→{campo}")
    descartados = [k for k in novos if k not in props
                   and not (usou_coordenadas and k in ("latitude", "longitude"))]
    if descartados:
        ajustes.append("descartados: " + ", ".join(descartados))
    return {k: v for k, v in novos.items() if k in props}, ajustes


def adaptar_args(args: dict[str, Any], schema: dict | None) -> dict[str, Any]:
    """Só os argumentos ajustados (ver `adaptar_args_com_ajustes`)."""
    return adaptar_args_com_ajustes(args, schema)[0]


def resumo_com_ajustes(resumo: str, ajustes: list[str]) -> str:
    """`searchOffers(term="pizza") · query→term; descartados: latitude` (a parte dos ajustes vai até 60 chars)."""
    if not ajustes:
        return resumo
    extra = "; ".join(ajustes)
    extra = extra if len(extra) <= 60 else extra[:59] + "…"
    return f"{resumo} · {extra}"


class ClienteIFood:
    """Envolve uma sessão MCP aberta e registra cada chamada em `rastro`."""

    def __init__(self, sessao: Client, modo: str, sinal_http: dict | None = None, permitir_envio: bool = True):
        self._sessao = sessao
        self.modo = modo
        self.rastro: list[ChamadaRastro] = []
        self._sinal_http = sinal_http  # modo real: último status HTTP visto (para explicar um 401)
        self._permitir_envio = permitir_envio  # modo real: `submitOrder` só com IFOOD_MCP_PERMITIR_ENVIO=true
        self._schemas: dict[str, dict] | None = None  # modo real: input_schema por tool (lido 1 vez)

    @property
    def demonstracao(self) -> bool:
        return self.modo == "demo"

    async def chamar(self, tool: str, **args: Any) -> dict:
        """Chama a tool e devolve o `structured_content`. Erro → `ErroMCP` com a mensagem da tool."""
        resumo = resumir(tool, args)
        inicio = time.perf_counter()
        if tool == "submitOrder" and not self._permitir_envio:
            self._registrar(tool, resumo, inicio, ok=False, erro=MSG_ENVIO_DESLIGADO)
            raise ErroMCP(MSG_ENVIO_DESLIGADO)
        if self.modo == "real":
            args, ajustes = adaptar_args_com_ajustes(args, (await self._schemas_reais()).get(tool))
            if ajustes:  # o rastro mostra o que de fato foi enviado e o que ficou de fora
                resumo = resumo_com_ajustes(resumir(tool, args), ajustes)
        try:
            resultado = await self._sessao.call_tool(tool, args)
        except Exception as e:  # falha de transporte/protocolo
            if self._sinal_http and self._sinal_http.get("401"):
                msg = f"Falha ao chamar {tool}: o iFood recusou o login (401). Conecte o iFood de novo."
            else:
                msg = f"Falha ao chamar {tool}: {e}"
            self._registrar(tool, resumo, inicio, ok=False, erro=msg)
            raise ErroMCP(msg) from e

        if resultado.is_error:
            msg = _mensagem_legivel(_texto_do_resultado(resultado)) or f"A tool {tool} devolveu erro sem mensagem."
            self._registrar(tool, resumo, inicio, ok=False, erro=msg)
            raise ErroMCP(msg)

        dados = resultado.structured_content
        if dados is None:  # servidor sem saída estruturada: tenta o texto em JSON
            texto = _texto_do_resultado(resultado)
            try:
                dados = json.loads(texto) if texto else {}
            except json.JSONDecodeError:
                dados = {"texto": texto}
        achado = erro_na_resposta(dados)  # MCP real: erro de negócio vem como resposta normal, sem isError
        if achado:
            self._registrar(tool, resumo, inicio, ok=False, erro=achado[0])
            raise ErroMCP(achado[0], codigo=achado[1])
        self._registrar(tool, resumo, inicio, ok=True)
        return dados

    async def listar_tools(self) -> list[dict]:
        """Todas as tools do servidor (segue a paginação): nome, descrição, input/output schema, anotações."""
        tools: list[dict] = []
        cursor: str | None = None
        for _ in range(50):
            pagina = await self._sessao.list_tools(cursor=cursor)
            for t in pagina.tools:
                tools.append({
                    "name": t.name,
                    "title": t.title,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "output_schema": t.output_schema,
                    "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else None,
                })
            cursor = pagina.next_cursor
            if not cursor:
                break
        return tools

    async def _schemas_reais(self) -> dict[str, dict]:
        """input_schema de cada tool do servidor real (1 `list_tools` por sessão; falha → sem adaptação)."""
        if self._schemas is None:
            try:
                self._schemas = {t["name"]: t.get("input_schema") or {} for t in await self.listar_tools()}
            except Exception:
                self._schemas = {}
        return self._schemas

    def rastro_como_dicts(self) -> list[dict]:
        return [asdict(c) for c in self.rastro]

    def _registrar(self, tool: str, resumo: str, inicio: float, ok: bool, erro: str | None = None) -> None:
        ms = int((time.perf_counter() - inicio) * 1000)
        self.rastro.append(ChamadaRastro(tool=tool, resumo=resumo, ms=ms, ok=ok, erro=erro))


def _desembrulhar(erro: BaseException) -> BaseException:
    while isinstance(erro, BaseExceptionGroup) and len(erro.exceptions) == 1:
        erro = erro.exceptions[0]
    return erro


async def _token_ou_erro(cfg: Config, forcar_renovacao: bool = False) -> str:
    try:
        return await oauth.token_valido(cfg, forcar_renovacao=forcar_renovacao)
    except oauth.ErroOAuth as e:  # mensagens já legíveis e sem segredo
        raise ErroMCP(str(e)) from None


def _http_real(token: str, sinal: dict) -> httpx2.AsyncClient:
    """Cliente HTTP do transporte MCP com o Bearer; um gancho anota se o iFood respondeu 401."""

    async def anotar(resposta: httpx2.Response) -> None:
        sinal["status"] = resposta.status_code
        if resposta.status_code == 401:
            sinal["401"] = True

    return httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(30.0, read=120.0),
        event_hooks={"response": [anotar]},
        transport=_transporte_real,
    )


# Transporte HTTP opcional do modo real (os testes trocam por um falso).
_transporte_real: httpx2.AsyncBaseTransport | None = None


async def _conectar_real(cfg: Config, pilha: AsyncExitStack) -> ClienteIFood:
    """Abre a sessão MCP real; se o iFood responder 401, renova o token 1 vez e tenta de novo."""
    token = await _token_ou_erro(cfg)
    for tentativa in range(2):
        sinal: dict = {}
        tentativa_pilha = AsyncExitStack()
        try:
            http = await tentativa_pilha.enter_async_context(_http_real(token, sinal))
            sessao = await tentativa_pilha.enter_async_context(
                Client(streamable_http_client(URL_MCP_REAL, http_client=http)))
        except Exception as bruto:
            try:
                await tentativa_pilha.aclose()
            except Exception:
                pass
            if sinal.get("401"):
                if tentativa == 0:
                    token = await _token_ou_erro(cfg, forcar_renovacao=True)
                    continue
                raise ErroMCP(MSG_401) from None
            e = _desembrulhar(bruto)
            raise ErroMCP(f"Não consegui conectar ao MCP do iFood ({type(e).__name__}): {e}") from None
        await pilha.enter_async_context(tentativa_pilha)
        return ClienteIFood(sessao, "real", sinal_http=sinal,
                            permitir_envio=getattr(cfg, "ifood_mcp_permitir_envio", False))
    raise ErroMCP(MSG_401)


@asynccontextmanager
async def abrir_cliente(cfg: Config) -> AsyncIterator[ClienteIFood]:
    """Abre o cliente MCP no modo da configuração (`demo` em processo; `real` no MCP oficial com OAuth)."""
    modo = getattr(cfg, "ifood_mcp_modo", "demo") or "demo"
    if modo == "real":
        async with AsyncExitStack() as pilha:
            yield await _conectar_real(cfg, pilha)
        return
    if modo != "demo":
        raise ValueError(f"IFOOD_MCP_MODO inválido: {modo!r}. Use 'demo' ou 'real'.")
    async with Client(criar_servidor_demo()) as sessao:
        yield ClienteIFood(sessao, modo)
