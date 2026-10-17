"""MCP de demonstração do iFood (consumidor) + cliente com rastro, testados pelo protocolo MCP."""

import dataclasses

import pytest
from mcp import Client

from app.config import carregar
from app.ifood_mcp import ErroMCP, abrir_cliente, criar_servidor_demo, resetar_demo, resumir

TOOLS_DA_DOC = {
    "getUser", "listAddresses", "searchOffers", "browseOffers", "getRecommendations", "getMerchant", "getItem",
    "createCart", "addItemToCart", "getCartDeliveryMethods", "setCartDelivery", "listPaymentMethods",
    "setCartPayment", "getCart", "submitOrder", "trackOrder", "getOrder",
}


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


async def test_servidor_expoe_as_tools_com_nomes_da_doc():
    async with Client(criar_servidor_demo()) as c:
        nomes = {t.name for t in (await c.list_tools()).tools}
    assert TOOLS_DA_DOC <= nomes


async def _montar_carrinho(cli, consulta="sorvete"):
    enderecos = await cli.chamar("listAddresses")
    end = enderecos["addresses"][0]
    coords = end["coordinates"]
    busca = await cli.chamar("searchOffers", query=consulta, latitude=coords["latitude"],
                             longitude=coords["longitude"], limit=5, resultKind="ITEM")
    oferta = busca["results"][0]
    loja = await cli.chamar("getMerchant", merchantId=oferta["merchantId"])
    item = await cli.chamar("getItem", merchantId=loja["merchantId"], itemId=oferta["itemId"])
    carrinho = await cli.chamar("createCart", merchantId=loja["merchantId"], addressId=end["addressId"])
    adicionado = await cli.chamar("addItemToCart", cartId=carrinho["cartId"], itemId=item["itemId"], quantity=2)
    return end, item, carrinho["cartId"], adicionado


async def test_sequencia_obrigatoria_inteira_via_cliente():
    async with abrir_cliente(carregar()) as cli:
        assert cli.modo == "demo"
        end, item, cart_id, adicionado = await _montar_carrinho(cli)
        assert end["alias"] == "Demonstração — São Carlos"
        assert adicionado["cartItemId"] and adicionado["item"]["quantity"] == 2

        entregas = await cli.chamar("getCartDeliveryMethods", cartId=cart_id)
        metodo = entregas["methods"][0]
        assert {"id", "name", "estimatedTime", "cost", "availableWindows"} <= metodo.keys()
        await cli.chamar("setCartDelivery", cartId=cart_id, deliveryMethodId=metodo["id"])

        pagamentos = await cli.chamar("listPaymentMethods", cartId=cart_id)
        assert all({"id", "name", "type"} <= m.keys() for m in pagamentos["methods"])
        await cli.chamar("setCartPayment", cartId=cart_id, paymentMethodId=pagamentos["methods"][0]["id"])

        carrinho = await cli.chamar("getCart", cartId=cart_id)
        for campo in ("items", "subtotal", "deliveryFee", "discount", "total", "deliveryMethod", "paymentMethod",
                      "warnings"):
            assert campo in carrinho
        assert carrinho["subtotal"] == round(item["price"] * 2, 2)
        assert carrinho["deliveryFee"] == metodo["cost"] > 0
        assert carrinho["total"] == round(carrinho["subtotal"] + carrinho["deliveryFee"] - carrinho["discount"], 2)

        pedido = await cli.chamar("submitOrder", cartId=cart_id, userConsent=True)
        assert pedido["orderId"] and pedido["demonstracao"] is True

        codigos = []
        for _ in range(5):
            r = await cli.chamar("trackOrder", orderId=pedido["orderId"])
            codigos.append(r["status"]["code"])
            assert r["demonstracao"] is True
        assert codigos == ["CONFIRMED", "PREPARING", "DISPATCHED", "CONCLUDED", "CONCLUDED"]
        assert r["agentHints"]["pollingStop"] is True and r["agentHints"]["retryMessage"] is None
        assert [h["code"] for h in r["statusHistory"]][0] == "CONCLUDED"

        detalhe = await cli.chamar("getOrder", orderId=pedido["orderId"])
        assert detalhe["id"] == pedido["orderId"] and detalhe["demonstracao"] is True

    esperado = ["listAddresses", "searchOffers", "getMerchant", "getItem", "createCart", "addItemToCart",
                "getCartDeliveryMethods", "setCartDelivery", "listPaymentMethods", "setCartPayment", "getCart",
                "submitOrder", "trackOrder", "trackOrder", "trackOrder", "trackOrder", "trackOrder", "getOrder"]
    assert [c.tool for c in cli.rastro] == esperado
    assert all(c.ok and c.erro is None and c.ms >= 0 for c in cli.rastro)
    assert all(len(c.resumo) <= 80 and c.resumo.startswith(c.tool) for c in cli.rastro)
    assert not any("latitude" in c.resumo for c in cli.rastro)


async def test_trackorder_tem_retry_message_antes_do_fim():
    async with abrir_cliente(carregar()) as cli:
        _, _, cart_id, _ = await _montar_carrinho(cli, "pizza")
        await cli.chamar("setCartDelivery", cartId=cart_id, deliveryMethodId="DEFAULT")
        await cli.chamar("setCartPayment", cartId=cart_id, paymentMethodId="pm-demo-pix")
        pedido = await cli.chamar("submitOrder", cartId=cart_id, userConsent=True)
        r = await cli.chamar("trackOrder", orderId=pedido["orderId"])
    assert r["status"]["code"] == "CONFIRMED"
    assert r["agentHints"]["retryMessage"] and r["agentHints"]["pollingStop"] is None


