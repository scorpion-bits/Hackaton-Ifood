"""Regras do pedido (`app/match/regras_pedido.json`, pedido do Thales às 09h11 de 18/10).

1. Mercado, farmácia e pet shop só com o botão "Compras": sem ele, tudo é restaurante e "arroz, feijão e bife" é prato.
2. Os itens de uma mesma pessoa saem do mesmo restaurante sempre que der.
"""

import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.match import regras
from app.match.interprete import interpretar_fallback
from app.match.modelos import Candidato, Desejo, Pesos
from app.match.motor import rodar_match
from app.match.otimizador import otimizar

COMPRAS = [regras.regras()["compras"]["chip"]]


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    resetar_demo()
    yield
    resetar_demo()


async def _rodar(desejos):
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        return await rodar_match(cfg, cli, desejos)


def test_arquivo_de_regras_tem_o_que_o_codigo_usa():
    r = regras.regras()
    assert r["compras"]["chip"] == "modo:compras"
    assert {"GROCERIES", "DRUGSTORE", "PETSTORE"} <= set(r["compras"]["tipos_de_loja"])
    assert 0 < regras.peso_mesma_loja() <= 1 and regras.lojas_mais_baratas_na_busca() >= 1


# ---------- 1. botão "Compras" ----------
@pytest.mark.parametrize("texto", ["arroz, feijão e bife", "arroz e feijão", "quero arroz, feijão e frango"])
def test_sem_compras_arroz_e_feijao_e_prato_de_restaurante(texto):
    [prato] = interpretar_fallback(Desejo("ana", "Ana", texto))
    assert prato.verticais == ["RESTAURANT"]
    assert prato.consultas[0].split()[0] in {"marmita", "prato", "executivo"}


def test_com_compras_arroz_e_feijao_e_lista_de_mercado():
    itens = interpretar_fallback(Desejo("ana", "Ana", "preciso fazer compras: arroz, feijão e detergente",
                                        chips=COMPRAS))
    assert [i.verticais for i in itens] == [["GROCERIES"]] * 3


async def test_sem_compras_o_grupo_pede_prato_e_nao_mercado():
    r = await _rodar([Desejo("ana", "Ana", "arroz, feijão e bife"), Desejo("bia", "Bia", "uma pizza")])
    lojas = {e["loja_id"] for e in r["combinacoes"][0]["escolhas"].values()}
    assert "loja-demo-mercado" not in lojas and "loja-demo-caseira" in lojas


async def test_sem_compras_item_de_farmacia_sai_com_aviso_e_o_resto_segue():
    r = await _rodar([Desejo("ana", "Ana", "dipirona"), Desejo("bia", "Bia", "uma pizza")])
    assert r["combinacoes"], "a Bia continua com o pedido dela"
    assert all(e["loja_id"] != "loja-demo-farmacia" for e in r["combinacoes"][0]["escolhas"].values())
    assert any("Dipirona para Ana é de farmácia: ligue \"Compras\"" in a for a in r["avisos"])


async def test_sem_compras_so_farmacia_nao_monta_nada_e_explica():
    r = await _rodar([Desejo("ana", "Ana", "dipirona e protetor solar")])
    assert r["combinacoes"] == []
    assert any("ligue \"Compras\"" in a for a in r["avisos"])


async def test_com_compras_a_farmacia_continua_funcionando():
    r = await _rodar([Desejo("ana", "Ana", "dipirona e protetor solar", chips=COMPRAS)])
    assert {e["loja_id"] for e in r["combinacoes"][0]["escolhas"].values()} == {"loja-demo-farmacia"}


# ---------- 2. mesma loja ----------
def test_itens_da_mesma_pessoa_preferem_a_mesma_loja_no_grupo(monkeypatch):
    """Grupo: a padaria já entra pela Bia; a batata de lá é R$ 3 mais barata que a McFritas. Sem a regra, a Ana ficava
    com o Big Mac de uma loja e a batata de outra (2 entregas para ela); com a regra, os itens dela ficam juntos."""
    from app.match import otimizador

    def c(slot, loja, item, preco):
        return Candidato(slot, loja, loja, item, item, preco, 30, "RESTAURANT", False, nota=0.9)

    candidatos = {
        "ana": [c("ana", "mc", "Big Mac", 25.0)],
        "ana#2": [c("ana#2", "mc", "McFritas", 12.0), c("ana#2", "padaria", "Batata frita", 9.0)],
        "bia": [c("bia", "padaria", "Pão de queijo", 10.0)],
    }

    def ana_batata(peso: float) -> str:
        monkeypatch.setattr(otimizador, "peso_mesma_loja", lambda: peso)
        melhor = otimizar(candidatos, Pesos(), max_lojas=3, taxas={"mc": 5.0, "padaria": 5.0},
                          pessoa_de={"ana": "ana", "ana#2": "ana", "bia": "bia"})[0]
        return melhor.escolhas["ana#2"].loja_id

    assert ana_batata(0.0) == "padaria"  # sem a regra: itens da Ana em 2 lojas
    assert ana_batata(regras.peso_mesma_loja()) == "mc"  # com a regra (regras_pedido.json): tudo no McDonald's
