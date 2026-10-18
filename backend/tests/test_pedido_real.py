"""C16 — pedido de verdade na conta de teste: nunca Pix, nunca cartão online; busca com fallback em browseOffers.

Parte com cliente falso (formatos possíveis do MCP real) e parte pelo protocolo MCP, com o servidor de demonstração
aberto como se fosse o modo real (`ClienteIFood(sessao, "real")`: adapta argumentos pelo input_schema).
"""

import json

import pytest
from mcp import Client

from app.ifood_mcp import resetar_demo
from app.ifood_mcp.cliente import ClienteIFood, ErroMCP
from app.ifood_mcp.demo_server import ARQUIVO_DADOS, criar_servidor_demo
from app.match import checkout
from app.match.busca import buscar_detalhado
from app.match.checkout import (MSG_ENVIO_SEM_GARANTIA, MSG_SEM_PAGAMENTO_SEGURO, ErroCheckout, _ler_pagamento,
                                enviar_pedidos, montar_carrinhos, sem_cobranca_online)
from app.match.modelos import Candidato, Combinacao, Intencao

PIX = {"id": "pm-pix", "name": "Pix", "type": "PIX"}
CREDITO_ONLINE = {"id": "pm-cred", "name": "Mastercard •••• 1234", "type": "CREDIT_CARD", "online": True}
CREDITO = {"id": "pm-cred2", "name": "Visa •••• 9999", "type": "CREDIT_CARD"}
DINHEIRO = {"id": "pm-cash", "name": "Dinheiro", "type": "CASH", "onDelivery": True}
VR_NA_ENTREGA = {"id": "pm-vr", "name": "Vale-refeição na entrega", "type": "MEAL_VOUCHER", "offline": True}


@pytest.fixture(autouse=True)
def demo_limpo():
    resetar_demo()
    yield
    resetar_demo()


# ---------- cliente falso: só o que o checkout usa ----------
class ClienteFalso:
    def __init__(self, modo: str, pagamentos: dict, carrinho_extra: dict | None = None):
        self.modo = modo
        self.pagamentos = pagamentos
        self.carrinho_extra = carrinho_extra or {}
        self.chamadas: list[tuple[str, dict]] = []

    @property
    def tools(self) -> list[str]:
        return [t for t, _ in self.chamadas]

    async def chamar(self, tool: str, **args):
        self.chamadas.append((tool, args))
        if tool == "createCart":
            return {"cartId": "cart-1"}
        if tool == "addItemToCart":
            return {"cartItemId": "ci-1"}
        if tool == "getCartDeliveryMethods":
            return {"methods": [{"id": "DEFAULT", "name": "Entrega", "estimatedTime": 40}]}
        if tool == "setCartDelivery":
            return {}
        if tool == "listPaymentMethods":
            return self.pagamentos
        if tool == "setCartPayment":
            return {}
        if tool == "getCart":
            return {"cartId": "cart-1", "merchantName": "Loja Real",
                    "items": [{"cartItemId": "ci-1", "itemId": "it-1", "name": "Marmita", "quantity": 1,
                               "unitPrice": 25.0}],
                    "subtotal": 25.0, "deliveryFee": 5.0, "discount": 0, "total": 30.0, **self.carrinho_extra}
        if tool == "submitOrder":
            return {"orderId": "ord-1", "total": 30.0}
        raise AssertionError(f"tool inesperada: {tool}")


def _comb() -> Combinacao:
    c = Candidato(participante_id="ana", loja_id="loja-1", loja_nome="Loja Real", item_id="it-1",
                  item_nome="Marmita", preco=25.0, eta_min=40, vertical="RESTAURANT", perecivel=False)
    return Combinacao(escolhas={"ana": c}, lojas=["loja-1"], score=1.0, componentes={}, taxa_conhecida=False)


def _pagamento_enviado(cli: ClienteFalso) -> str | None:
    return next((a["paymentMethodId"] for t, a in cli.chamadas if t == "setCartPayment"), None)


# ---------- escolha da forma de pagamento ----------
async def test_real_escolhe_dinheiro_na_entrega_entre_pix_e_credito():
    cli = ClienteFalso("real", {"methods": [PIX, CREDITO_ONLINE, DINHEIRO]})
    [carrinho] = await montar_carrinhos(cli, _comb(), "end-1")
    assert _pagamento_enviado(cli) == "pm-cash"
    assert carrinho["pagamento"] == {"id": "pm-cash", "nome": "Dinheiro", "tipo": "CASH", "offline": True}
    assert not carrinho["avisos"]


