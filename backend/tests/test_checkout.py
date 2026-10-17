"""Checkout do Match (C6) contra o MCP de demonstração, pelo protocolo MCP."""

import json

import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.ifood_mcp.demo_server import ARQUIVO_DADOS
from app.match.checkout import ErroCheckout, acompanhar, enviar_pedidos, montar_carrinhos
from app.match.modelos import Candidato, Combinacao, para_dict

ENDERECO = "end-demo-sao-carlos"
SEQUENCIA_LOJA = ["createCart", "addItemToCart", "getCartDeliveryMethods", "setCartDelivery",
                  "listPaymentMethods", "setCartPayment", "getCart"]


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


def _lojas() -> dict:
    dados = json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
    return {l["id"]: l for l in dados["lojas"]}


def _cand(slot: str, loja_id: str, item_id: str) -> Candidato:
    loja = _lojas()[loja_id]
    item = next(i for i in loja["itens"] if i["id"] == item_id)
    return Candidato(participante_id=slot, loja_id=loja_id, loja_nome=loja["nome"], item_id=item_id,
                     item_nome=item["nome"], preco=item["preco"], eta_min=loja["tempo_entrega_min"],
                     vertical=loja["merchantType"], perecivel=bool(item.get("perecivel", False)))


def _combinacao(*cands: Candidato) -> Combinacao:
    escolhas = {c.participante_id: c for c in cands}
    lojas = list(dict.fromkeys(c.loja_id for c in cands))
    return Combinacao(escolhas=escolhas, lojas=lojas, score=1.0, componentes={}, taxa_conhecida=False)


def _combinacao_roteiro() -> Combinacao:
    # Thales: japonês + sorvete (2 slots) · Milan: japonês · Zenon: sorvete
    return _combinacao(
        _cand("thales", "loja-demo-japones", "jp-temaki"),
        _cand("thales#2", "loja-demo-sorvete", "sv-pistache300"),
        _cand("milan", "loja-demo-japones", "jp-hotroll"),
        _cand("zenon", "loja-demo-sorvete", "sv-chocolate500"),
    )


async def test_monta_dois_carrinhos_com_valores_do_getcart():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        conferencia = [await cli.chamar("getCart", cartId=c["cart_id"]) for c in carrinhos]

    assert [c["loja_id"] for c in carrinhos] == ["loja-demo-japones", "loja-demo-sorvete"]
    for c, real in zip(carrinhos, conferencia):
        assert (c["subtotal"], c["taxa"], c["desconto"], c["total"]) == (
            real["subtotal"], real["deliveryFee"], real["discount"], real["total"])
        assert c["loja_nome"] == real["merchantName"]
        assert c["pagamento"]["id"] == "pm-demo-credito" == real["paymentMethod"]["id"]  # 1º crédito
        assert c["eta_min"] == _lojas()[c["loja_id"]]["tempo_entrega_min"]
        assert c["demonstracao"] is True
        assert real["deliveryMethod"]["id"] == "DEFAULT"  # recomendado em agentHints

    jp, sv = carrinhos
    assert [(i["item_id"], i["participante_id"], i["slot"]) for i in jp["itens"]] == [
        ("jp-temaki", "thales", "thales"), ("jp-hotroll", "milan", "milan")]
    assert [(i["item_id"], i["participante_id"], i["slot"]) for i in sv["itens"]] == [
        ("sv-pistache300", "thales", "thales#2"), ("sv-chocolate500", "zenon", "zenon")]
    assert jp["subtotal"] == round(32.9 + 26.9, 2) and jp["taxa"] == 7.99
    assert all(i["preco"] and i["quantidade"] == 1 for i in jp["itens"] + sv["itens"])

    ferramentas = [c.tool for c in cli.rastro]
    esperado_loja = lambda n: SEQUENCIA_LOJA[:2] + ["addItemToCart"] * (n - 1) + SEQUENCIA_LOJA[2:]
    assert ferramentas[:-2] == esperado_loja(2) + esperado_loja(2)
    assert "submitOrder" not in ferramentas


async def test_mesmo_item_para_duas_pessoas_vira_duas_linhas_e_aceita_dict():
    comb = _combinacao(_cand("ana", "loja-demo-burger", "bg-smash"), _cand("bia", "loja-demo-burger", "bg-smash"))
    async with abrir_cliente(carregar()) as cli:
        [carrinho] = await montar_carrinhos(cli, para_dict(comb), ENDERECO, pagamento_id="pm-demo-pix")
    assert [(i["item_id"], i["participante_id"]) for i in carrinho["itens"]] == [
        ("bg-smash", "ana"), ("bg-smash", "bia")]
    assert carrinho["subtotal"] == round(29.9 * 2, 2)
    assert carrinho["pagamento"]["id"] == "pm-demo-pix" and not carrinho["avisos"]


async def test_pagamento_inexistente_cai_no_credito_e_avisa():
    comb = _combinacao(_cand("ana", "loja-demo-acai", "ac-500"))
    async with abrir_cliente(carregar()) as cli:
        [carrinho] = await montar_carrinhos(cli, comb, ENDERECO, pagamento_id="pm-que-nao-existe")
    assert carrinho["pagamento"]["id"] == "pm-demo-credito"
    assert any("pm-que-nao-existe" in a for a in carrinho["avisos"])


