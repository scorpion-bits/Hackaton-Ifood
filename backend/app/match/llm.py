"""Uma chamada de LLM que devolve JSON (intérprete e juiz do Match).

Usa o provedor do `.env` (mesmas variáveis de `agente/provedores.py`): OpenAI-compatível (groq, gemini, ollama,
openai) ou anthropic. `LLM_PROVIDER=mock`, falta de modelo, erro, timeout (8 s) ou resposta sem JSON → `None`;
quem chama tem fallback determinístico. Nunca lança exceção para o motor.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from ..config import Config

TIMEOUT_S = 8.0
MAX_TOKENS = 1500
log = logging.getLogger(__name__)


def _cliente_http(provedor: str) -> Any | None:
    """Cliente HTTP a injetar no SDK (os testes trocam por um transporte falso). `None` = padrão do SDK."""
    return None


def extrair_json(texto: str | None) -> dict | None:
    """Primeiro objeto JSON (dict) dentro do texto, aceitando cercas ```json e texto em volta."""
    if not texto:
        return None
    texto = re.sub(r"```(?:json)?", "", texto)
    decodificador = json.JSONDecoder()
    for m in re.finditer(r"\{", texto):
        try:
            obj, _ = decodificador.raw_decode(texto, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


async def completar_json(cfg: Config, sistema: str, usuario: str, timeout: float | None = None) -> dict | None:
    """Pede ao LLM um objeto JSON. Qualquer falha → `None` (o chamador usa o fallback).

    `timeout` (s) troca o limite padrão de 8 s (o leilão usa ~6 s por agente de loja)."""
    if cfg.llm_provedor == "mock" or not cfg.llm_modelo:
        return None
    limite = timeout if timeout and timeout > 0 else TIMEOUT_S
    sistema = sistema + "\nResponda somente com um objeto JSON válido, sem texto antes ou depois."
    try:
        if cfg.llm_provedor == "anthropic":
            texto = await asyncio.wait_for(_anthropic(cfg, sistema, usuario, limite), limite)
        else:
            texto = await asyncio.wait_for(_openai(cfg, sistema, usuario, limite), limite)
    except Exception as e:  # timeout, rede, chave, modelo… o motor segue com o fallback
        log.warning("LLM (%s) falhou: %s", cfg.llm_provedor, e)
        return None
    return extrair_json(texto)


async def _openai(cfg: Config, sistema: str, usuario: str, limite: float = TIMEOUT_S) -> str | None:
    from openai import AsyncOpenAI, BadRequestError

    cliente = AsyncOpenAI(api_key=cfg.llm_chave or "sem-chave", base_url=cfg.llm_base_url,
                          http_client=_cliente_http(cfg.llm_provedor), timeout=limite, max_retries=0)
    mensagens = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
    try:
        resp = await cliente.chat.completions.create(
            model=cfg.llm_modelo, messages=mensagens, temperature=0.2, max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
        )
    except BadRequestError:
        # provedor/modelo sem response_format: a instrução no prompt + extração do JSON bastam
        resp = await cliente.chat.completions.create(
            model=cfg.llm_modelo, messages=mensagens, temperature=0.2, max_tokens=MAX_TOKENS,
        )
    return resp.choices[0].message.content


async def _anthropic(cfg: Config, sistema: str, usuario: str, limite: float = TIMEOUT_S) -> str | None:
    import anthropic

    cliente = anthropic.AsyncAnthropic(api_key=cfg.llm_chave or None, http_client=_cliente_http("anthropic"),
                                       timeout=limite, max_retries=0)
    resp = await cliente.messages.create(
        model=cfg.llm_modelo, max_tokens=MAX_TOKENS, system=sistema,
        messages=[{"role": "user", "content": usuario}],
    )
    return "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
