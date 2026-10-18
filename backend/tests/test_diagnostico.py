"""Diagnóstico do MCP real (03.1b): sanitização sem vazamento, sem máscara em excesso, e robustez do script.

Os payloads de vazamento vêm do QA (`san.py`): imitam respostas plausíveis do iFood com dado pessoal em chaves
que a lista negra antiga não conhecia. Nenhum deles fala com a rede.
"""

import json
import os

import pytest

from app.ifood_mcp import oauth, resetar_demo
from app.ifood_mcp.cliente import MSG_401, ErroMCP
from app.ifood_mcp.diagnostico import (
    AVISO_BUSCA, CONTEXTO_POR_TOOL, LEMBRETE, MASCARA, executar, limpar_erro, principal, sanitizar,
)
from app.match.salas import ErroSala
from app.rotas_match import _erro_do_ifood

SEGREDOS = [
    "Thales", "Hajes", "thales@test.ifood.com.br", "16999991234", "99999-1234", "123.456.789-09", "12345678909",
    "123 456 789 09", "Rua Episcopal", "1234", "Apto 42", "13560-000", "13560000", "-22.01789", "-47.89123",
    "Perto da padaria", "Maria", "Souza", "cust-778899", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc",
    "rt-SEGREDO", "5555", "Visa terminado em 4321", "4321", "Joao", "4111111111111111", "12/30",
]

CASOS = {
    "getUser": {"data": {"user": {
        "id": "cust-778899", "name": "Thales Hajes", "email": "thales@test.ifood.com.br",
        "phone": {"countryCode": "55", "areaCode": "16", "number": "999991234"}, "phoneNumber": "+55 16 99999-1234",
        "taxPayerIdentificationNumber": "123.456.789-09", "tax_payer_identification_number": "12345678909",
        "customerName": "Thales Hajes", "user_name": "Thales", "firstName": "Thales"}}},
    "getUser_plano": {
        "name": "Thales Hajes", "nome": "Thales Hajes", "cpf": "12345678909", "telefone": "16999991234",
        "contactInfo": "ligue (16) 99999-1234", "bio": "Meu cel é 16 99999 1234 e cpf 123 456 789 09",
        "agentHints": {"hello": "Olá, Thales Hajes!"}},
    "listAddresses": {"addresses": [{
        "id": "a1", "streetName": "Rua Episcopal", "streetNumber": "1234", "complement": "Apto 42",
        "reference": "Perto da padaria", "postalCode": "13560-000", "neighborhood": "Centro", "city": "São Carlos",
        "state": "SP", "coordinates": {"latitude": -22.017891, "longitude": -47.891234},
        "label": "Casa da Maria Souza", "fullAddress": "Rua Episcopal, 1234 - Centro",
        "street_name": "Rua Episcopal", "zip_code": "13560000", "number": 1234, "receiverName": "Maria Souza",
        "contacts": [{"phone": "16999991234"}]}]},
    "listPaymentMethods": {"paymentMethods": [{
        "id": "pm1", "brand": "VISA", "lastDigits": "1234", "cardholder": "Thales Hajes", "holder": "Maria Souza",
        "last4Digits": "5555", "lastFourDigits": "5555", "description": "Visa terminado em 4321",
        "alias": "Cartão do Joao", "owner": {"name": "Thales Hajes"}, "billingAddress": "Rua Episcopal, 1234",
        "card": {"holderName": "Thales Hajes", "number": "4111111111111111", "expiration": "12/30"},
        "extra": 4321}]},
    "getCart": {
        "cartId": "c1", "customer": {"name": "Thales Hajes", "phone": "16999991234"},
        "deliveryAddress": {"streetName": "Rua Episcopal", "streetNumber": "1234", "neighborhood": "Centro"},
        "addressText": "Rua Episcopal, 1234", "streetAddress": "Rua Episcopal, 1234", "recipient": "Maria Souza",
        "userLocation": "-22.017891,-47.891234", "location": {"lat": "-22.017891", "lng": "-47.891234"},
        "observations": "Entregar para Maria Souza, tel 16 99999-1234, email thales@test.ifood.com.br",
        "accessToken": "rt-SEGREDO", "auth": {"refresh": "rt-SEGREDO"},
        "authorization": "Bearer rt-SEGREDO-abcdef12345", "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc",
        "selectedPaymentMethod": {"id": "pm1", "type": "CREDIT_CARD", "lastDigits": "5555"},
        "nota": "pago com cartão final 4321", "sessionId": "rt-SEGREDO-2"},
}


