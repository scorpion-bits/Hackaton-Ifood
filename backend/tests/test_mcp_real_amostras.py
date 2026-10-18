"""Amostras reais do MCP do iFood (docs/mcp-real/, coletadas pelo Thales em 18/10) contra o nosso código.

- Argumentos: cada chamada que o app faz no modo real é validada contra o input_schema real (`tools.json`):
  obrigatórios presentes, nenhum campo fora do schema, enums válidos (bugs 1, 3, 5).
- Erros: as duas formas de erro "normal" do MCP real (`{"error": {...}}` e `success:false` + `errors{}`) viram
  `ErroMCP` com o code (bug 2).
- Parser: searchOffers/getMerchant/listAddresses reais lidos pela busca.

O cliente é o `ClienteIFood` de verdade (modo "real": adapta args pelo schema e detecta erro), sobre uma sessão
MCP falsa que devolve as amostras. Respostas de carrinho de SUCESSO ainda não têm amostra real: as daqui imitam o
demo/getCart e estão marcadas como suposição.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any, Callable

import pytest

from app.config import carregar
from app.ifood_mcp.cliente import ClienteIFood, ErroMCP, erro_na_resposta
from app.ifood_mcp.diagnostico import executar
from app.match import busca
from app.match.busca import buscar_detalhado, ler_endereco
from app.match.checkout import ErroCheckout, acompanhar, enviar_pedidos, montar_carrinhos
from app.match.modelos import Candidato, Combinacao, Desejo, Intencao
from app.match.motor import MSG_SEM_ENDERECO, rodar_match

PASTA = Path(__file__).resolve().parents[2] / "docs" / "mcp-real"
TOOLS = {t["name"]: t for t in json.loads((PASTA / "tools.json").read_text(encoding="utf-8"))}
SCHEMAS = {n: t.get("input_schema") or t.get("inputSchema") or {} for n, t in TOOLS.items()}
LOCAL = {"latitude": -22.02, "longitude": -47.89}


def _amostra(tool: str) -> dict:
    return json.loads((PASTA / f"{tool}.json").read_text(encoding="utf-8"))


def _resposta(tool: str, rotulo: str | None = None) -> dict:
    chamadas = _amostra(tool)["chamadas"]
    return next(c for c in chamadas if rotulo is None or c["rotulo"] == rotulo)["resposta"]


# ---------- validador mínimo de JSON Schema (o que os schemas reais usam) ----------
_TIPOS = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list,
          "null": type(None)}


def _erros_valor(p: dict, v: Any, caminho: str) -> list[str]:
    tipos = p.get("type")
    tipos = tipos if isinstance(tipos, list) else [tipos] if tipos else []
    if tipos and not any(isinstance(v, _TIPOS[t]) and not (t in ("integer", "number") and isinstance(v, bool))
                         for t in tipos):
        return [f"{caminho}: tipo {type(v).__name__}, esperado {tipos}"]
    if "enum" in p and v not in p["enum"]:
        return [f"{caminho}: {v!r} fora do enum {p['enum']}"]
    if isinstance(v, dict) and p.get("properties"):
        return _erros_objeto(p, v, caminho + ".")
    if isinstance(v, list) and isinstance(p.get("items"), dict):
        return [e for i, x in enumerate(v) for e in _erros_valor(p["items"], x, f"{caminho}[{i}]")]
    return []


def _erros_objeto(schema: dict, args: dict, prefixo: str = "") -> list[str]:
    props = schema.get("properties") or {}
    erros = [f"{prefixo}{r}: obrigatório" for r in schema.get("required") or [] if r not in args]
    for k, v in args.items():
        if k not in props:
            erros.append(f"{prefixo}{k}: fora do schema")
        else:
            erros.extend(_erros_valor(props[k], v, prefixo + k))
    return erros


def validar(tool: str, args: dict) -> list[str]:
    return _erros_objeto(SCHEMAS[tool], args)


# ---------- sessão MCP falsa com os schemas reais ----------
class ErroTool:
    """Resposta com isError (texto como o servidor real manda)."""

    def __init__(self, texto: str):
        self.texto = texto


class SessaoReal:
    def __init__(self, responder: Callable[[str, dict], Any]):
        self.responder = responder
        self.chamadas: list[tuple[str, dict]] = []

    async def call_tool(self, tool: str, args: dict):
        self.chamadas.append((tool, args))
        r = self.responder(tool, args)
        if isinstance(r, ErroTool):
            return NS(is_error=True, structured_content=None, content=[NS(text=r.texto)])
        return NS(is_error=False, structured_content=r, content=[])

    async def list_tools(self, cursor=None):
        tools = [NS(name=t["name"], title=t.get("title"), description=t.get("description"),
                    input_schema=SCHEMAS[t["name"]], output_schema=None, annotations=None) for t in TOOLS.values()]
        return NS(tools=tools, next_cursor=None)

    def args_de(self, tool: str) -> list[dict]:
        return [a for t, a in self.chamadas if t == tool]


def _cliente(responder, permitir_envio: bool = False) -> tuple[ClienteIFood, SessaoReal]:
    sessao = SessaoReal(responder)
    return ClienteIFood(sessao, "real", permitir_envio=permitir_envio), sessao


def _sem_erros_de_schema(sessao: SessaoReal) -> None:
    problemas = {f"{t} #{i}": e for i, (t, a) in enumerate(sessao.chamadas) if (e := validar(t, a))}
    assert problemas == {}


# ---------- os schemas confirmam os bugs ----------
def test_schemas_reais_confirmam_o_que_o_app_precisa():
    assert SCHEMAS["listPaymentMethods"]["required"] == ["merchantId"]
    assert set(SCHEMAS["listPaymentMethods"]["properties"]) == {"merchantId"}  # cartId não existe
    assert "contentMode" in SCHEMAS["getRecommendations"]["required"]
    assert set(SCHEMAS["browseOffers"]["required"]) == {"userLocation", "merchantType"}
    itens = SCHEMAS["createCart"]["properties"]["items"]["items"]
    assert set(itens["required"]) == {"itemId", "quantity"}
    # o schema não marca nada como obrigatório, mas o servidor exige (amostra do bug 1)
    assert SCHEMAS["createCart"]["required"] == []
    assert "items are required" in _resposta("createCart")["error"]["message"]


# ---------- bug 2: erro em resposta normal ----------
def test_erro_do_createcart_real_vira_erromcp_com_code():
    msg, codigo = erro_na_resposta(_resposta("createCart"))
    assert codigo == "MISSING_REQUIRED_FIELDS"
    assert "items are required" in msg and "(código MISSING_REQUIRED_FIELDS)" in msg
    assert "***" not in msg  # userFriendlyMessage mascarado na amostra: cai no message


def test_erro_do_createaddress_formato_success_false():
    resp = {"success": False, "message": "unexpected status: 400 Bad Request (code=ADR-2001)",
            "errors": {"mcpCode": "ADDRESS_CREATION_FAILED", "code": "ADR-2001"}, "retryable": True}
    msg, codigo = erro_na_resposta(resp)
    assert codigo == "ADDRESS_CREATION_FAILED"
    assert msg.startswith("unexpected status: 400") and "ADDRESS_CREATION_FAILED / ADR-2001" in msg


@pytest.mark.parametrize("resp", [
    _resposta("getUser"),                         # success: true
    _resposta("listAddresses"),                   # results: []
    _resposta("searchOffers", "searchOffers pizza ITEM"),
    {"results": [], "errors": []},                # chave errors vazia não é erro
    {"cartId": "c1", "error": None},
    {"success": True, "errors": {}},
])
def test_resposta_valida_nao_vira_erro(resp):
    assert erro_na_resposta(resp) is None


async def test_cliente_real_levanta_erromcp_e_marca_rastro():
    cli, _ = _cliente(lambda t, a: _resposta("createCart"))
    with pytest.raises(ErroMCP) as erro:
        await cli.chamar("createCart", merchantId="m1")
    assert erro.value.codigo == "MISSING_REQUIRED_FIELDS"
    assert cli.rastro[-1].ok is False and "MISSING_REQUIRED_FIELDS" in cli.rastro[-1].erro


async def test_erro_json_no_texto_do_iserror_fica_legivel():
    texto = json.loads(json.dumps(_amostra("getRecommendations")["chamadas"][0]["erro"]))
    cli, _ = _cliente(lambda t, a: ErroTool(texto))
    with pytest.raises(ErroMCP) as erro:
        await cli.chamar("getRecommendations", latitude=-22.0, longitude=-47.9)
    assert str(erro.value).startswith("the value provided for `contentMode`")


# ---------- bugs 1 e 3: checkout real dentro do schema ----------
def _cand(slot: str, loja: str, item: str, preco: float) -> Candidato:
    return Candidato(participante_id=slot, loja_id=loja, loja_nome="Ponto da Esfiha São Carlos", item_id=item,
                     item_nome=f"Item {item}", preco=preco, eta_min=50, vertical="RESTAURANT", perecivel=False)


LOJA = "54615ed7-5697-413b-a508-9156e3f5ec70"
ITEM_A = "9e51164c-fd47-4faf-8e1b-92d480301ce5"  # featuredItems do getMerchant real (R$ 6,00)
ITEM_B = "5c57c447-c13a-4b9d-b34e-d4b1527e18b4"  # R$ 8,99


class CarrinhoSuposto:
    """Respostas de carrinho no formato do demo (o real de sucesso ainda não tem amostra). Erros iguais ao real."""

    def __init__(self, create_devolve_itens: bool = True):
        self.create_devolve_itens = create_devolve_itens
        self.itens: list[dict] = []

    def _linha(self, item_id: str) -> dict:
        preco = {ITEM_A: 6.0, ITEM_B: 8.99}.get(item_id, 75.99)
        linha = {"cartItemId": f"ci-{len(self.itens) + 1}", "itemId": item_id, "name": item_id[:4],
                 "quantity": 1, "unitPrice": preco}
        self.itens.append(linha)
        return linha

    def __call__(self, tool: str, args: dict) -> Any:
        if tool == "createCart":
            if not (args.get("addressId") and args.get("merchantId") and args.get("items")):
                return _resposta("createCart")  # o erro real (MISSING_REQUIRED_FIELDS)
            for i in args["items"]:
                self._linha(i["itemId"])
            return {"cartId": "cart-r1", **({"items": list(self.itens)} if self.create_devolve_itens else {})}
        if tool == "addItemToCart":
            return {"cartItemId": self._linha(args["itemId"])["cartItemId"]}
        if tool == "getCartDeliveryMethods":  # suposição: mesmo formato do deliveryMethod da busca real
            return {"deliveryMethods": [{"deliveryMethodId": "DEFAULT", "deliveryMethodMode": "DELIVERY",
                                         "estimatedMinutes": {"min": 40, "max": 50}, "fee": 7.5}]}
        if tool == "listPaymentMethods":
            if "merchantId" not in args:
                return {"error": {"code": "MISSING_REQUIRED_FIELDS", "message": "merchantId is required."}}
            return {"methods": [{"id": "PIX", "name": "Pix", "type": "PIX"},
                                {"id": "CASH", "name": "Dinheiro", "type": "CASH"}]}
        if tool in ("setCartDelivery", "setCartPayment"):
            return {"cartId": args["cartId"]}
        if tool == "getCart":
            sub = round(sum(i["unitPrice"] for i in self.itens), 2)
            return {"cartId": "cart-r1", "merchantName": "Ponto da Esfiha São Carlos", "items": list(self.itens),
                    "subtotal": sub, "deliveryFee": 7.5, "discount": 0, "total": round(sub + 7.5, 2),
                    "paymentMethod": {"id": "CASH", "name": "Dinheiro", "type": "CASH"}}
        if tool == "submitOrder":
            return {"orderId": "ord-r1"}
        if tool == "trackOrder":
            return {"status": {"code": "CONFIRMED", "description": "ok"}}
        raise AssertionError(tool)


def _comb_dois() -> Combinacao:
    return Combinacao(escolhas={"ana": _cand("ana", LOJA, ITEM_A, 6.0), "bia": _cand("bia", LOJA, ITEM_B, 8.99)},
                      lojas=[LOJA], score=1.0, componentes={}, taxa_conhecida=False)


async def test_checkout_real_cria_carrinho_com_items_e_paga_por_merchant():
    cli, sessao = _cliente(CarrinhoSuposto(), permitir_envio=True)
    [carrinho] = await montar_carrinhos(cli, _comb_dois(), "addr-1")

    [criar] = sessao.args_de("createCart")
    assert criar == {"merchantId": LOJA, "addressId": "addr-1", "items": [{"itemId": ITEM_A, "quantity": 1}]}
    assert [a["itemId"] for a in sessao.args_de("addItemToCart")] == [ITEM_B]  # só o resto
    assert all(a["options"] == [] for a in sessao.args_de("addItemToCart"))  # sem options o servidor real quebra
    assert sessao.args_de("listPaymentMethods") == [{"merchantId": LOJA}]
    assert sessao.args_de("setCartDelivery") == [{"cartId": "cart-r1", "deliveryMethodId": "DEFAULT"}]
    assert sessao.args_de("setCartPayment") == [{"cartId": "cart-r1", "paymentMethodId": "CASH"}]  # nunca Pix
    # dono de cada linha, inclusive a 1ª (cartItemId lido do items[] do createCart)
    assert [(i["item_id"], i["participante_id"], i["cart_item_id"]) for i in carrinho["itens"]] == [
        (ITEM_A, "ana", "ci-1"), (ITEM_B, "bia", "ci-2")]
    assert carrinho["eta_min"] == 50 and carrinho["entrega"] == {"id": "DEFAULT", "nome": "DELIVERY"}

    pedidos = await enviar_pedidos(cli, [carrinho], consentimento=True)
    assert pedidos[0]["status"] == "enviado"
    await acompanhar(cli, pedidos[0]["order_id"])
    assert sessao.args_de("submitOrder") == [{"cartId": "cart-r1", "userConsent": True}]
    _sem_erros_de_schema(sessao)


async def test_checkout_real_sem_cartitemid_no_createcart_casa_pelo_itemid():
    cli, sessao = _cliente(CarrinhoSuposto(create_devolve_itens=False))
    [carrinho] = await montar_carrinhos(cli, _comb_dois(), "addr-1")
    assert [(i["item_id"], i["participante_id"]) for i in carrinho["itens"]] == [(ITEM_A, "ana"), (ITEM_B, "bia")]
    _sem_erros_de_schema(sessao)


async def test_checkout_real_erro_do_createcart_vira_mensagem_legivel():
    cli, _ = _cliente(CarrinhoSuposto())
    with pytest.raises(ErroCheckout) as erro:
        await montar_carrinhos(cli, _comb_dois(), "")  # sem addressId → o erro real
    assert "Ponto da Esfiha" in erro.value.mensagem and "MISSING_REQUIRED_FIELDS" in erro.value.mensagem


async def test_submitorder_real_continua_travado_sem_permissao():
    cli, sessao = _cliente(CarrinhoSuposto(), permitir_envio=False)
    [carrinho] = await montar_carrinhos(cli, _comb_dois(), "addr-1")
    pedidos = await enviar_pedidos(cli, [carrinho], consentimento=True)
    assert pedidos[0]["status"] == "falhou" and "Envio real desligado" in pedidos[0]["erro"]
    assert sessao.args_de("submitOrder") == []


# ---------- bug 17: item com grupo de opção obrigatório (getItem real) ----------
PIZZA = "269eae27-aee2-4224-a89b-7c6bce57f53e"  # "Pizzas Doces Grandes": grupo "Sabores" minSelections 1


class CarrinhoComGetItem(CarrinhoSuposto):
    """getItem devolve a amostra real (pizza com sabor obrigatório); itens simples vêm sem optionGroups."""

    def __call__(self, tool: str, args: dict) -> Any:
        if tool == "getItem":
            if args["itemId"] == PIZZA:
                return _resposta("getItem")
            return {"itemId": args["itemId"], "itemName": "Carne", "optionGroups": [], "unitPrice": 6.0}
        if tool in ("createCart", "addItemToCart"):
            itens = args.get("items") or [args]
            for i in itens:  # o servidor real recusa com ITEM-001 se faltar o obrigatório
                if i["itemId"] == PIZZA and not i.get("options"):
                    return {"error": {"code": "ITEM-001",
                                      "message": "É preciso escolher todos os complementos obrigatórios"}}
        return super().__call__(tool, args)


def _comb_pizza() -> Combinacao:
    return Combinacao(escolhas={"ana": _cand("ana", LOJA, PIZZA, 75.99), "bia": _cand("bia", LOJA, ITEM_A, 6.0)},
                      lojas=[LOJA], score=1.0, componentes={}, taxa_conhecida=False)


async def test_checkout_real_preenche_opcao_obrigatoria_mais_barata():
    cli, sessao = _cliente(CarrinhoComGetItem())
    [carrinho] = await montar_carrinhos(cli, _comb_pizza(), "addr-1", geo=LOCAL)

    assert [a["itemId"] for a in sessao.args_de("getItem")] == [PIZZA, ITEM_A]  # 1 por item escolhido
    assert all(a["userLocation"] == LOCAL and a["merchantId"] == LOJA for a in sessao.args_de("getItem"))
    [criar] = sessao.args_de("createCart")
    # 1 sabor (o mais barato; empate → o 1º da lista), o grupo opcional "Adicional de Frutas" fica de fora
    assert criar["items"] == [{"itemId": PIZZA, "quantity": 1,
                               "options": [{"optionId": "e45c1772-a63d-475c-bddf-9280cb2e6b4d", "quantity": 1}]}]
    assert sessao.args_de("addItemToCart")[0]["options"] == []  # item simples continua com options=[]
    assert any("Pizza Doce de Confete" in a and "75.99" in a for a in carrinho["avisos"])
    assert [i["participante_id"] for i in carrinho["itens"]] == ["ana", "bia"]
    _sem_erros_de_schema(sessao)


async def test_checkout_real_opcao_obrigatoria_tambem_no_additemtocart():
    cli, sessao = _cliente(CarrinhoComGetItem())
    comb = Combinacao(escolhas={"bia": _cand("bia", LOJA, ITEM_A, 6.0), "ana": _cand("ana", LOJA, PIZZA, 75.99)},
                      lojas=[LOJA], score=1.0, componentes={}, taxa_conhecida=False)
    await montar_carrinhos(cli, comb, "addr-1", geo=LOCAL)
    assert "options" not in sessao.args_de("createCart")[0]["items"][0]
    [add] = sessao.args_de("addItemToCart")
    assert add["itemId"] == PIZZA and add["options"] == [{"optionId": "e45c1772-a63d-475c-bddf-9280cb2e6b4d",
                                                          "quantity": 1}]
    _sem_erros_de_schema(sessao)


async def test_checkout_real_coordenadas_podem_vir_dentro_da_combinacao():
    cli, sessao = _cliente(CarrinhoComGetItem())
    comb = {"escolhas": {"ana": _cand("ana", LOJA, PIZZA, 75.99)}, "geo": LOCAL}
    await montar_carrinhos(cli, comb, "addr-1")
    assert sessao.args_de("getItem") and sessao.args_de("createCart")[0]["items"][0]["options"]


async def test_checkout_real_sem_coordenadas_nao_chama_getitem_e_explica_item_001():
    cli, sessao = _cliente(CarrinhoComGetItem())
    with pytest.raises(ErroCheckout) as erro:
        await montar_carrinhos(cli, _comb_pizza(), "addr-1")
    assert sessao.args_de("getItem") == []
    assert erro.value.codigo == "complemento_obrigatorio" and "complementos" in erro.value.mensagem


def test_opcoes_obrigatorias_da_amostra_real():
    obrig = busca.opcoes_obrigatorias(_resposta("getItem"))
    assert obrig == {"opcoes": [{"optionId": "e45c1772-a63d-475c-bddf-9280cb2e6b4d", "quantity": 1}],
                     "extra": 75.99, "nomes": ["Pizza Doce de Confete"], "completo": True}
    assert busca.opcoes_obrigatorias({"itemId": "x"}) is None  # sem optionGroups: não dá para saber


def test_busca_descarta_item_com_opcao_obrigatoria_que_custa():
    item = _resposta("getItem")
    loja = {"id": LOJA, "nome": "Ponto da Esfiha", "aberta": True}
    assert busca._ler_item(item, loja) is None
    gratis = {**item, "optionGroups": [{"minSelections": 1, "options": [
        {"optionId": "o1", "name": "Sem gelo", "additionalPrice": 0}, {"optionId": "o2", "additionalPrice": 2}]}]}
    assert busca._ler_item(gratis, loja) is not None  # obrigatória grátis: o checkout preenche
    opcional = {**item, "optionGroups": [g for g in item["optionGroups"] if g["minSelections"] == 0]}
    assert busca._ler_item(opcional, loja) is not None


# ---------- bug 19: adicional barato não vira prato ----------
@pytest.mark.parametrize("nome, secao, preco, fica", [
    ("Rodeio", "", 0.90, False),                       # o caso real (BK, browseOffers)
    ("Carne", "Esfihas Salgadas Abertas", 6.0, True),  # esfiha barata de verdade
    ("Bacon extra", "Adicionais", 4.0, False),
    ("Adicional de cheddar", "", 5.0, False),
    ("Molho de tomate tradicional 340 g", "Molhos", 4.49, True),  # mercado do demo
])
def test_adicional_barato_nao_vira_prato(nome, secao, preco, fica):
    r = {"itemId": "i1", "itemName": nome, "menuSection": secao, "unitPrice": preco}
    assert (busca._ler_item(r, {"id": "l1", "nome": "Loja"}) is not None) is fica


async def test_browseoffers_real_nao_oferece_rodeio_como_opcao_mais_proxima():
    rodeio = {"itemId": "r1", "itemName": "Rodeio", "unitPrice": 0.9, "promotionalUnitPrice": 0.9,
              "merchant": {"merchantId": "bk", "merchantName": "Burger King", "isOpen": True}}
    whopper = {**rodeio, "itemId": "w1", "itemName": "Whopper", "unitPrice": 29.9, "promotionalUnitPrice": 29.9}

    def responder(tool: str, args: dict) -> Any:
        return {"results": [rodeio, whopper]} if tool == "browseOffers" else {"results": []}

    cli, _ = _cliente(responder)
    intencao = Intencao(participante_id="ana", consultas=["japonês"])
    candidatos, _ = await buscar_detalhado(cli, intencao, {"latitude": -22.02, "longitude": -47.89})
    assert [c.item_nome for c in candidatos] == ["Whopper"]


# ---------- busca: parser das amostras reais + args no schema ----------
def _busca_real(tool: str, args: dict) -> Any:
    if tool == "searchOffers":
        rotulo = f"searchOffers {args['query']} {args.get('resultKind', 'MERCHANT')}"
        try:
            return _resposta("searchOffers", rotulo)
        except StopIteration:
            return {"results": []}
    if tool == "getMerchant":
        return _resposta("getMerchant")
    if tool == "browseOffers":
        return {"results": []}
    raise AssertionError(tool)


async def test_busca_le_itens_reais_do_searchoffers():
    cli, sessao = _cliente(_busca_real)
    candidatos, detalhes = await buscar_detalhado(cli, Intencao("ana", consultas=["pizza"]),
                                                  {"latitude": -22.02, "longitude": -47.89})
    por_id = {c.item_id: c for c in candidatos}
    pizza = por_id["269eae27-aee2-4224-a89b-7c6bce57f53e"]
    assert (pizza.item_nome, pizza.loja_nome, pizza.preco, pizza.eta_min) == (
        "Pizzas Doces Grandes", "Ponto da Esfiha São Carlos", 75.99, 50)
    assert pizza.loja_id == LOJA
    assert detalhes[(LOJA, pizza.item_id)]["avaliacao"] == 4.7
    assert len(candidatos) == 5
    [args] = sessao.args_de("searchOffers")
    assert args == {"query": "pizza", "resultKind": "ITEM", "pageSize": busca.LIMITE_BUSCA, "userLocation": LOCAL}
    _sem_erros_de_schema(sessao)


async def test_busca_real_usa_preco_promocional():
    cli, _ = _cliente(_busca_real)
    candidatos, _ = await buscar_detalhado(cli, Intencao("ana", consultas=["hambúrguer"]), LOCAL)
    x = next(c for c in candidatos if c.item_nome == "X-Americano")
    assert x.preco == 30.55  # promotionalUnitPrice (unitPrice é 47)


def test_getmerchant_real_le_featured_items():
    itens = busca._itens_do_menu(_resposta("getMerchant"))
    assert [(i["item_nome"], i["preco"], i["categoria"]) for i in itens][:2] == [
        ("Carne", 6.0, "Esfihas Salgadas Abertas"), ("Três Queijos", 8.99, "Esfihas Salgadas Abertas")]
    assert all(i["loja_id"] == LOJA and i["eta_min"] == 50 and i["vertical"] == "RESTAURANT" for i in itens)


def test_loja_fechada_e_descartada():
    r = json.loads(json.dumps(_resposta("searchOffers", "searchOffers pizza ITEM")["results"][0]))
    assert busca._ler_item(r) is not None
    r["merchant"]["isOpen"] = False
    assert busca._ler_item(r) is None


async def test_browseoffers_real_sempre_manda_merchanttype():
    cli, sessao = _cliente(lambda t, a: {"results": []})
    await buscar_detalhado(cli, Intencao("ana", consultas=["qualquer coisa"]), LOCAL)
    [args] = sessao.args_de("browseOffers")
    assert args["merchantType"] == "RESTAURANT" and args["userLocation"] == LOCAL
    _sem_erros_de_schema(sessao)


# ---------- bug 4: conta sem endereço → mensagem clara ----------
async def test_conta_real_sem_endereco_para_com_mensagem_clara():
    assert ler_endereco(_resposta("listAddresses")) is None
    cli, _ = _cliente(lambda t, a: _resposta("listAddresses"))
    resultado = await rodar_match(carregar(), cli, [Desejo("ana", "Ana", "pizza")])
    assert resultado["problema"] == "endereco" and resultado["avisos"] == [MSG_SEM_ENDERECO]


# ---------- bug 5 + diagnóstico com as respostas reais ----------
def _diag_real(com_endereco: bool) -> Callable[[str, dict], Any]:
    carrinho = CarrinhoSuposto()

    def responder(tool: str, args: dict) -> Any:
        if tool == "getUser":
            return _resposta("getUser")
        if tool == "listAddresses":
            return ({"results": [{"addressId": "addr-1", "coordinates": LOCAL}]} if com_endereco
                    else _resposta("listAddresses"))
        if tool == "searchOffers":
            return _busca_real(tool, args)
        if tool == "getMerchant":
            return _resposta("getMerchant")
        if tool == "getItem":
            return _resposta("getItem")
        if tool == "getRecommendations":
            if args.get("contentMode") not in SCHEMAS["getRecommendations"]["properties"]["contentMode"]["enum"]:
                return ErroTool(_amostra("getRecommendations")["chamadas"][0]["erro"])
            return {"results": []}
        if tool == "createCart" and args.get("merchantId") != LOJA:
            return {"error": {"code": "ITEM_NOT_FOUND", "message": "item not found"}}
        return carrinho(tool, args)

    return responder


async def test_diagnostico_real_manda_contentmode_e_nao_marca_ok_no_erro(tmp_path, capsys):
    cli, sessao = _cliente(_diag_real(com_endereco=False))
    resumo = await executar(cli, tmp_path, carrinho=True, local=(-22.02, -47.89))
    [rec] = sessao.args_de("getRecommendations")
    assert rec["contentMode"] == "RECOMMENDED" and not validar("getRecommendations", rec)
    assert "getRecommendations" not in resumo["erros"]
    # sem endereço: createCart falha com o erro real e o diagnóstico registra ok: false (bug 2)
    criados = json.loads((tmp_path / "createCart.json").read_text(encoding="utf-8"))["chamadas"]
    assert criados and all(c["ok"] is False for c in criados)
    assert "MISSING_REQUIRED_FIELDS" in criados[0]["erro"]
    assert all(c["args"]["items"] for c in criados)
    assert resumo["carrinho"]["carrinhos_criados"] == 0


async def test_diagnostico_real_com_endereco_lista_pagamentos_por_merchant(tmp_path, capsys):
    cli, sessao = _cliente(_diag_real(com_endereco=True))
    resumo = await executar(cli, tmp_path, carrinho=True)
    assert resumo["carrinho"]["carrinhos_criados"] == 1  # a 2ª loja dá erro (resposta normal com `error`)
    assert sessao.args_de("listPaymentMethods") == [{"merchantId": LOJA}]
    assert "submitOrder" not in [t for t, _ in sessao.chamadas]
    for tool in ("createCart", "addItemToCart", "listPaymentMethods", "getRecommendations"):
        for args in sessao.args_de(tool):
            assert validar(tool, args) == [], tool