async def test_falha_ao_montar_levanta_erro_com_a_loja():
    ruim = _cand("ana", "loja-demo-burger", "bg-smash")
    ruim.item_id = "sv-sundae"  # item de outra loja
    async with abrir_cliente(carregar()) as cli:
        with pytest.raises(ErroCheckout) as erro:
            await montar_carrinhos(cli, _combinacao(_cand("bia", "loja-demo-acai", "ac-300"), ruim), ENDERECO)
    assert erro.value.loja_id == "loja-demo-burger"
    assert "Brasa Burger" in erro.value.mensagem and "não existe na loja" in erro.value.mensagem


async def test_sem_consentimento_nao_envia_nada():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        antes = len(cli.rastro)
        for consentimento in (False, None, "sim"):
            with pytest.raises(ValueError, match="Sem confirmação humana"):
                await enviar_pedidos(cli, carrinhos, consentimento)
        assert len(cli.rastro) == antes
        assert "submitOrder" not in [c.tool for c in cli.rastro]
        for c in carrinhos:
            assert (await cli.chamar("getCart", cartId=c["cart_id"]))["status"] == "OPEN"


async def test_envia_os_dois_e_acompanha_ate_encerrar():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
        assert [(p["loja_id"], p["status"]) for p in pedidos] == [
            ("loja-demo-japones", "enviado"), ("loja-demo-sorvete", "enviado")]
        assert [p["total"] for p in pedidos] == [c["total"] for c in carrinhos]
        assert all(p["order_id"] for p in pedidos)

        estados = []
        for _ in range(6):
            r = await acompanhar(cli, pedidos[0]["order_id"])
            estados.append(r)
            if r["encerrado"]:
                break
    assert [r["status_code"] for r in estados] == ["CONFIRMED", "PREPARING", "DISPATCHED", "CONCLUDED"]
    assert estados[0]["proxima_consulta"] and estados[0]["proxima_consulta_s"] == 2 and not estados[0]["encerrado"]
    final = estados[-1]
    assert final["encerrado"] is True and final["proxima_consulta"] is None
    assert final["order_id"] == pedidos[0]["order_id"] and final["status_descricao"]
    assert [h["codigo"] for h in final["historico"]] == ["CONCLUDED", "DISPATCHED", "PREPARING", "CONFIRMED"]
    assert [c.tool for c in cli.rastro].count("submitOrder") == 2


async def test_total_mudou_para_antes_de_enviar():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        await cli.chamar("addItemToCart", cartId=carrinhos[1]["cart_id"], itemId="sv-fruta500", quantity=1)
        pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
    assert pedidos[0]["status"] == "enviado" and pedidos[0]["loja_id"] == "loja-demo-japones"
    mudou = pedidos[1]
    assert mudou["status"] == "total_mudou" and mudou["loja_id"] == "loja-demo-sorvete"
    assert mudou["total_agora"] == round(mudou["total_antes"] + 27.9, 2)
    assert [c.tool for c in cli.rastro].count("submitOrder") == 1


async def test_total_mudou_no_primeiro_nao_envia_nenhum():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        await cli.chamar("addItemToCart", cartId=carrinhos[0]["cart_id"], itemId="jp-temaki", quantity=1)
        pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
    assert [p["status"] for p in pedidos] == ["total_mudou"]
    assert "submitOrder" not in [c.tool for c in cli.rastro]


async def test_falha_no_segundo_pedido_mantem_o_primeiro():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        # força a falha: o 2º carrinho já virou pedido por fora, então o submitOrder dele é recusado
        await cli.chamar("submitOrder", cartId=carrinhos[1]["cart_id"], userConsent=True)
        pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
    assert pedidos[0]["status"] == "enviado" and pedidos[0]["order_id"]
    falha = pedidos[1]
    assert falha == {"loja_id": "loja-demo-sorvete", "loja_nome": carrinhos[1]["loja_nome"],
                     "status": "falhou", "erro": falha["erro"]}
    assert "já foi enviado" in falha["erro"] and "Error executing" not in falha["erro"]


async def test_carrinho_invalido_vira_falhou_e_para():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        quebrado = [{**carrinhos[0], "cart_id": "cart-inexistente"}, carrinhos[1]]
        pedidos = await enviar_pedidos(cli, quebrado, consentimento=True)
    assert [(p["loja_id"], p["status"]) for p in pedidos] == [("loja-demo-japones", "falhou")]
    assert "não encontrado" in pedidos[0]["erro"]
    assert "submitOrder" not in [c.tool for c in cli.rastro]


async def test_nao_reenvia_carrinho_ja_enviado():
    async with abrir_cliente(carregar()) as cli:
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)
        ja = set()
        primeira = await enviar_pedidos(cli, carrinhos[:1], consentimento=True, ja_enviados=ja)
        assert ja == {carrinhos[0]["cart_id"]}
        segunda = await enviar_pedidos(cli, carrinhos, consentimento=True, ja_enviados=ja)
        terceira = await enviar_pedidos(cli, carrinhos, consentimento=True, ja_enviados=ja)
    assert [p["loja_id"] for p in primeira] == ["loja-demo-japones"]
    assert [(p["loja_id"], p["status"]) for p in segunda] == [("loja-demo-sorvete", "enviado")]
    assert terceira == []
    assert [c.tool for c in cli.rastro].count("submitOrder") == 2