@pytest.mark.parametrize("nome", list(CASOS))
def test_nenhum_dado_pessoal_escapa(nome):
    tool = nome.split("_")[0]
    texto = json.dumps(sanitizar(CASOS[nome], CONTEXTO_POR_TOOL.get(tool)), ensure_ascii=False)
    vazou = [s for s in SEGREDOS if s in texto]
    assert not vazou, f"{nome} vazou {vazou}: {texto}"


def test_getuser_mascara_toda_string_e_mantem_a_forma():
    limpo = sanitizar(CASOS["getUser"], "pessoal")
    usuario = limpo["data"]["user"]
    assert set(usuario) == set(CASOS["getUser"]["data"]["user"])
    assert usuario["id"] == MASCARA and usuario["phone"] == {"countryCode": MASCARA, "areaCode": MASCARA,
                                                             "number": MASCARA}


def test_pagamento_lista_branca_mantem_so_o_util():
    forma = sanitizar(CASOS["listPaymentMethods"], "pagamento")["paymentMethods"][0]
    assert forma["id"] == "pm1" and forma["brand"] == "VISA"
    assert forma["description"] == f"Visa {MASCARA}"
    for chave in ("lastDigits", "cardholder", "holder", "alias", "extra", "billingAddress"):
        assert forma[chave] == MASCARA, chave
    assert forma["card"] == {"holderName": MASCARA, "number": MASCARA, "expiration": MASCARA}
    # A mesma regra vale para listas de pagamento dentro de outras tools.
    fora = sanitizar({"paymentMethods": [{"id": "pm-2", "name": "Pix", "type": "PIX", "nickname": "Joao"}]})
    assert fora["paymentMethods"][0] == {"id": "pm-2", "name": "Pix", "type": "PIX", "nickname": MASCARA}


def test_coordenadas_arredondadas_inclusive_texto_lat_lng():
    limpo = sanitizar(CASOS["getCart"])
    assert limpo["userLocation"] == "-22.02,-47.89"
    assert limpo["location"] == {"lat": -22.02, "lng": -47.89}
    assert limpo["deliveryAddress"]["neighborhood"] == "Centro"
    assert sanitizar({"texto": "estou em -22.017891, -47.891234"})["texto"] == "estou em -22.02,-47.89"


def test_regex_de_texto_livre_final_terminado_e_cpf_com_espacos():
    for frase in ("cartão terminado em 4321", "final 4321", "termina 4321", "Cartão terminada em 4321",
                  "cpf 123 456 789 09", "cpf 123.456.789-09", "cpf 123-456-789-09"):
        assert "4321" not in limpar_erro(frase) and "789" not in limpar_erro(frase), frase


def test_mensagem_de_erro_passa_pela_mesma_limpeza():
    msg = ('Endereço inválido: {"streetName": "Rua Episcopal", "receiverName": "Maria Souza", "city": "São Carlos"}'
           " (contato thales@test.ifood.com.br)")
    limpo = limpar_erro(msg)
    assert "Rua Episcopal" not in limpo and "Maria" not in limpo and "thales@" not in limpo
    assert "São Carlos" in limpo and limpo.startswith("Endereço inválido:")


# ---------- sem máscara em excesso (QA over.py) ----------
LOJA = {
    "merchantId": "550e8400-e29b-41d4-a716-446655440000", "id": "1234567890", "itemId": "12345678901",
    "createdAt": "2026-10-18T12:34:56Z", "epoch": "1760745600", "timestamp": "1760745600123",
    "price": "R$ 39,90", "number": "42", "orderNumber": "1234-5678", "name": "Pizza Calabresa",
    "merchantName": "Forno da Praça", "description": "Serve 2 pessoas.",
    "merchant": {"name": "Forno da Praça", "address": {"streetName": "Av São Carlos", "city": "São Carlos"}},
    "items": [{"itemId": "abc", "name": "Coca 2L", "unitPrice": 12.5, "quantity": 1, "productName": "Coca"}],
    "deliveryMethods": [{"id": "DEFAULT", "mode": "DELIVERY", "fee": 8.99, "title": "Padrão", "eta": "30-40 min"}],
    "deliveryFee": 8.99, "subtotal": 59.9, "total": 68.89, "discount": 0.0, "cartId": "c-1",
}


