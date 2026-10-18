"""Bugs 12, 13 e 14 (A3) no fallback offline do intérprete."""

import pytest

from app.match.interprete import interpretar_fallback, normalizar
from app.match.modelos import Desejo


def _fb(texto: str, chips: list[str] | None = None):
    return interpretar_fallback(Desejo("p", "P", texto, None, chips or []))


def test_bug12_pizza_pra_dividir_sem_carne_e_so_a_pizza_vegetariana():
    intencoes = _fb("pizza pra dividir, mas eu não como carne")
    assert len(intencoes) == 1
    assert intencoes[0].consultas[-1] == "pizza" and intencoes[0].restricoes == ["vegetariano"]


def test_bug12_doce_qualquer_chega_rapido_e_so_o_doce():
    intencoes = _fb("doce qualquer, chega rápido")
    assert len(intencoes) == 1
    assert "doce" in intencoes[0].consultas and intencoes[0].perfil == "rapido"
    assert "chega" not in intencoes[0].vontades


@pytest.mark.parametrize("texto, restricao", [
    ("nada com glúten até R$ 30", "sem_gluten"),
    ("nada de glúten", "sem_gluten"),
    ("sem glúten", "sem_gluten"),
    ("nada de carne", "vegetariano"),
    ("nada com carne", "vegetariano"),
    ("sem lactose", "sem_lactose"),
    ("nada de lactose", "sem_lactose"),
])
def test_bug13_negacao_vira_restricao_e_nao_vontade(texto, restricao):
    intencoes = _fb(texto)
    assert len(intencoes) == 1
    assert intencoes[0].restricoes == [restricao]
    assert "nada" not in intencoes[0].vontades and "nada" not in intencoes[0].consultas
    assert intencoes[0].consultas  # busca pelo termo da restrição, não fica sem consulta


def test_bug13_orcamento_continua_valendo():
    assert _fb("nada com glúten até R$ 30")[0].orcamento_max == 30


def test_bug13_restricao_junto_com_comida():
    intencoes = _fb("nada de lactose, uma pizza")
    assert len(intencoes) == 1 and intencoes[0].restricoes == ["sem_lactose"]
    assert "pizza" in intencoes[0].consultas


def test_bug14_emoji_de_comida_vira_a_comida():
    intencoes = _fb("🍕🍕")
    assert len(intencoes) == 1 and intencoes[0].consultas == ["pizza"]
    duas = _fb("🍔 e 🍦, até 40")
    assert [i.consultas[0] for i in duas] == ["hambúrguer", "sorvete"]
    assert all(i.orcamento_max == 40 for i in duas)
    assert normalizar("quero 🍣") == "quero  sushi "


def test_ia_doce_ganha_a_consulta_da_categoria():
    # ia-real-3: a IA devolveu só "doce" e a busca não achou nada; "sobremesa" casa com as sorveterias
    from app.match.interprete import validar_resposta_llm
    dados = {"itens": [{"consultas": ["doce"], "verticais": ["RESTAURANT"], "vontades": ["doce"]}]}
    intencoes = validar_resposta_llm(dados, Desejo("p", "P", "doce qualquer, chega rápido", None, []))
    assert intencoes[0].consultas == ["doce", "sobremesa"]