async def test_real_sem_forma_sem_cobranca_para_antes_do_setcartpayment():
    cli = ClienteFalso("real", {"methods": [PIX, CREDITO]})
    with pytest.raises(ErroCheckout) as erro:
        await montar_carrinhos(cli, _comb(), "end-1")
    assert erro.value.codigo == "sem_pagamento_sem_cobranca" and erro.value.loja_id == "loja-1"
    assert erro.value.mensagem.startswith(MSG_SEM_PAGAMENTO_SEGURO) and "Loja Real" in erro.value.mensagem
    assert "listPaymentMethods" in cli.tools
    assert "setCartPayment" not in cli.tools and "submitOrder" not in cli.tools


async def test_real_ignora_recomendacao_de_pix():
    resp = {"methods": [PIX, CREDITO, VR_NA_ENTREGA], "agentHints": {"recommendedMethodId": "pm-pix"}}
    cli = ClienteFalso("real", resp)
    [carrinho] = await montar_carrinhos(cli, _comb(), "end-1")
    assert _pagamento_enviado(cli) == "pm-vr" and carrinho["pagamento"]["offline"] is True


def test_real_recomendacao_so_vale_entre_as_formas_sem_cobranca():
    maquininha = {"id": "pm-maq", "name": "Cartão na entrega (maquininha)", "type": "CREDIT_CARD", "onDelivery": True}
    resp = {"methods": [PIX, VR_NA_ENTREGA, maquininha], "agentHints": {"recommendedMethodId": "pm-maq"}}
    m, aviso, offline = _ler_pagamento(resp, None, "real")
    assert m["id"] == "pm-maq" and aviso is None and offline is True
    # dinheiro ganha da recomendação (o mais seguro de todos)
    m, _, _ = _ler_pagamento({**resp, "methods": [*resp["methods"], DINHEIRO]}, None, "real")
    assert m["id"] == "pm-cash"


def test_real_pagamento_pedido_pix_e_trocado_com_aviso():
    m, aviso, offline = _ler_pagamento({"methods": [PIX, DINHEIRO]}, "pm-pix", "real")
    assert m["id"] == "pm-cash" and offline is True
    assert "pm-pix" in aviso and "sem cobrança online" in aviso


def test_modo_desconhecido_e_tratado_como_real():
    with pytest.raises(ErroMCP, match="sem cobrança"):
        _ler_pagamento({"methods": [PIX, CREDITO]}, None, None)


def test_demo_inalterado_primeiro_credito_mesmo_com_recomendacao_pix():
    resp = {"methods": [PIX, CREDITO, DINHEIRO], "agentHints": {"recommendedMethodId": "pm-pix"}}
    m, aviso, offline = _ler_pagamento(resp, None, "demo")
    assert m["id"] == "pm-cred2" and aviso is None and offline is False
    m, aviso, _ = _ler_pagamento(resp, "pm-pix", "demo")  # no demo o id pedido é respeitado
    assert m["id"] == "pm-pix" and aviso is None


@pytest.mark.parametrize("forma, contexto_resp, esperado", [
    ({"id": "a", "name": "Dinheiro na entrega"}, None, True),
    ({"id": "a", "method": "CASH"}, None, True),
    ({"id": "a", "type": {"name": "OFFLINE"}, "method": {"name": "DEBIT"}}, None, True),
    ({"id": "a", "paymentType": "ON_DELIVERY", "brand": "Elo"}, None, True),
    ({"id": "a", "name": "Cartão de crédito na entrega"}, None, True),
    ({"id": "a", "type": "MEAL_VOUCHER"}, None, False),                      # vale sem "na entrega": pode ser online
    ({"id": "a", "type": "MEAL_VOUCHER", "onDelivery": True}, None, True),
    ({"id": "a", "type": "CREDIT_CARD"}, None, False),                       # cartão sem marca de entrega = online
    ({"id": "a", "type": "CASH", "online": True}, None, False),              # contraditório → não arrisca
    ({"id": "a", "type": "CASH", "offline": False}, None, False),
    ({"id": "a", "name": "Pix na entrega", "offline": True}, None, False),   # Pix nunca
    ({"id": "pm-pix-1", "name": "Pagamento na entrega"}, None, False),       # Pix no id também conta
    ({"id": "a", "type": {"name": "ONLINE"}, "name": "Dinheiro"}, None, False),
    ({"id": "a", "name": "Dinheiro", "description": "nada é cobrado online"}, None, True),  # "online" só no texto
    ({"id": "a", "name": "Visa"}, {"name": "Pague na entrega"}, True),        # herdado do grupo
    ({"id": "a", "name": "Visa"}, {"name": "Pague pelo app"}, False),
    ({"id": "a", "name": "Visa"}, {"type": "ONLINE"}, False),
])
def test_classificacao_sem_cobranca(forma, contexto_resp, esperado):
    assert sem_cobranca_online(forma, contexto_resp) is esperado


