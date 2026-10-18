"""T16 / bug 40: refeição (marmita, prato feito) vira 1 item de restaurante, e o chip `onde:X` ("Onde pedir?")
manda todos os itens da pessoa para aquele tipo de loja. MCP de demonstração e LLM mock."""

import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.match.interprete import (aplicar_onde, interpretar_fallback, onde_pedir, pede_refeicao, normalizar,
                                  validar_resposta_llm)
from app.match.modelos import Desejo, Intencao
from app.match.motor import rodar_match

CONSULTAS_MARMITA = ["marmita", "prato feito", "executivo"]


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


def _ler(texto: str, chips: list[str] | None = None) -> list[Intencao]:
    return interpretar_fallback(Desejo("ana", "Ana", texto, None, chips or []))


# ---------- (1) refeição × lista de compras ----------
def test_arroz_feijao_salada_e_guarnicao_e_uma_marmita_de_restaurante():
    [prato] = _ler("arroz, feijão, salada e guarnição")
    assert prato.verticais == ["RESTAURANT"]
    assert prato.consultas == CONSULTAS_MARMITA
    assert {"arroz", "feijão", "salada", "guarnição"} <= set(prato.vontades)


def test_lista_de_compras_com_arroz_e_feijao_continua_no_mercado():
    itens = _ler("preciso fazer compras: arroz, feijão e detergente", ["modo:compras"])  # com o botão Compras
    assert [i.verticais for i in itens] == [["GROCERIES"]] * 3
    assert all(i.consultas != CONSULTAS_MARMITA for i in itens)


@pytest.mark.parametrize("texto", ["1 kg de arroz e feijão com salada", "arroz Camil, feijão e salada",
                                   "arroz, feijão, salada e detergente", "arroz e feijão"])
def test_sinal_de_compra_ou_so_arroz_e_feijao_nao_viram_marmita(texto):
    assert not pede_refeicao(normalizar(texto))
    assert all(i.consultas != CONSULTAS_MARMITA for i in _ler(texto, ["modo:compras"]))  # com o botão Compras


@pytest.mark.parametrize("texto,consultas", [
    ("uma marmita", CONSULTAS_MARMITA),
    ("marmitex", CONSULTAS_MARMITA),
    ("comida caseira", CONSULTAS_MARMITA),
    # T18: a proteína vai na 1ª consulta, com o nome que a pessoa usou (PF → "prato feito")
    ("um PF com bife e ovo", ["prato feito bife", "prato feito", "marmita"]),
    ("prato executivo de frango", ["executivo frango", "executivo", "marmita"]),
    ("arroz, feijão, bife e batata frita", ["marmita bife", "marmita", "prato feito"]),
    ("arroz, feijão, frango grelhado e salada", ["marmita frango grelhado", "marmita", "prato feito"]),
])
def test_frases_de_refeicao_viram_um_item_so(texto, consultas):
    [prato] = _ler(texto)
    assert prato.verticais == ["RESTAURANT"] and prato.consultas == consultas


def test_marmita_e_coca_sao_dois_itens_e_a_proteina_vai_na_busca():
    marmita, coca = _ler("marmita de frango e uma coca")
    assert marmita.consultas == ["marmita frango", "marmita", "prato feito"] and "frango" in marmita.vontades
    assert "refrigerante" in coca.consultas


def test_outro_prato_com_acompanhamento_nao_vira_marmita():
    [burger] = _ler("hambúrguer com acompanhamento")
    assert "hambúrguer" in burger.consultas
    pizza, coca = _ler("pizza de frango e uma coca")
    assert pizza.consultas[0] == "pizza" and "refrigerante" in coca.consultas


def test_duas_marmitas_viram_dois_itens():
    itens = _ler("2 marmitas e uma coca")
    assert [i.consultas == CONSULTAS_MARMITA for i in itens] == [True, True, False]


