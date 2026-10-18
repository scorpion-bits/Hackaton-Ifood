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
