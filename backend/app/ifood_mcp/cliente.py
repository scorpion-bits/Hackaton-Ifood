"""Cliente MCP do iFood (consumidor) com rastro de chamadas.

O motor e o checkout do Match só falam com o iFood por aqui. O modo vem de `IFOOD_MCP_MODO`:
- "demo": servidor de demonstração em processo (`demo_server.py`), sem rede nem credencial;
- "real": MCP remoto com OAuth — fica para a etapa 03.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

from mcp import Client

from ..config import Config
from .demo_server import criar_servidor_demo

# Argumentos que nunca entram no resumo do rastro (localização e dados pessoais).
CHAVES_SENSIVEIS = {
    "latitude", "longitude", "userLocation", "coordinates", "address", "complement", "reference",
    "neighborhood", "email", "phone", "taxPayerIdentificationNumber", "candidateId",
}
TAMANHO_RESUMO = 80
TAMANHO_VALOR = 24


class ErroMCP(Exception):
    """Erro devolvido por uma tool do MCP, com mensagem legível para a pessoa."""


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
    """Tira o prefixo técnico do SDK ("Error executing tool X: ") e deixa só a mensagem da tool."""
    return re.sub(r"^Error executing tool \w+:\s*", "", texto).strip()


class ClienteIFood:
    """Envolve uma sessão MCP aberta e registra cada chamada em `rastro`."""

    def __init__(self, sessao: Client, modo: str):
        self._sessao = sessao
        self.modo = modo
        self.rastro: list[ChamadaRastro] = []

    @property
    def demonstracao(self) -> bool:
        return self.modo == "demo"

    async def chamar(self, tool: str, **args: Any) -> dict:
        """Chama a tool e devolve o `structured_content`. Erro → `ErroMCP` com a mensagem da tool."""
        resumo = resumir(tool, args)
        inicio = time.perf_counter()
        try:
            resultado = await self._sessao.call_tool(tool, args)
        except Exception as e:  # falha de transporte/protocolo
            self._registrar(tool, resumo, inicio, ok=False, erro=f"Falha ao chamar {tool}: {e}")
            raise ErroMCP(f"Falha ao chamar {tool}: {e}") from e

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
        self._registrar(tool, resumo, inicio, ok=True)
        return dados

    def rastro_como_dicts(self) -> list[dict]:
        return [asdict(c) for c in self.rastro]

    def _registrar(self, tool: str, resumo: str, inicio: float, ok: bool, erro: str | None = None) -> None:
        ms = int((time.perf_counter() - inicio) * 1000)
        self.rastro.append(ChamadaRastro(tool=tool, resumo=resumo, ms=ms, ok=ok, erro=erro))


@asynccontextmanager
async def abrir_cliente(cfg: Config) -> AsyncIterator[ClienteIFood]:
    """Abre o cliente MCP no modo da configuração (`demo` em processo; `real` na etapa 03)."""
    modo = getattr(cfg, "ifood_mcp_modo", "demo") or "demo"
    if modo == "real":
        raise NotImplementedError("etapa 03")
    if modo != "demo":
        raise ValueError(f"IFOOD_MCP_MODO inválido: {modo!r}. Use 'demo' ou 'real'.")
    async with Client(criar_servidor_demo()) as sessao:
        yield ClienteIFood(sessao, modo)
