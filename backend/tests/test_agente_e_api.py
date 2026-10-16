from fastapi.testclient import TestClient

from app.agente import responder
from app.main import app


async def test_agente_mock_comprador_propoe_pedido():
    r = await responder("quero pedir um burger até R$ 40", "comprador")
    assert [p["ferramenta"] for p in r["passos"]] == ["comprador_buscar_itens", "comprador_propor_pedido"]
    assert r["acoes"][0]["tipo"] == "criar_pedido"
    assert "Burger clássico" in r["acoes"][0]["resumo"]
    assert "confirme" in r["texto"].lower()


async def test_agente_mock_vendedor_propoe_promocao():
    r = await responder("crie uma promoção de 15%", "vendedor")
    assert r["acoes"][0]["tipo"] == "criar_promocao"
    assert "15%" in r["acoes"][0]["resumo"]


async def test_agente_nao_ve_ferramentas_do_outro_lado():
    r = await responder("mostre o cardápio", "comprador")
    assert all(not p["ferramenta"].startswith("vendedor_") for p in r["passos"])


def test_api_fluxo_completo_com_confirmacao_e_reset():
    with TestClient(app) as c:
        assert c.get("/api/saude").json()["demonstracao"] is True
        r = c.post("/api/chat", json={"mensagem": "quero pedir uma pizza", "lado": "comprador"}).json()
        acao_id = r["acoes"][0]["id"]
        assert c.get("/api/acoes", params={"status": "pendente"}).json()[0]["id"] == acao_id

        assert c.post(f"/api/acoes/{acao_id}/confirmar").json()["status"] == "executada"
        assert c.post(f"/api/acoes/{acao_id}/confirmar").status_code == 409

        # a conversa guarda histórico
        r2 = c.post("/api/chat", json={"mensagem": "quais lojas?", "conversa_id": r["conversa_id"]}).json()
        assert r2["conversa_id"] == r["conversa_id"]

        assert c.post("/api/demo/resetar").json() == {"ok": True}
        assert c.get("/api/acoes").json() == []
