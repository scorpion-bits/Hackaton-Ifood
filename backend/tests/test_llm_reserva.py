"""Bug 15 (A3): modelo de reserva no 429, "molho" do modelo limitado e uma chamada de intérprete por grupo."""

import asyncio
import json
import time

import httpx
import pytest

from app.config import carregar
from app.match import interprete, llm
from app.match.modelos import Desejo


@pytest.fixture(autouse=True)
def estado_limpo():
    llm.resetar_estado()
    yield
    llm.resetar_estado()


def _resposta_ok(conteudo: dict) -> httpx.Response:
    return httpx.Response(200, json={"id": "x", "object": "chat.completion", "created": 0, "model": "m", "choices": [
        {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(conteudo)}}]})


def _usar(monkeypatch, handler, reserva="openai/gpt-oss-20b,qwen/qwen3.8-27b", principal="openai/gpt-oss-120b"):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", principal)
    monkeypatch.setenv("LLM_API_KEY", "chave-teste")
    monkeypatch.setenv("LLM_MODELOS_RESERVA", reserva)
    monkeypatch.setattr(llm, "_cliente_http", lambda _p: httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _handler(modelos_com_erro: dict[str, int], pedidas: list[dict]):
    def handler(request):
        corpo = json.loads(request.content)
        pedidas.append(corpo)
        status = modelos_com_erro.get(corpo["model"])
        if status:
            return httpx.Response(status, json={"error": {"message": "limite", "type": "x"}})
        return _resposta_ok({"ok": True, "modelo": corpo["model"]})
    return handler


def test_config_le_modelos_de_reserva(monkeypatch):
    monkeypatch.setenv("LLM_MODELOS_RESERVA", " openai/gpt-oss-20b , qwen/qwen3.8-27b ,, ")
    assert carregar().llm_modelos_reserva == ("openai/gpt-oss-20b", "qwen/qwen3.8-27b")
    monkeypatch.setenv("LLM_MODELOS_RESERVA", "")
    assert carregar().llm_modelos_reserva == ()


async def test_429_no_principal_usa_a_reserva_e_lembra_do_molho(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 429}, pedidas))
    cfg = carregar()
    assert await llm.completar_json(cfg, "s", "u") == {"ok": True, "modelo": "openai/gpt-oss-20b"}
    assert [p["model"] for p in pedidas] == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    # 2ª chamada: o principal está de molho (~60 s) e nem é tentado
    assert await llm.completar_json(cfg, "s", "u") == {"ok": True, "modelo": "openai/gpt-oss-20b"}
    assert [p["model"] for p in pedidas][2:] == ["openai/gpt-oss-20b"]
    assert llm.estatisticas["429"] == 1
    assert llm.estatisticas["atendidas"]["openai/gpt-oss-20b"] == 2


async def test_molho_expira_e_o_principal_volta(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 429}, pedidas))
    cfg = carregar()
    await llm.completar_json(cfg, "s", "u")
    llm._de_molho["openai/gpt-oss-120b"] = time.monotonic() - 1  # passou o minuto
    pedidas.clear()
    await llm.completar_json(cfg, "s", "u")
    assert pedidas[0]["model"] == "openai/gpt-oss-120b"


async def test_cai_para_a_terceira_e_depois_para_fallback_sem_esperar(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 429, "openai/gpt-oss-20b": 429}, pedidas))
    cfg = carregar()
    assert (await llm.completar_json(cfg, "s", "u"))["modelo"] == "qwen/qwen3.8-27b"
    assert llm.estatisticas["429"] == 2

    pedidas.clear()
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 429, "openai/gpt-oss-20b": 429, "qwen/qwen3.8-27b": 429},
                                pedidas))
    llm.resetar_estado()
    inicio = time.monotonic()
    assert await llm.completar_json(carregar(), "s", "u") is None  # todos limitados: fallback do chamador
    assert time.monotonic() - inicio < 2 and len(pedidas) == 3
    pedidas.clear()
    assert await llm.completar_json(carregar(), "s", "u") is None
    assert pedidas == []  # todos de molho: nem faz requisição