def test_ia_que_le_o_prato_feito_como_mercado_cai_no_fallback():
    d = Desejo("ana", "Ana", "arroz, feijão, salada e guarnição")
    mercado = {"itens": [{"consultas": ["arroz"], "verticais": ["GROCERIES"]},
                         {"consultas": ["feijão"], "verticais": ["GROCERIES"]}]}
    assert validar_resposta_llm(mercado, d) is None
    certo = {"itens": [{"consultas": ["prato feito"], "verticais": ["RESTAURANT"], "vontades": ["arroz"]}]}
    assert [i.verticais for i in validar_resposta_llm(certo, d)] == [["RESTAURANT"]]
    com_proteina = {"itens": [{"consultas": ["marmita de frango"], "verticais": ["RESTAURANT"]}]}
    assert validar_resposta_llm(com_proteina, Desejo("ana", "Ana", "marmita de frango")) is not None


# ---------- (3) chip "Onde pedir?" ----------
def test_onde_pedir_le_o_chip_e_ignora_valor_desconhecido():
    assert onde_pedir(["barato", "onde:GROCERIES"]) == "GROCERIES"
    assert onde_pedir(["onde:restaurant"]) == "RESTAURANT"
    assert onde_pedir(["onde:SHOPPING", "barato"]) is None  # fora das 4 opções da tela: Match decide
    assert onde_pedir([]) is None


def test_onde_x_manda_todos_os_itens_para_aquele_tipo_de_loja():
    itens = _ler("uma pizza e uma coca", ["onde:GROCERIES"])
    assert [i.verticais for i in itens] == [["GROCERIES"]] * 2
    farmacia = _ler("protetor solar e um shampoo", ["onde:DRUGSTORE"])
    assert all(i.verticais == ["DRUGSTORE"] for i in farmacia)


def test_sem_chip_nada_muda():
    itens = [Intencao("ana", consultas=["pizza"], verticais=["RESTAURANT"])]
    assert aplicar_onde(Desejo("ana", "Ana", "pizza", None, ["barato"]), itens) == itens


def test_onde_restaurante_faz_arroz_e_feijao_virar_prato_feito():
    [prato] = _ler("arroz e feijão", ["onde:RESTAURANT"])
    assert prato.consultas == CONSULTAS_MARMITA and prato.verticais == ["RESTAURANT"]


def test_onde_mercado_desliga_a_marmita():
    itens = _ler("arroz, feijão, salada e guarnição", ["onde:GROCERIES"])
    assert len(itens) == 4 and all(i.verticais == ["GROCERIES"] for i in itens)


def test_onde_vale_tambem_no_caminho_da_ia():
    from app.match.interprete import aplicar_quantidades
    d = Desejo("ana", "Ana", "uma pizza", None, ["onde:GROCERIES"])
    validas = validar_resposta_llm({"itens": [{"consultas": ["pizza"], "verticais": ["RESTAURANT"]}]}, d)
    assert aplicar_onde(d, aplicar_quantidades(d, validas)[0])[0].verticais == ["GROCERIES"]


# ---------- ponta a ponta no demo ----------
async def test_so_eu_marmita_no_demo_sai_da_loja_de_comida_caseira():
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        r = await rodar_match(cfg, cli, [Desejo("ana", "Ana", "arroz, feijão, salada e guarnição")])
    melhor = r["combinacoes"][0]
    [escolha] = melhor["escolhas"].values()
    assert escolha["loja_id"] == "loja-demo-caseira"
    assert escolha["item_id"] in {"cc-marmitex-frango", "cc-pf-bife", "cc-executivo-parmegiana"}


async def test_marmita_de_frango_no_demo_acha_o_marmitex_de_frango():
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        r = await rodar_match(cfg, cli, [Desejo("ana", "Ana", "marmita de frango")])
    [escolha] = r["combinacoes"][0]["escolhas"].values()
    assert escolha["item_id"] in {"cc-marmitex-frango", "cc-executivo-parmegiana"}  # os 2 de frango do demo


async def test_compras_de_mercado_no_demo_nao_vao_para_a_marmita():
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        r = await rodar_match(cfg, cli, [Desejo("ana", "Ana", "preciso fazer compras: arroz, feijão e detergente",
                                                chips=["modo:compras"])])
    lojas = {e["loja_id"] for e in r["combinacoes"][0]["escolhas"].values()}
    assert lojas == {"loja-demo-mercado"}