@pytest.mark.parametrize("resp, id_esperado", [
    ({"paymentMethods": [PIX, {"id": "x", "name": "Dinheiro"}]}, "x"),
    ({"data": {"methods": [CREDITO, {"paymentMethodId": "y", "method": "CASH"}]}}, "y"),
    ({"groups": [{"name": "Pague pelo app", "methods": [PIX, CREDITO]},
                 {"name": "Pague na entrega", "methods": [{"id": "z", "name": "Elo"}]}]}, "z"),
    ({"online": [PIX, CREDITO], "offline": [{"id": "w", "name": "Elo"}]}, "w"),
])
def test_formatos_da_lista_de_pagamentos(resp, id_esperado):
    m, _, offline = _ler_pagamento(resp, None, "real")
    assert checkout._id_pagamento(m) == id_esperado and offline is True


# ---------- envio ----------
async def test_real_envia_com_dinheiro_e_consentimento():
    cli = ClienteFalso("real", {"methods": [PIX, DINHEIRO]})
    carrinhos = await montar_carrinhos(cli, _comb(), "end-1")
    pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
    assert [(p["status"], p["order_id"]) for p in pedidos] == [("enviado", "ord-1")]
    assert ("submitOrder", {"cartId": "cart-1", "userConsent": True}) in cli.chamadas


async def test_real_nao_envia_carrinho_sem_garantia_de_pagamento_offline():
    cli = ClienteFalso("real", {"methods": [DINHEIRO]})
    carrinhos = await montar_carrinhos(cli, _comb(), "end-1")
    for pagamento in ({**carrinhos[0]["pagamento"], "offline": False}, None):
        antigo = {**carrinhos[0], "pagamento": pagamento}  # ex.: carrinho guardado antes da C16
        pedidos = await enviar_pedidos(cli, [antigo], consentimento=True)
        assert pedidos == [{"loja_id": "loja-1", "loja_nome": "Loja Real", "status": "falhou",
                            "erro": MSG_ENVIO_SEM_GARANTIA}]
    assert "submitOrder" not in cli.tools


async def test_real_nao_envia_se_o_getcart_mostra_pix():
    cli = ClienteFalso("real", {"methods": [DINHEIRO]})
    carrinhos = await montar_carrinhos(cli, _comb(), "end-1")
    cli.carrinho_extra = {"paymentMethod": {"id": "pm-pix", "name": "Pix", "type": "PIX"}}  # trocado por fora
    pedidos = await enviar_pedidos(cli, carrinhos, consentimento=True)
    assert pedidos[0]["status"] == "falhou" and pedidos[0]["erro"] == MSG_ENVIO_SEM_GARANTIA
    assert "submitOrder" not in cli.tools


# ---------- pelo protocolo MCP: servidor de demonstração tratado como real ----------
def _cand_demo(slot: str, loja_id: str, item_id: str) -> Candidato:
    dados = json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
    loja = next(l for l in dados["lojas"] if l["id"] == loja_id)
    item = next(i for i in loja["itens"] if i["id"] == item_id)
    return Candidato(participante_id=slot, loja_id=loja_id, loja_nome=loja["nome"], item_id=item_id,
                     item_nome=item["nome"], preco=item["preco"], eta_min=loja["tempo_entrega_min"],
                     vertical=loja["merchantType"], perecivel=False)


