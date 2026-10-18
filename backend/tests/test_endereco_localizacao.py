"""Endereço em formatos variados do MCP real, `userLocation` pelo input_schema e trava do `submitOrder` real."""

import asyncio

import pytest

from app.ifood_mcp.cliente import MSG_ENVIO_DESLIGADO, ClienteIFood, ErroMCP, adaptar_args
from app.match.busca import ler_endereco


def test_endereco_formato_da_doc():
    dados = {"addresses": [{"addressId": "a1", "alias": "Casa", "formattedAddress": "Rua X, 1",
                            "coordinates": {"latitude": -22.01, "longitude": -47.89}}]}
    e = ler_endereco(dados)
    assert e["id"] == "a1" and e["latitude"] == -22.01 and e["longitude"] == -47.89


@pytest.mark.parametrize("dados", [
    [{"id": "a1", "streetName": "Rua X", "location": {"lat": "-22.0123", "lng": "-47.8912"}}],
    {"data": {"addresses": [{"id": "a1", "streetName": "Rua X", "geo": {"latitude": -22.0123, "longitude": -47.8912}}]}},
    {"items": [{"addressId": "a1", "address": {"coordinates": {"lat": -22.0123, "lon": -47.8912}}}]},
    {"result": {"content": [{"addressId": "a1", "neighborhood": "Centro", "latitude": "-22,0123",
                             "longitude": "-47,8912"}]}},
])
def test_endereco_formatos_alternativos(dados):
    e = ler_endereco(dados)
    assert e is not None and e["id"] == "a1"
    assert e["latitude"] == pytest.approx(-22.0123) and e["longitude"] == pytest.approx(-47.8912)


def test_endereco_prefere_o_ultimo_usado():
    dados = {"addresses": [{"addressId": "a1", "alias": "Trabalho"},
                           {"addressId": "a2", "alias": "Casa", "usagePattern": {"isLastUsedAddress": True}}]}
    assert ler_endereco(dados)["id"] == "a2"


def test_sem_endereco():
    assert ler_endereco({"addresses": []}) is None
    assert ler_endereco({"user": {"name": "x"}}) is None


SCHEMA_BUSCA = {"type": "object", "required": ["query", "userLocation"],
                "properties": {"query": {}, "resultKind": {}, "limit": {}, "userLocation": {"type": "object"}}}


def test_adaptar_vira_user_location_e_descarta_extras():
    novos = adaptar_args({"query": "pizza", "resultKind": "ITEM", "limit": 5, "latitude": -22.0, "longitude": -47.9},
                         SCHEMA_BUSCA)
    assert novos == {"query": "pizza", "resultKind": "ITEM", "limit": 5,
                     "userLocation": {"latitude": -22.0, "longitude": -47.9}}


def test_adaptar_sem_schema_nao_mexe():
    args = {"merchantId": "m1", "latitude": -22.0, "longitude": -47.9}
    assert adaptar_args(args, None) == args
    assert adaptar_args(args, {"type": "object"}) == args


def test_adaptar_mantem_lat_lng_se_o_schema_pedir():
    schema = {"properties": {"merchantId": {}, "latitude": {}, "longitude": {}}}
    assert adaptar_args({"merchantId": "m1", "latitude": 1.0, "longitude": 2.0}, schema) == {
        "merchantId": "m1", "latitude": 1.0, "longitude": 2.0}


class _SessaoFalsa:
    def __init__(self):
        self.chamadas = []

    async def call_tool(self, tool, args):
        self.chamadas.append((tool, args))
        raise AssertionError("não deveria chamar")


def test_submit_order_real_desligado_por_padrao():
    sessao = _SessaoFalsa()
    cliente = ClienteIFood(sessao, "real", permitir_envio=False)
    with pytest.raises(ErroMCP) as e:
        asyncio.run(cliente.chamar("submitOrder", cartId="c1", userConsent=True))
    assert str(e.value) == MSG_ENVIO_DESLIGADO
    assert sessao.chamadas == [] and cliente.rastro[-1].ok is False