def test_ids_precos_e_taxas_continuam_legiveis():
    limpo = sanitizar(LOJA)
    for chave in ("merchantId", "id", "itemId", "createdAt", "epoch", "timestamp", "price", "number",
                  "orderNumber", "name", "merchantName", "description", "items", "deliveryMethods",
                  "deliveryFee", "subtotal", "total", "discount", "cartId"):
        assert limpo[chave] == LOJA[chave], chave
    assert limpo["merchant"]["name"] == "Forno da Praça"
    assert limpo["merchant"]["address"] == {"streetName": MASCARA, "city": "São Carlos"}


def test_number_so_e_mascarado_em_endereco_pagamento_e_usuario():
    assert sanitizar({"number": "42"})["number"] == "42"
    assert sanitizar({"address": {"number": 42}})["address"]["number"] == MASCARA
    assert sanitizar({"card": {"number": "4111"}})["card"]["number"] == MASCARA
    assert sanitizar({"number": "42"}, "pessoal")["number"] == MASCARA


# ---------- robustez do script ----------
class ClienteFalso:
    """Imita o ClienteIFood: list_tools pode falhar; searchOffers volta vazio; guarda os argumentos."""

    def __init__(self, falhar_list_tools=False):
        self.falhar_list_tools = falhar_list_tools
        self.chamadas: list[tuple[str, dict]] = []

    async def listar_tools(self):
        if self.falhar_list_tools:
            raise ExceptionGroup("grupo", [RuntimeError("caiu: thales@test.ifood.com.br")])
        return [{"name": "searchOffers", "input_schema": {"properties": {"query": {}, "limit": {}}}}]

    async def chamar(self, tool, **args):
        self.chamadas.append((tool, args))
        if tool == "getUser":
            raise ErroMCP('falhou para {"name": "Thales Hajes"}')
        return {"results": []}


async def test_buscas_vazias_avisam_e_args_busca_e_mesclado(tmp_path, capsys):
    cli = ClienteFalso()
    resumo = await executar(cli, tmp_path, args_busca={"sortBy": "RELEVANCE", "limit": 9})
    buscas = [a for t, a in cli.chamadas if t == "searchOffers"]
    assert len(buscas) == 6 and all(a["sortBy"] == "RELEVANCE" and a["limit"] == 9 for a in buscas)
    assert "resultKind" not in buscas[0]  # o resto continua filtrado pelo input_schema
    assert AVISO_BUSCA in resumo["avisos"] and AVISO_BUSCA in capsys.readouterr().out
    usuario = (tmp_path / "getUser.json").read_text(encoding="utf-8")
    assert "Thales" not in usuario


async def test_list_tools_com_erro_nao_derruba_o_diagnostico(tmp_path):
    resumo = await executar(ClienteFalso(falhar_list_tools=True), tmp_path)
    assert resumo["total_tools"] == 0 and any("list_tools falhou (RuntimeError)" in a for a in resumo["avisos"])
    assert "thales@" not in json.dumps(resumo)