async def test_protocolo_modo_real_usa_dinheiro_e_envia_so_com_permissao():
    comb = Combinacao(escolhas={"ana": _cand_demo("ana", "loja-demo-burger", "bg-smash")},
                      lojas=["loja-demo-burger"], score=1.0, componentes={}, taxa_conhecida=False)
    async with Client(criar_servidor_demo()) as sessao:
        cli = ClienteIFood(sessao, "real", permitir_envio=False)
        [carrinho] = await montar_carrinhos(cli, comb, "end-demo-sao-carlos")
        # demo recomenda Pix e tem crédito antes: no modo real vale só o dinheiro na entrega
        assert carrinho["pagamento"]["id"] == "pm-demo-dinheiro"
        assert carrinho["pagamento"]["offline"] is True and carrinho["pagamento"]["tipo"] == "CASH"
        assert (await cli.chamar("getCart", cartId=carrinho["cart_id"]))["paymentMethod"]["id"] == "pm-demo-dinheiro"

        travado = await enviar_pedidos(cli, [carrinho], consentimento=True)  # sem IFOOD_MCP_PERMITIR_ENVIO
        assert travado[0]["status"] == "falhou" and "Envio real desligado" in travado[0]["erro"]

        cli._permitir_envio = True
        [pedido] = await enviar_pedidos(cli, [carrinho], consentimento=True)
    assert pedido["status"] == "enviado" and pedido["order_id"]
    tools = [c.tool for c in cli.rastro]
    assert tools.index("listPaymentMethods") < tools.index("setCartPayment") < tools.index("submitOrder")


# ---------- busca: fallback em browseOffers ----------
class BuscaFalsa:
    """searchOffers/getMerchant vazios (ou fora da vertical); browseOffers traz itens perto do endereço."""

    modo = "real"

    def __init__(self, itens_busca: list[dict] | None = None):
        self.itens_busca = itens_busca or []
        self.chamadas: list[tuple[str, dict]] = []

    async def chamar(self, tool: str, **args):
        self.chamadas.append((tool, args))
        if tool == "searchOffers":
            return {"results": self.itens_busca if args.get("resultKind") == "ITEM" else []}
        if tool == "browseOffers":
            return {"results": [
                {"itemId": "b1", "name": "Feijão tropeiro", "price": 32.0, "merchantId": "m1",
                 "merchantName": "Mineiro", "merchantType": "RESTAURANT", "deliveryTime": "30-40 min"},
                {"itemId": "b2", "name": "Prato caro", "price": 99.0, "merchantId": "m1",
                 "merchantName": "Mineiro", "merchantType": "RESTAURANT"},
            ]}
        raise AssertionError(tool)


ENDERECO = {"id": "e1", "latitude": -22.0, "longitude": -47.9}


async def test_busca_vazia_cai_em_browseoffers_perto_do_endereco():
    cli = BuscaFalsa()
    intencao = Intencao("ana", consultas=["feijoada completa"], verticais=["RESTAURANT"], orcamento_max=60)
    candidatos, detalhes = await buscar_detalhado(cli, intencao, ENDERECO)
    assert [c.item_id for c in candidatos] == ["b1"]  # o de R$ 99 fica fora do orçamento
    assert ("m1", "b1") in detalhes
    tools = [t for t, _ in cli.chamadas]
    assert tools[0] == "searchOffers" and tools[-1] == "browseOffers"
    args = cli.chamadas[-1][1]
    assert args["merchantType"] == "RESTAURANT" and args["resultKind"] == "ITEM"
    assert (args["latitude"], args["longitude"]) == (-22.0, -47.9)


async def test_busca_so_fora_da_vertical_tambem_cai_em_browseoffers():
    mercado = {"itemId": "x", "name": "Feijoada congelada", "price": 20.0, "merchantId": "mx",
               "merchantName": "Mercado", "merchantType": "GROCERIES"}
    cli = BuscaFalsa([mercado])
    intencao = Intencao("ana", consultas=["feijoada"], verticais=["RESTAURANT"])
    candidatos, _ = await buscar_detalhado(cli, intencao, ENDERECO)
    assert [c.item_id for c in candidatos] == ["b1", "b2"]
    assert "browseOffers" in [t for t, _ in cli.chamadas]


async def test_busca_com_resultado_nao_chama_browseoffers():
    achado = {"itemId": "f1", "name": "Feijoada completa", "price": 45.0, "merchantId": "m2",
              "merchantName": "Boteco", "merchantType": "RESTAURANT"}
    cli = BuscaFalsa([achado])
    candidatos, _ = await buscar_detalhado(cli, Intencao("ana", consultas=["feijoada"]), ENDERECO)
    assert [c.item_id for c in candidatos] == ["f1"]
    assert "browseOffers" not in [t for t, _ in cli.chamadas]


async def test_browseoffers_com_erro_nao_quebra_a_busca():
    class Quebrada(BuscaFalsa):
        async def chamar(self, tool, **args):
            if tool == "browseOffers":
                self.chamadas.append((tool, args))
                raise ErroMCP("fora do ar")
            return await super().chamar(tool, **args)

    cli = Quebrada()
    assert await buscar_detalhado(cli, Intencao("ana", consultas=["feijoada"]), ENDERECO) == ([], {})
