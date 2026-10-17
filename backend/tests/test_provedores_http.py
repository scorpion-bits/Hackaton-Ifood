"""Provedores reais e cliente iFood real testados com HTTP simulado (sem chave, sem internet)."""

import json

import httpx
import httpx2

from app import config
from app.agente import laco, provedores
from app.ifood.real import ClienteReal


def _respostas(sequencia, http=httpx):
    """Transporte HTTP que devolve as respostas na ordem e guarda as requisições."""
    pedidas = []

    def handler(request):
        pedidas.append(request)
        return http.Response(200, json=sequencia[len(pedidas) - 1])

    return http.MockTransport(handler), pedidas


async def _rodar_laco(monkeypatch, provedor, classe, sequencia, mensagem, lado):
    # o SDK da Anthropic 1.x usa httpx2; o da OpenAI aceita httpx
    http = httpx2 if classe is provedores.ConversaAnthropic else httpx
    transporte, pedidas = _respostas(sequencia, http)
    monkeypatch.setenv("LLM_PROVIDER", provedor)
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")
    monkeypatch.setenv("LLM_API_KEY", "chave-teste")
    original = provedores.criar_conversa

    def com_transporte(cfg, sistema, historico, msg, ferramentas, contexto):
        return classe(cfg, sistema, historico, msg, ferramentas,
                      http_client=http.AsyncClient(transport=transporte))

    monkeypatch.setattr(laco, "criar_conversa", com_transporte)
    try:
        return await laco.responder(mensagem, lado), pedidas
    finally:
        monkeypatch.setattr(laco, "criar_conversa", original)


async def test_laco_com_provedor_openai_compativel(monkeypatch):
    chamada = {"id": "c1", "type": "function",
               "function": {"name": "comprador_buscar_itens", "arguments": json.dumps({"termo": "sushi"})}}
    seq = [
        {"id": "1", "object": "chat.completion", "created": 0, "model": "m", "choices": [
            {"index": 0, "finish_reason": "tool_calls",
             "message": {"role": "assistant", "content": None, "tool_calls": [chamada]}}]},
        {"id": "2", "object": "chat.completion", "created": 0, "model": "m", "choices": [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "Achei o combinado."}}]},
    ]
    r, pedidas = await _rodar_laco(monkeypatch, "groq", provedores.ConversaOpenAI, seq, "tem sushi?", "comprador")
    assert r["texto"] == "Achei o combinado."
    assert r["passos"][0]["ferramenta"] == "comprador_buscar_itens" and r["passos"][0]["ok"]
    corpo1 = json.loads(pedidas[0].content)
    assert all(not t["function"]["name"].startswith("vendedor_") for t in corpo1["tools"])
    corpo2 = json.loads(pedidas[1].content)
    assert corpo2["messages"][-1]["role"] == "tool" and "Combinado 20" in corpo2["messages"][-1]["content"]


async def test_laco_com_provedor_anthropic(monkeypatch):
    seq = [
        {"id": "m1", "type": "message", "role": "assistant", "model": "modelo-teste", "stop_reason": "tool_use",
         "usage": {"input_tokens": 1, "output_tokens": 1},
         "content": [{"type": "tool_use", "id": "t1", "name": "vendedor_listar_cardapio",
                      "input": {"loja_id": "loja-demo-1"}}]},
        {"id": "m2", "type": "message", "role": "assistant", "model": "modelo-teste", "stop_reason": "end_turn",
         "usage": {"input_tokens": 1, "output_tokens": 1}, "content": [{"type": "text", "text": "Cardápio ok."}]},
    ]
    r, pedidas = await _rodar_laco(monkeypatch, "anthropic", provedores.ConversaAnthropic, seq,
                                   "mostre o cardápio", "vendedor")
    assert r["texto"] == "Cardápio ok."
    corpo2 = json.loads(pedidas[1].content)
    resultado = corpo2["messages"][-1]["content"][0]
    assert resultado["type"] == "tool_result" and resultado["tool_use_id"] == "t1"


def test_cliente_ifood_real_le_token_e_cardapio(monkeypatch):
    monkeypatch.setenv("IFOOD_CLIENT_ID", "id")
    monkeypatch.setenv("IFOOD_CLIENT_SECRET", "segredo")
    rotas = {
        "/authentication/v1.0/oauth/token": {"accessToken": "tok", "expiresIn": 21600},
        "/merchant/v1.0/merchants": [{"id": "m1", "name": "Loja Real"}],
        "/catalog/v2.0/merchants/m1/catalogs": [{"catalogId": "c1"}],
        "/catalog/v2.0/merchants/m1/catalogs/c1/categories": [
            {"name": "Lanches", "items": [{"id": "i1", "name": "X-Burger", "status": "AVAILABLE",
                                            "price": {"value": 25.0}}]}],
    }
    vistos = []

    def handler(req: httpx.Request):
        vistos.append(req)
        return httpx.Response(200, json=rotas[req.url.path])

    cfg = config.carregar()
    cli = ClienteReal(cfg, http=httpx.Client(base_url=cfg.ifood_base_url, transport=httpx.MockTransport(handler)))
    itens = cli.buscar_itens("burger", preco_max=30)
    assert itens[0]["nome"] == "X-Burger" and itens[0]["fonte"] == "iFood"
    assert vistos[0].headers["content-type"] == "application/x-www-form-urlencoded"
    assert b"grantType=client_credentials" in vistos[0].content
    assert vistos[1].headers["authorization"] == "Bearer tok"
