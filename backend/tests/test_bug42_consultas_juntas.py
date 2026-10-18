"""Bug 42: com a IA no limite (429), os itens da mesma pessoa vieram com as consultas juntas ("sushi e um
sorvete" → os 2 itens = [sushi, sorvete]) e o Match trocava o sushi por McFlurry. A guarda cai no fallback."""

import pytest

from app.config import carregar
from app.match import interprete
from app.match.interprete import interpretar, interpretar_fallback, validar_resposta_llm
from app.match.modelos import Desejo


def _juntos(*consultas):
    return {"itens": [{"consultas": list(consultas), "verticais": ["RESTAURANT"]} for _ in consultas]}


@pytest.mark.parametrize("texto,consultas", [
    ("sushi e um sorvete", ["sushi", "sorvete"]),
    ("hambúrguer e sorvete", ["hambúrguer", "sorvete"]),
    ("sushi e uma coca", ["sushi", "coca"]),
    ("coxinha e esfiha", ["coxinha", "esfiha"]),
])
def test_itens_com_as_mesmas_consultas_misturadas_caem_no_fallback(texto, consultas):
    assert validar_resposta_llm(_juntos(*consultas), Desejo("ana", "Ana", texto)) is None


def test_fallback_separa_os_itens_que_a_ia_juntou():
    sushi, sorvete = interpretar_fallback(Desejo("ana", "Ana", "sushi e um sorvete"))
    assert "sorvete" not in sushi.consultas and "sorvete" in sorvete.consultas


@pytest.mark.parametrize("dados,texto", [
    ({"itens": [{"consultas": ["coca"]}, {"consultas": ["coca"]}]}, "2 cocas"),  # vira [coca, refrigerante] 2×
    ({"itens": [{"consultas": ["pastel de queijo", "pastel"]}] * 2}, "2 pastéis de queijo"),
    ({"itens": [{"consultas": ["sushi"]}, {"consultas": ["sorvete"]}]}, "sushi e um sorvete"),
    ({"itens": [{"consultas": ["marmita", "prato feito"], "verticais": ["RESTAURANT"]}] * 2}, "2 marmitas"),
])
def test_resposta_boa_ou_item_repetido_de_verdade_continua_valendo(dados, texto):
    validas = validar_resposta_llm(dados, Desejo("ana", "Ana", texto))
    assert validas is not None and len(validas) == len(dados["itens"])


async def test_interpretar_com_a_ia_juntando_usa_o_fallback(monkeypatch):
    async def ia_no_limite(cfg, sistema, usuario, max_tokens=0):
        return _juntos("sushi", "sorvete")
    monkeypatch.setattr(interprete, "completar_json", ia_no_limite)
    sushi, sorvete = await interpretar(carregar(), Desejo("ana", "Ana", "sushi e um sorvete"))
    assert "sushi" in sushi.consultas and "sorvete" not in sushi.consultas
    assert "sorvete" in sorvete.consultas and "sushi" not in sorvete.consultas