async def test_submitorder_sem_consentimento_falha_com_mensagem_legivel():
    async with abrir_cliente(carregar()) as cli:
        _, _, cart_id, _ = await _montar_carrinho(cli)
        await cli.chamar("setCartDelivery", cartId=cart_id, deliveryMethodId="DEFAULT")
        await cli.chamar("setCartPayment", cartId=cart_id, paymentMethodId="pm-demo-credito")
        with pytest.raises(ErroMCP) as sem_campo:
            await cli.chamar("submitOrder", cartId=cart_id)
        with pytest.raises(ErroMCP) as falso:
            await cli.chamar("submitOrder", cartId=cart_id, userConsent=False)
        carrinho = await cli.chamar("getCart", cartId=cart_id)

    for erro in (sem_campo, falso):
        assert "consentimento" in str(erro.value) and "Error executing" not in str(erro.value)
    assert carrinho["status"] == "OPEN"  # nada foi enviado
    falhas = [c for c in cli.rastro if not c.ok]
    assert [c.tool for c in falhas] == ["submitOrder", "submitOrder"]
    assert all("consentimento" in c.erro for c in falhas)


async def test_submitorder_exige_entrega_e_pagamento():
    async with abrir_cliente(carregar()) as cli:
        _, _, cart_id, _ = await _montar_carrinho(cli)
        with pytest.raises(ErroMCP, match="entrega"):
            await cli.chamar("submitOrder", cartId=cart_id, userConsent=True)


async def test_rastro_tem_uma_entrada_por_chamada():
    async with abrir_cliente(carregar()) as cli:
        await cli.chamar("getUser")
        await cli.chamar("listAddresses")
        with pytest.raises(ErroMCP, match="não encontrada"):
            await cli.chamar("getMerchant", merchantId="loja-que-nao-existe")
        await cli.chamar("browseOffers", merchantType="GROCERIES")
    assert [(c.tool, c.ok) for c in cli.rastro] == [
        ("getUser", True), ("listAddresses", True), ("getMerchant", False), ("browseOffers", True)]
    assert dataclasses.asdict(cli.rastro[0]).keys() == {"tool", "resumo", "ms", "ok", "erro"}


async def test_busca_sorvete_acha_a_sorveteria_sem_acento_e_maiuscula():
    async with abrir_cliente(carregar()) as cli:
        lojas = await cli.chamar("searchOffers", query="SORVETES", resultKind="MERCHANT")
        itens = await cli.chamar("searchOffers", query="acai", resultKind="ITEM")
    nomes = [l["name"] for l in lojas["results"]]
    assert "Gelato Bom Clima (demo)" in nomes
    assert itens["results"] and all(i["merchantName"] == "Açaí do Campus (demo)" for i in itens["results"])
    assert all(i["perecivel"] for i in itens["results"])


async def test_busca_acha_itens_do_roteiro():
    async with abrir_cliente(carregar()) as cli:
        japones = await cli.chamar("searchOffers", query="japonês", resultKind="MERCHANT")
        burger = await cli.chamar("searchOffers", query="hambúrguer", resultKind="ITEM")
        veg = await cli.chamar("searchOffers", query="vegetariano", resultKind="ITEM",
                               refinements={"maxPrice": 30, "merchantType": "RESTAURANT"})
        mercado = await cli.chamar("browseOffers", merchantType="GROCERIES")
    assert japones["results"][0]["merchantId"] == "loja-demo-japones"
    assert any(i["merchantId"] == "loja-demo-burger" for i in burger["results"])
    assert veg["results"] and all("vegetariano" in i["tags"] and i["price"] <= 30 for i in veg["results"])
    assert [l["merchantId"] for l in mercado["results"]] == ["loja-demo-mercado"]


async def test_taxa_de_entrega_nao_aparece_na_busca():
    async with abrir_cliente(carregar()) as cli:
        for kind in ("MERCHANT", "ITEM"):
            r = await cli.chamar("searchOffers", query="pizza", resultKind=kind)
            assert r["results"]
            for resultado in r["results"]:
                assert not {"deliveryFee", "cost", "taxa_entrega", "fee"} & resultado.keys()
        loja = await cli.chamar("getMerchant", merchantId="loja-demo-pizza")
        assert "deliveryFee" not in loja and "taxa_entrega" not in loja


async def test_createcart_nao_e_idempotente_e_payload_tem_selo():
    async with abrir_cliente(carregar()) as cli:
        a = await cli.chamar("createCart", merchantId="loja-demo-burger", addressId="end-demo-sao-carlos")
        b = await cli.chamar("createCart", merchantId="loja-demo-burger", addressId="end-demo-sao-carlos")
        assert a["cartId"] != b["cartId"]
        assert a["demonstracao"] is True and b["demonstracao"] is True
        with pytest.raises(ErroMCP, match="não existe na loja"):
            await cli.chamar("addItemToCart", cartId=a["cartId"], itemId="sv-sundae", quantity=1)


async def test_resetar_demo_apaga_carrinhos():
    async with abrir_cliente(carregar()) as cli:
        a = await cli.chamar("createCart", merchantId="loja-demo-burger", addressId="end-demo-sao-carlos")
        resetar_demo()
        with pytest.raises(ErroMCP, match="não encontrado"):
            await cli.chamar("getCart", cartId=a["cartId"])


async def test_modo_real_fica_para_a_etapa_03(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    with pytest.raises(NotImplementedError, match="etapa 03"):
        async with abrir_cliente(carregar()):
            pass


def test_resumo_curto_e_sem_dados_sensiveis():
    r = resumir("searchOffers", {"query": "x" * 200, "latitude": -22.0, "longitude": -47.8,
                                 "resultKind": "ITEM", "refinements": {"maxPrice": 30}, "limit": 5})
    assert len(r) <= 80 and r.startswith("searchOffers(") and "-22" not in r