async def test_principal_sem_login_sai_com_1_sem_traceback(tmp_path, capsys):
    assert await principal(["--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("ERRO: ErroMCP: ") and oauth.MSG_SEM_TOKEN in err and "Traceback" not in err


async def test_principal_captura_exceptiongroup(tmp_path, capsys, monkeypatch):
    from app.ifood_mcp import diagnostico

    async def explode(*_a, **_k):
        raise ExceptionGroup("tarefas", [ValueError("cpf 123.456.789-09")])

    monkeypatch.setattr(diagnostico, "executar", explode)
    assert await principal(["--demo", "--saida", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("ERRO: ValueError: ") and "123.456" not in err


async def test_principal_demo_imprime_o_lembrete(tmp_path, capsys):
    resetar_demo()
    assert await principal(["--demo", "--carrinho", "--saida", str(tmp_path)]) == 0
    assert LEMBRETE in capsys.readouterr().out
    pagamentos = json.loads((tmp_path / "listPaymentMethods.json").read_text(encoding="utf-8"))
    assert {m["type"] for m in pagamentos["chamadas"][0]["resposta"]["methods"]} >= {"PIX", "CREDIT_CARD"}


# ---------- erros de login na API da sala (QA #4) ----------
def _embrulhado(original: Exception) -> ErroMCP:
    try:
        try:
            raise original
        except oauth.ErroOAuth as e:
            raise ErroMCP(str(e)) from None  # igual ao cliente._token_ou_erro
    except ErroMCP as final:
        return final


@pytest.mark.parametrize("erro", [
    _embrulhado(oauth.SemToken()),
    _embrulhado(oauth.SemToken(oauth.MSG_SESSAO_EXPIRADA)),
    _embrulhado(oauth.SemCredenciais()),
    ErroMCP(MSG_401),
    ExceptionGroup("g", [ErroMCP(MSG_401)]),
    oauth.SemCredenciais(),
])
def test_erro_de_login_vira_401_sem_prefixo(erro):
    traduzido = _erro_do_ifood(erro)
    assert isinstance(traduzido, ErroSala) and traduzido.status == 401
    assert "O iFood respondeu com erro" not in traduzido.mensagem


def test_outro_erro_do_mcp_continua_502():
    traduzido = _erro_do_ifood(ErroMCP("Loja fechada."))
    assert traduzido.status == 502 and traduzido.mensagem == "O iFood respondeu com erro: Loja fechada."


# ---------- arquivo de tokens preso no Windows (QA #7) ----------
def _tokens():
    return oauth.Tokens(access_token="A-SECRETO", refresh_token="R-SECRETO", expires_at=9e9)


def test_salvar_tokens_tenta_de_novo_uma_vez(monkeypatch):
    original, chamadas = os.replace, []

    def replace_instavel(origem, destino):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise PermissionError("em uso")
        return original(origem, destino)

    monkeypatch.setattr(oauth.os, "replace", replace_instavel)
    monkeypatch.setattr(oauth.time, "sleep", lambda _s: None)
    oauth.salvar_tokens(_tokens())
    assert len(chamadas) == 2 and oauth.carregar_tokens().access_token == "A-SECRETO"


def test_salvar_tokens_preso_vira_erro_legivel(monkeypatch):
    def sempre_preso(_o, _d):
        raise PermissionError("em uso")

    monkeypatch.setattr(oauth.os, "replace", sempre_preso)
    monkeypatch.setattr(oauth.time, "sleep", lambda _s: None)
    with pytest.raises(oauth.ErroOAuth) as info:
        oauth.salvar_tokens(_tokens())
    assert "Feche o arquivo .tokens_ifood.json" in str(info.value) and "SECRETO" not in str(info.value)
    assert not list(oauth.ARQUIVO_TOKENS.parent.glob("*.tmp"))


# ---------- payloads adversariais do QA (recriados): aninhados, caixa trocada, camelCase/snake_case ----------
ADVERSARIOS = {
    "pedidos_aninhados": {"Orders": [
        {"CUSTOMER_INFO": {"Full_Name": "Thales Hajes", "E-Mail": "thales@test.ifood.com.br"}},
        {"delivery": {"Driver": {"Name": "Joao Souza", "PHONE_NUMBER": "16999991234"}}},
        {"buyerData": [{"Document_Number": "123.456.789-09"}, {"TAX_PAYER_IDENTIFICATION_NUMBER": "12345678909"}]},
        {"customerDocument": "12.345.678/0001-90", "person": {"cpf": "123 456 789 09"}},
    ]},
    "segredos_em_chaves": {
        "Authorization": "Bearer rt-SEGREDO-abcdef12345", "X-Session-Id": "rt-SEGREDO-2", "setCookie": "sid=rt-SEGREDO",
        "client_secret": "rt-SEGREDO", "idToken": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc", "REFRESH_TOKEN": "rt-SEGREDO",
        "meta": {"sessionCookie": "rt-SEGREDO", "nested": [{"apiToken": "rt-SEGREDO"}]},
    },
    "texto_livre": {"message": (
        "Olá! Entrega em Rua Episcopal, 1234, Apto 42, CEP 13560-000. CNPJ 12.345.678/0001-90. "
        "Cartões: Mastercard 4321, VISA •••• 5555, 4111 1111 1111 1111, final 4321. cpf 12345678909, "
        "tel (16) 99999-1234, e-mail thales@test.ifood.com.br, posição -22.017891"),
        "agentHints": {"tip": "Pague com o Visa terminado em 4321 e entregue na Av. São Carlos 2000 apto 42"},
        "debug": "token=rt-SEGREDO-123456 secret: rt-SEGREDO-999"},
    "pagamentos_snake": {"payment_methods": [{
        "id": "pm1", "card_brand": "VISA", "masked_number": "**** 4321", "display": "Visa terminado em 4321",
        "holder_name": "Thales Hajes", "Description": "Mastercard final 4321", "billing": {"zip": "13560-000"}}],
        "selected_card": {"last_four": "4321", "brand": "ELO"}},
    "endereco_fora_de_objeto": {
        "shippingInfo": {"street": "Rua Episcopal", "houseNumber": "1234", "complemento": "Apto 42",
                         "Zip_Code": "13560-000", "neighborhood": "Centro"},
        "position": [-22.017891, -47.891234], "geo_point": {"Lat": "-22.017891", "Lng": "-47.891234"},
        "deliveryAddressLine": "Rua Episcopal, 1234", "referencePoint": "Perto da padaria"},
}


@pytest.mark.parametrize("nome", list(ADVERSARIOS))
def test_payload_adversarial_nao_vaza(nome):
    texto = json.dumps(sanitizar(ADVERSARIOS[nome]), ensure_ascii=False)
    vazou = [s for s in SEGREDOS + ["rt-SEGREDO", "12.345.678/0001-90", "2000", "-22.0178"] if s in texto]
    assert not vazou, f"{nome} vazou {vazou}: {texto}"


def test_texto_livre_mantem_o_que_nao_e_pessoal():
    limpo = sanitizar(ADVERSARIOS["texto_livre"])
    assert limpo["message"].startswith("Olá! Entrega em ***") and "posição -22.02" in limpo["message"]
    assert "Mastercard ***" in limpo["message"]
    assert sanitizar({"name": "Forno da Praça Pizzaria", "description": "Pizza 2 sabores, serve 2"}) == {
        "name": "Forno da Praça Pizzaria", "description": "Pizza 2 sabores, serve 2"}
    assert sanitizar(ADVERSARIOS["endereco_fora_de_objeto"])["shippingInfo"]["neighborhood"] == "Centro"


async def test_nome_do_getuser_some_de_todas_as_amostras(tmp_path):
    """Texto pessoal visto no getUser/listAddresses é apagado também onde nenhuma regra pegaria."""

    class Cliente:
        async def listar_tools(self):
            return []

        async def chamar(self, tool, **args):
            return {
                "getUser": {"name": "Thales Hajes", "email": "thales@test.ifood.com.br"},
                "listAddresses": {"addresses": [{"id": "a1", "streetName": "Rua Episcopal",
                                                 "coordinates": {"latitude": -22.017891, "longitude": -47.891234}}]},
            }.get(tool, {"results": [{"merchantId": "m1", "itemId": "i1", "name": "Pizza"}],
                         "agentHints": {"greeting": "Pedido do thales para a casa em Rua Episcopal"},
                         "texto": "Olá Hajes"})

    await executar(Cliente(), tmp_path)
    for arquivo in tmp_path.glob("*.json"):
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "Thales" not in conteudo and "thales" not in conteudo and "Hajes" not in conteudo, arquivo.name
        assert "Episcopal" not in conteudo and "-22.0178" not in conteudo, arquivo.name
    busca = json.loads((tmp_path / "searchOffers.json").read_text(encoding="utf-8"))
    assert busca["chamadas"][0]["resposta"]["results"][0]["name"] == "Pizza"


# ---------- MCP falso que EXIGE userLocation (formato do MCP real visto pela equipe em 18/10) ----------
MSG_USER_LOCATION = ("Error: `userLocation` is required and must be a JSON object with numeric `latitude` and "
                     "`longitude`. Ask the user for their location and try again.")


def _servidor_exigente(chamadas: list, enderecos: dict, obrigatorio: bool = False):
    """Imita o MCP real: searchOffers/getRecommendations/getMerchant/getItem/createCart exigem `userLocation`
    (objeto) e recusam latitude/longitude soltos; createCart não tem addressId no schema.
    `obrigatorio`: userLocation também aparece em `required` no schema de searchOffers/getRecommendations."""
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError

    mcp = MCPServer("ifood-real-falso")

    def conferir(nome: str, userLocation: dict | None, latitude=None, longitude=None, **outros) -> None:
        chamadas.append((nome, {"userLocation": userLocation, "latitude": latitude, "longitude": longitude}
                         | outros))
        if latitude is not None or longitude is not None:
            raise ToolError("latitude/longitude soltos não são aceitos; use userLocation.")
        ok = isinstance(userLocation, dict) and all(
            isinstance(userLocation.get(c), (int, float)) for c in ("latitude", "longitude"))
        if not ok:
            raise ToolError(MSG_USER_LOCATION)

    @mcp.tool(name="getUser")
    def get_user() -> dict:
        chamadas.append(("getUser", {}))
        return {"user": {"name": "Thales Hajes", "email": "thales@test.ifood.com.br"}}

    @mcp.tool(name="listAddresses")
    def list_addresses() -> dict:
        chamadas.append(("listAddresses", {}))
        return enderecos

    def buscar(query, userLocation, resultKind, latitude, longitude) -> dict:
        conferir("searchOffers", userLocation, latitude, longitude, query=query, resultKind=resultKind)
        return {"results": [{"merchantId": "m1", "itemId": "i1", "name": "Pizza", "price": 39.9},
                            {"merchantId": "m2", "itemId": "i2", "name": "Sorvete", "price": 12.0}]}

    if obrigatorio:
        @mcp.tool(name="searchOffers")
        def search_offers(query: str, userLocation: dict, resultKind: str = "MERCHANT", limit: int = 10) -> dict:
            return buscar(query, userLocation, resultKind, None, None)

        @mcp.tool(name="getRecommendations")
        def get_recommendations(userLocation: dict) -> dict:
            conferir("getRecommendations", userLocation)
            return {"results": []}
    else:
        @mcp.tool(name="searchOffers")
        def search_offers_opcional(query: str, userLocation: dict | None = None, resultKind: str = "MERCHANT",
                                   limit: int = 10, latitude: float | None = None,
                                   longitude: float | None = None) -> dict:
            return buscar(query, userLocation, resultKind, latitude, longitude)

        @mcp.tool(name="getRecommendations")
        def get_recommendations_opcional(userLocation: dict | None = None) -> dict:
            conferir("getRecommendations", userLocation)
            return {"results": []}

    @mcp.tool(name="getMerchant")
    def get_merchant(merchantId: str, userLocation: dict | None = None) -> dict:
        conferir("getMerchant", userLocation, merchantId=merchantId)
        return {"merchantId": merchantId, "name": "Loja"}

    @mcp.tool(name="getItem")
    def get_item(merchantId: str, itemId: str, userLocation: dict | None = None) -> dict:
        conferir("getItem", userLocation, merchantId=merchantId, itemId=itemId)
        return {"itemId": itemId, "price": 39.9}

    @mcp.tool(name="createCart")
    def create_cart(merchantId: str, userLocation: dict | None = None) -> dict:
        conferir("createCart", userLocation, merchantId=merchantId)
        return {"cartId": f"c-{merchantId}"}

    @mcp.tool(name="addItemToCart")
    def add_item(cartId: str, itemId: str, quantity: int = 1) -> dict:
        chamadas.append(("addItemToCart", {"cartId": cartId}))
        return {"cartId": cartId, "total": 39.9}

    @mcp.tool(name="getCartDeliveryMethods")
    def delivery(cartId: str) -> dict:
        chamadas.append(("getCartDeliveryMethods", {}))
        return {"methods": [{"id": "DEFAULT", "fee": 5.0}]}

    @mcp.tool(name="listPaymentMethods")
    def payments(cartId: str) -> dict:
        chamadas.append(("listPaymentMethods", {}))
        return {"methods": [{"id": "pm1", "type": "PIX"}]}

    @mcp.tool(name="getCart")
    def get_cart(cartId: str) -> dict:
        chamadas.append(("getCart", {}))
        return {"cartId": cartId, "total": 44.9}

    @mcp.tool(name="submitOrder")
    def submit(cartId: str) -> dict:
        chamadas.append(("submitOrder", {}))
        raise ToolError("o diagnóstico nunca deveria chamar submitOrder")

    return mcp


ENDERECO_REAL_ANINHADO = {"data": {"addresses": [{
    "id": "addr-1", "street": "Rua Episcopal", "streetNumber": "1234",
    "geo": {"coordinates": {"lat": "-22.017891", "lng": "-47.891234"}}}]}}


async def _rodar_exigente(tmp_path, enderecos=ENDERECO_REAL_ANINHADO, obrigatorio=False, **kwargs):
    from mcp import Client

    from app.ifood_mcp.cliente import ClienteIFood

    chamadas: list = []
    async with Client(_servidor_exigente(chamadas, enderecos, obrigatorio)) as sessao:
        resumo = await executar(ClienteIFood(sessao, "real"), tmp_path, carrinho=True, **kwargs)
    return resumo, chamadas


async def test_user_location_vai_como_objeto_pelo_schema(tmp_path, capsys):
    resumo, chamadas = await _rodar_exigente(tmp_path)
    buscas = [a for t, a in chamadas if t == "searchOffers"]
    assert len(buscas) == 6
    for args in buscas:  # valor real em memória (sem arredondar) e sem latitude/longitude soltos
        assert args["userLocation"] == {"latitude": -22.017891, "longitude": -47.891234}
        assert args["latitude"] is None and args["longitude"] is None
    for tool in ("getMerchant", "getItem", "getRecommendations", "createCart"):
        assert any(t == tool and a["userLocation"] for t, a in chamadas), tool
    assert "addressId" not in json.dumps([a for t, a in chamadas if t == "createCart"])  # fora do schema
    assert resumo["erros"] == {} and resumo["carrinho"]["dois_carrinhos_abertos"] is True
    assert "submitOrder" not in [t for t, _ in chamadas]
    # Resumo mostra os obrigatórios; as amostras gravam a coordenada arredondada.
    assert {"query"} <= set(resumo["schemas"]["searchOffers"]["obrigatorios"])
    assert "userLocation" in resumo["schemas"]["searchOffers"]["opcionais"] + resumo["schemas"]["searchOffers"]["obrigatorios"]
    assert "Argumentos (input_schema)" not in capsys.readouterr().out  # o resumo impresso é do principal
    gravado = (tmp_path / "searchOffers.json").read_text(encoding="utf-8")
    assert '"latitude": -22.02' in gravado and "-22.0178" not in gravado


async def test_obrigatorio_no_schema_tambem_vai_como_objeto(tmp_path):
    resumo, chamadas = await _rodar_exigente(tmp_path, obrigatorio=True)
    assert resumo["schemas"]["searchOffers"]["obrigatorios"] == ["query", "userLocation"]
    assert resumo["erros"] == {} and len([t for t, _ in chamadas if t == "searchOffers"]) == 6


async def test_sem_coordenadas_avisa_e_pula_o_que_exige_local(tmp_path):
    resumo, chamadas = await _rodar_exigente(tmp_path, enderecos={"addresses": [{"id": "a1", "street": "X"}]},
                                             obrigatorio=True)
    assert not [t for t, _ in chamadas if t in ("searchOffers", "getRecommendations")]
    assert any("Não achei latitude/longitude" in a and "--lat" in a for a in resumo["avisos"])
    assert any("pulada" in a for a in resumo["avisos"]) and resumo["localizacao_encontrada"] is False


async def test_lat_lng_da_linha_de_comando_tem_prioridade(tmp_path):
    _, chamadas = await _rodar_exigente(tmp_path, local=(-22.5, -47.5))
    assert {json.dumps(a["userLocation"]) for t, a in chamadas if t == "searchOffers"} == {
        json.dumps({"latitude": -22.5, "longitude": -47.5})}


async def test_erro_de_user_location_aparece_legivel_e_avisa(tmp_path):
    """Sem coordenada e com userLocation opcional no schema: o erro do servidor fica registrado e o aviso
    de busca com erro sugere --args-busca/--lat/--lng."""
    resumo, _ = await _rodar_exigente(tmp_path, enderecos={"addresses": []})
    assert "userLocation" in resumo["erros"]["searchOffers"][0]
    assert any("Não achei latitude/longitude" in a for a in resumo["avisos"])
    assert any("--args-busca" in a and "--lat" in a for a in resumo["avisos"])


def test_achar_coordenadas_em_formatos_variados():
    from app.ifood_mcp.diagnostico import achar_coordenadas, escolher_endereco

    assert achar_coordenadas({"coordinates": {"latitude": -22.1, "longitude": -47.2}}) == (-22.1, -47.2)
    assert achar_coordenadas({"location": {"Lat": "-22,1", "LNG": "-47.2"}}) == (-22.1, -47.2)
    assert achar_coordenadas({"geo": {"location": "-22.1, -47.2"}}) == (-22.1, -47.2)
    assert achar_coordenadas({"geometry": {"coordinates": [-47.2, -22.1]}}) == (-22.1, -47.2)  # GeoJSON
    assert achar_coordenadas({"lat": 0, "lng": 0}) is None and achar_coordenadas({"lat": "x"}) is None
    escolhido = escolher_endereco({"result": {"addresses": [
        {"id": "sem"}, {"id": "a", "lat": 1, "lng": 1},
        {"id": "b", "lat": 2, "lng": 2, "usagePattern": {"isLastUsedAddress": True}}]}})
    assert escolhido["id"] == "b"


async def test_principal_imprime_schemas_e_valida_lat_lng(tmp_path, capsys):
    resetar_demo()
    assert await principal(["--demo", "--lat", "-22.02", "--lng", "-47.89", "--saida", str(tmp_path)]) == 0
    saida = capsys.readouterr().out
    assert "Argumentos (input_schema):" in saida and "searchOffers: obrigatórios: query" in saida
    with pytest.raises(SystemExit):
        await principal(["--demo", "--lat", "-22.02"])
    with pytest.raises(SystemExit):
        await principal(["--demo", "--lat", "-122", "--lng", "-47"])
    assert "--lat e --lng juntos" in capsys.readouterr().err


# ---------- API: login/token → 401 legível; sem token na mensagem ----------
def test_renovacao_recusada_e_401_do_meio_da_sessao_viram_401():
    from app.match import checkout

    sessao = ErroMCP("Falha ao chamar getCart: o iFood recusou o login (401). Conecte o iFood de novo.")
    assert _erro_do_ifood(sessao).status == 401
    assert _erro_do_ifood(sessao).mensagem == oauth.MSG_SESSAO_EXPIRADA
    recusado = _embrulhado(oauth.ErroOAuthToken("invalid_client", "", 401))
    assert _erro_do_ifood(recusado).status == 401
    try:
        raise checkout.ErroCheckout("m1", f"Não deu para montar o carrinho: {sessao}") from sessao
    except checkout.ErroCheckout as e:
        assert _erro_do_ifood(e).status == 401


def test_sem_conexao_com_o_login_e_502_sem_prefixo_e_sem_token():
    falha = _embrulhado(oauth.SemConexao("Não consegui falar com o login do iFood (ConnectError)."))
    traduzido = _erro_do_ifood(falha)
    assert traduzido.status == 502 and traduzido.mensagem.startswith("Não consegui falar")
    vazado = _erro_do_ifood(ErroMCP("falhou com Bearer abcdef.ghijkl.123456 e access_token=XYZ-123456789"))
    assert "abcdef" not in vazado.mensagem and "XYZ-123" not in vazado.mensagem and vazado.status == 502
    generico = _erro_do_ifood(RuntimeError("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc"))
    assert "eyJ" not in generico.mensagem and "RuntimeError" in generico.mensagem


def test_args_busca_aceita_json_pares_e_arquivo(tmp_path):
    import argparse

    from app.ifood_mcp.diagnostico import _json_objeto

    assert _json_objeto('{"sortBy": "relevance", "limit": 10}') == {"sortBy": "relevance", "limit": 10}
    assert _json_objeto("{sortBy: relevance, limit: 10}") == {"sortBy": "relevance", "limit": 10}  # PowerShell 5
    assert _json_objeto("sortBy=relevance,limit=10") == {"sortBy": "relevance", "limit": 10}
    arquivo = tmp_path / "args.json"
    arquivo.write_text('{"refinements": {"maxPrice": 50}}', encoding="utf-8")
    assert _json_objeto(f"@{arquivo}") == {"refinements": {"maxPrice": 50}}
    with pytest.raises(argparse.ArgumentTypeError):
        _json_objeto("[1, 2]")


async def test_schema_sem_user_location_mas_servidor_pede_repete_uma_vez(tmp_path):
    class Cliente:
        def __init__(self):
            self.chamadas = []

        async def listar_tools(self):
            schema = {"properties": {"query": {}, "latitude": {}, "longitude": {}}, "required": ["query"]}
            return [{"name": "searchOffers", "input_schema": schema}]

        async def chamar(self, tool, **args):
            self.chamadas.append((tool, args))
            if tool == "listAddresses":
                return {"addresses": [{"id": "a1", "lat": -22.017891, "lng": -47.891234}]}
            if tool == "searchOffers" and "userLocation" not in args:
                raise ErroMCP(MSG_USER_LOCATION)
            return {"results": []}

    cli = Cliente()
    resumo = await executar(cli, tmp_path)
    buscas = [a for t, a in cli.chamadas if t == "searchOffers"]
    assert len(buscas) == 12  # 6 buscas × (1ª com latitude/longitude soltos + 1 repetição)
    assert buscas[0]["latitude"] == -22.017891 and "userLocation" not in buscas[0]
    assert buscas[1] == {"query": "pizza", "userLocation": {"latitude": -22.017891, "longitude": -47.891234}}
    assert AVISO_BUSCA in resumo["avisos"]  # repetições deram ok, mas vazias
