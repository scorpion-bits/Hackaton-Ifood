"""Uma chamada de LLM que devolve JSON (intérprete e juiz do Match).

Usa o provedor do `.env` (mesmas variáveis de `agente/provedores.py`): OpenAI-compatível (groq, gemini, ollama,
openai) ou anthropic. `LLM_PROVIDER=mock`, falta de modelo, erro, timeout (8 s) ou resposta sem JSON → `None`;
quem chama tem fallback determinístico. Nunca lança exceção para o motor.

Reserva de modelos (bug 15): o Groq grátis limita tokens/min POR MODELO. `LLM_MODELOS_RESERVA` lista modelos a
tentar, em ordem, quando o principal dá 429 (ou erro de modelo). O modelo que deu 429 fica "de molho" por até 60 s
(ou o `retry-after` do provedor, se menor), em memória do processo, e não é tentado de novo nesse prazo. Nunca
espera/retenta com pausa: o tempo total da chamada continua limitado pelo timeout.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import Counter
from typing import Any

from ..config import Config

TIMEOUT_S = 8.0
MAX_TOKENS = 1500  # teto padrão; cada chamada do Match passa o seu (bem menor) para não gastar o TPM à toa
MOLHO_S = 60.0  # quanto tempo um modelo que deu 429 fica sem ser tentado
_STATUS_TROCA_MODELO = {404, 503, 529}  # modelo inexistente/aposentado/sobrecarregado: tenta o próximo
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


# modelo -> instante (time.monotonic) até o qual não vale tentar; estado do processo
_de_molho: dict[str, float] = {}
estatisticas: dict[str, Any] = {"429": 0, "chamadas": 0, "atendidas": Counter()}


def resetar_estado() -> None:
    """Zera molho e estatísticas (testes e `testar_ia`)."""
    _de_molho.clear()
    estatisticas.update({"429": 0, "chamadas": 0, "atendidas": Counter()})


def modelos_da_cfg(cfg: Config) -> list[str]:
    """Principal + reserva, sem repetição, na ordem."""
    lista = [cfg.llm_modelo, *getattr(cfg, "llm_modelos_reserva", ())]
    return list(dict.fromkeys(m for m in lista if m))


def _disponiveis(modelos: list[str]) -> list[str]:
    agora = time.monotonic()
    return [m for m in modelos if _de_molho.get(m, 0.0) <= agora]


def _status(e: Exception) -> int | None:
    status = getattr(e, "status_code", None)
    return status if isinstance(status, int) else None


def _retry_after(e: Exception) -> float | None:
    cab = getattr(getattr(e, "response", None), "headers", None)
    try:
        return float(cab.get("retry-after")) if cab is not None and cab.get("retry-after") else None
    except (TypeError, ValueError):
        return None


def _trocar_de_modelo(e: Exception) -> bool:
    """O erro é do modelo (limite, inexistente, sobrecarga): vale tentar a reserva. Timeout/rede/chave, não."""
    status = _status(e)
    if status == 429 or status in _STATUS_TROCA_MODELO:
        return True
    return status == 400 and "model" in str(e).lower()


async def completar_json(cfg: Config, sistema: str, usuario: str, timeout: float | None = None,
                         max_tokens: int | None = None) -> dict | None:
    """Pede ao LLM um objeto JSON. Qualquer falha → `None` (o chamador usa o fallback).

    `timeout` (s) troca o limite padrão de 8 s (o leilão usa ~6 s por agente de loja), valendo para o total das
    tentativas. `max_tokens` limita a resposta (no Groq o pedido conta no limite por minuto)."""
    if cfg.llm_provedor == "mock" or not cfg.llm_modelo:
        return None
    limite = timeout if timeout and timeout > 0 else TIMEOUT_S
    teto = max_tokens if max_tokens and max_tokens > 0 else MAX_TOKENS
    sistema = sistema + "\nResponda somente com um objeto JSON válido, sem texto antes ou depois."
    fim = time.monotonic() + limite
    for modelo in _disponiveis(modelos_da_cfg(cfg)):
        restante = fim - time.monotonic()
        if restante <= 0.2:
            break
        estatisticas["chamadas"] += 1
        try:
            if cfg.llm_provedor == "anthropic":
                texto = await asyncio.wait_for(_anthropic(cfg, sistema, usuario, restante, modelo, teto), restante)
            else:
                texto = await asyncio.wait_for(_openai(cfg, sistema, usuario, restante, modelo, teto), restante)
        except Exception as e:  # timeout, rede, chave, modelo… o motor segue com o fallback
            log.warning("LLM (%s/%s) falhou: %s", cfg.llm_provedor, modelo, e)
            if _status(e) == 429:
                estatisticas["429"] += 1
            if _trocar_de_modelo(e):
                espera = _retry_after(e)
                _de_molho[modelo] = time.monotonic() + (min(espera, MOLHO_S) if espera else MOLHO_S)
                continue
            return None
        dados = extrair_json(texto)
        if dados is not None:
            estatisticas["atendidas"][modelo] += 1
        return dados
    return None


async def _openai(cfg: Config, sistema: str, usuario: str, limite: float = TIMEOUT_S,
                  modelo: str | None = None, max_tokens: int = MAX_TOKENS) -> str | None:
    from openai import AsyncOpenAI, BadRequestError

    modelo = modelo or cfg.llm_modelo
    cliente = AsyncOpenAI(api_key=cfg.llm_chave or "sem-chave", base_url=cfg.llm_base_url,
                          http_client=_cliente_http(cfg.llm_provedor), timeout=limite, max_retries=0)
    mensagens = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
    extras: dict[str, Any] = {}
    if "gpt-oss" in modelo:  # modelo de raciocínio: esforço baixo gasta bem menos tokens (e cabe no TPM)
        esforco = cfg.llm_esforco if cfg.llm_esforco in ("low", "medium", "high") else "low"
        extras["extra_body"] = {"reasoning_effort": esforco}
    try:
        resp = await cliente.chat.completions.create(
            model=modelo, messages=mensagens, temperature=0.2, max_tokens=max_tokens,
            response_format={"type": "json_object"}, **extras,
        )
    except BadRequestError:
        # provedor/modelo sem response_format: a instrução no prompt + extração do JSON bastam
        resp = await cliente.chat.completions.create(
            model=modelo, messages=mensagens, temperature=0.2, max_tokens=max_tokens, **extras,
        )
    return resp.choices[0].message.content


async def _anthropic(cfg: Config, sistema: str, usuario: str, limite: float = TIMEOUT_S,
                     modelo: str | None = None, max_tokens: int = MAX_TOKENS) -> str | None:
    import anthropic

    cliente = anthropic.AsyncAnthropic(api_key=cfg.llm_chave or None, http_client=_cliente_http("anthropic"),
                                       timeout=limite, max_retries=0)
    resp = await cliente.messages.create(
        model=modelo or cfg.llm_modelo, max_tokens=max_tokens, system=sistema,
        messages=[{"role": "user", "content": usuario}],
    )
    return "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