async def test_modelo_inexistente_tambem_tenta_a_reserva(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 404}, pedidas))
    assert (await llm.completar_json(carregar(), "s", "u"))["modelo"] == "openai/gpt-oss-20b"
    assert llm.estatisticas["429"] == 0


async def test_erro_de_servidor_nao_troca_de_modelo(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 500}, pedidas))
    assert await llm.completar_json(carregar(), "s", "u") is None
    assert len(pedidas) == 1


async def test_sem_reserva_o_429_vira_fallback(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({"openai/gpt-oss-120b": 429}, pedidas), reserva="")
    assert await llm.completar_json(carregar(), "s", "u") is None
    assert llm.estatisticas["429"] == 1 and len(pedidas) == 1


async def test_max_tokens_e_esforco_do_gpt_oss_vao_no_pedido(monkeypatch):
    pedidas: list[dict] = []
    _usar(monkeypatch, _handler({}, pedidas), reserva="")
    await llm.completar_json(carregar(), "s", "u", max_tokens=321)
    assert pedidas[0]["max_tokens"] == 321 and pedidas[0]["reasoning_effort"] == "low"


async def test_grupo_e_interpretado_em_uma_unica_chamada(monkeypatch):
    pedidas: list[dict] = []

    def handler(request):
        corpo = json.loads(request.content)
        pedidas.append(corpo)
        entrada = json.loads(corpo["messages"][1]["content"])
        return _resposta_ok({"pessoas": [
            {"id": "a", "itens": [{"consultas": ["sushi"], "verticais": ["RESTAURANT"], "vontades": ["sushi"]}],
             "restricoes": [], "orcamento_max": 40, "perfil": "equilibrado"},
            {"id": "b", "itens": [{"consultas": ["pizza"], "verticais": ["RESTAURANT"], "vontades": ["pizza"]}],
             "restricoes": [], "orcamento_max": None, "perfil": "barato"},
            # "c" não veio na resposta: usa o fallback só dessa pessoa
        ]}) if len(entrada["pessoas"]) == 3 else _resposta_ok({})

    _usar(monkeypatch, handler, reserva="")
    cfg = carregar()
    desejos = [Desejo("a", "Ana", "sushi, até 40"), Desejo("b", "Beto", "uma pizza barata"),
               Desejo("c", "Cris", "açaí")]
    ia, ib, ic = await asyncio.gather(*(interprete.interpretar(cfg, d) for d in desejos))
    assert len(pedidas) == 1  # 1 chamada para as 3 pessoas
    assert ia[0].consultas == ["sushi"] and ia[0].orcamento_max == 40
    assert ib[0].consultas == ["pizza"] and ib[0].perfil == "barato"
    assert ic == interprete.interpretar_fallback(desejos[2])
    assert pedidas[0]["max_tokens"] <= 1400


async def test_item_fantasma_do_llm_e_descartado(monkeypatch):
    """Bug 12 no caminho do LLM: o modelo devolve 'mas'/'chega' como 2º item; só a pizza fica."""
    pedidas: list[dict] = []

    def handler(request):
        pedidas.append(1)
        return _resposta_ok({"itens": [
            {"consultas": ["pizza"], "verticais": ["RESTAURANT"], "vontades": ["pizza"]},
            {"consultas": ["nada", "mas"], "verticais": ["RESTAURANT"], "vontades": ["vegetariano"]}],
            "restricoes": ["vegetariano"], "orcamento_max": None, "perfil": "equilibrado"})

    _usar(monkeypatch, handler, reserva="")
    desejo = Desejo("p", "P", "pizza pra dividir, mas eu não como carne")
    intencoes = await interprete.interpretar(carregar(), desejo)
    assert [i.consultas for i in intencoes] == [["pizza"]]
    assert intencoes[0].restricoes == ["vegetariano"]
