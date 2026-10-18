"""Fallback determinístico do intérprete: item sem categoria conhecida vira a própria consulta (T17c)."""

import pytest

from app.match.interprete import interpretar_fallback
from app.match.modelos import Desejo


def _fallback(texto: str, chips: list[str] | None = None):
    return interpretar_fallback(Desejo("p", "P", texto, None, chips or []))


@pytest.mark.parametrize("texto, consulta", [
    ("coxinha", "coxinha"),
    ("feijoada completa", "feijoada completa"),
    ("yakisoba", "yakisoba"),
    ("esfiha", "esfiha"),
    ("tapioca", "tapioca"),
    ("pastel de queijo", "pastel de queijo"),
    ("Quero uma tapioca de queijo coalho bem rápida até R$ 20", "tapioca de queijo coalho"),
    ("gostaria de uma coxinha barata", "coxinha"),
    ("Pão de queijo", "pão de queijo"),  # acento mantido para o searchOffers
])
def test_item_sem_categoria_vira_consulta(texto, consulta):
    intencoes = _fallback(texto)
    assert len(intencoes) == 1
    assert intencoes[0].consultas == [consulta]
    assert intencoes[0].verticais == ["RESTAURANT"]


def test_marmita_fit_continua_pela_categoria_conhecida():
    # "fit" é gatilho da categoria poke: há consulta (não cai na busca genérica)
    assert _fallback("marmita fit")[0].consultas


@pytest.mark.parametrize("texto", ["qualquer coisa", "surpreenda-me", "Surpreenda-me!", "tanto faz", "",
                                   "   ", "algo barato", "quero comer algo gostoso", "pode ser qualquer coisa até 30"])
def test_pedido_generico_continua_sem_consulta(texto):
    intencoes = _fallback(texto)
    assert len(intencoes) == 1 and intencoes[0].consultas == []


def test_dois_itens_livres_cada_um_com_sua_consulta_e_orcamento():
    intencoes = _fallback("coxinha e um suco até 30")
    assert [i.participante_id for i in intencoes] == ["p", "p#2"]
    assert intencoes[0].consultas == ["coxinha"]
    assert intencoes[1].consultas[0] == "suco"  # suco tem categoria (bebida)
    assert all(i.orcamento_max == 30 for i in intencoes)

    livres = _fallback("esfiha, tapioca e yakisoba; 60 reais")
    assert [i.consultas for i in livres] == [["esfiha"], ["tapioca"], ["yakisoba"]]
    assert all(i.orcamento_max == 60 for i in livres)


def test_restricao_e_perfil_ficam_fora_da_consulta():
    i = _fallback("coxinha barata sem lactose", ["sem lactose"])[0]
    assert i.restricoes == ["sem_lactose"] and i.perfil == "barato"
    assert i.consultas == ["coxinha sem lactose", "coxinha"]
    assert all("barata" not in c for c in i.consultas)


def test_alternativa_e_complemento():
    alternativa = _fallback("coxinha ou esfiha")
    assert len(alternativa) == 1 and alternativa[0].consultas == ["coxinha", "esfiha"]
    prato = _fallback("feijoada completa com farofa")
    assert len(prato) == 1 and prato[0].consultas == ["feijoada completa"]


def test_consulta_livre_limita_palavras_e_quantidade_repete_slot():
    assert len(_fallback("prato feito de frango com batata doce e salada verde com molho")[0].consultas[0].split()) <= 4
    duas = _fallback("duas coxinhas e um suco")
    assert [i.consultas[0] for i in duas] == ["coxinhas", "coxinhas", "suco"]


def test_categoria_conhecida_nao_muda():
    assert _fallback("pizza")[0].consultas == ["pizza"]
    assert _fallback("pizza com borda recheada")[0].consultas == ["pizza"]
    assert _fallback("hambúrguer sem cebola")[0].consultas == ["hambúrguer"]
    assert _fallback("algo barato e vegetariano")[0].consultas == ["vegetariano"]


# ---------- pedido completo (Trilha A′, etapa 05): bebida pela marca ----------
@pytest.mark.parametrize("texto, marca", [
    ("uma pizza e uma coca", "coca"),
    ("pizza e um guaraná, até 50", "guaraná"),
    ("hambúrguer e uma Pepsi", "pepsi"),
    ("pizza e refri", "refri"),
])
def test_bebida_pela_marca_vira_slot_de_bebida_que_busca_refrigerante(texto, marca):
    intencoes = _fallback(texto)
    assert len(intencoes) == 2
    bebida = intencoes[1]
    assert bebida.participante_id == "p#2"
    assert bebida.consultas[0].lower() == marca
    assert "refrigerante" in bebida.consultas


def test_consulta_da_ia_com_marca_ganha_refrigerante():
    from app.match.interprete import validar_resposta_llm
    dados = {"itens": [{"consultas": ["pizza"]}, {"consultas": ["Coca-Cola"], "vontades": ["coca-cola"]}]}
    intencoes = validar_resposta_llm(dados, Desejo("p", "P", "pizza e uma coca-cola"))
    assert intencoes[1].consultas == ["Coca-Cola", "refrigerante"]
