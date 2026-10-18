"""Bug 21: erro numa loja não derruba o `escolher` inteiro.

A loja que falhou (createCart MERCH-007, getCart INTERNAL...) sai do pedido; as outras seguem, com um aviso legível
de quem ficou sem o quê. Todas falharam → o 502 legível de sempre. Checkout pelo protocolo MCP (servidor de
demonstração), com um embrulho que faz o iFood "responder erro" numa loja escolhida.
"""

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app import rotas_match
from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.ifood_mcp.cliente import MSG_401, ErroMCP
from app.main import app
from app.match import checkout
from app.match.acerto import centavos
from app.match.checkout import ErroCheckout, montar_carrinhos

from test_checkout import ENDERECO, _cand, _combinacao, _combinacao_roteiro
from test_salas import Sala, soma_carrinhos, soma_partes

MERCH_007 = ("Could not retrieve merchant (código MERCH-007)", "MERCH-007")
INTERNAL = ("Erro no upstream service (código INTERNAL)", "INTERNAL")


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    monkeypatch.setattr(checkout, "ESPERA_NOVA_TENTATIVA_S", 0)  # a nova tentativa não atrasa os testes
    resetar_demo()
    yield
    resetar_demo()


class IFoodComFalha:
    """Embrulha o cliente MCP: `tool` falha para as lojas em `lojas` (`vezes` = quantas chamadas falham; None = todas).

    createCart é casado pelo merchantId; as tools por cartId, pelo carrinho que aquela loja abriu."""

    def __init__(self, cliente, tool: str, lojas: set[str], erro=MERCH_007, vezes: int | None = None):
        self._cliente = cliente
        self.tool, self.lojas, self.erro, self.vezes = tool, lojas, erro, vezes
        self.carrinho_da_loja: dict[str, str] = {}
        self.falhas = 0
        self.chamadas: list[str] = []

    def __getattr__(self, nome):
        return getattr(self._cliente, nome)

    async def chamar(self, tool: str, **args):
        self.chamadas.append(tool)
        loja = args.get("merchantId") or next((l for l, c in self.carrinho_da_loja.items()
                                                if c == args.get("cartId")), None)
        if tool == self.tool and loja in self.lojas and (self.vezes is None or self.falhas < self.vezes):
            self.falhas += 1
            raise ErroMCP(self.erro[0], codigo=self.erro[1])
        resp = await self._cliente.chamar(tool, **args)
        if tool == "createCart":
            self.carrinho_da_loja[args["merchantId"]] = checkout._ler_cart_id(resp)
        return resp


# ---------- checkout ----------
async def test_createcart_falha_numa_loja_e_a_outra_segue():
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "createCart", {"loja-demo-sorvete"})
        falhas: list[dict] = []
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO, falhas=falhas)
    assert [c["loja_id"] for c in carrinhos] == ["loja-demo-japones"]
    assert cli.falhas == 1  # MERCH-007 não é transitório: nenhuma nova tentativa
    [f] = falhas
    assert f["loja_id"] == "loja-demo-sorvete" and f["codigo_ifood"] == "MERCH-007"
    assert f["participantes"] == ["thales", "zenon"]  # thales#2 → thales
    assert {i["slot"] for i in f["itens"]} == {"thales#2", "zenon"}
    assert "Could not retrieve merchant" in f["erro"]


async def test_getcart_internal_duas_vezes_tira_a_loja():
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "getCart", {"loja-demo-japones"}, erro=INTERNAL)
        falhas: list[dict] = []
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO, falhas=falhas)
    assert [c["loja_id"] for c in carrinhos] == ["loja-demo-sorvete"]
    assert cli.falhas == 2  # 1ª chamada + 1 nova tentativa
    assert [f["codigo_ifood"] for f in falhas] == ["INTERNAL"]


async def test_getcart_internal_uma_vez_passa_na_nova_tentativa():
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "getCart", {"loja-demo-japones"}, erro=INTERNAL, vezes=1)
        falhas: list[dict] = []
        carrinhos = await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO, falhas=falhas)
    assert [c["loja_id"] for c in carrinhos] == ["loja-demo-japones", "loja-demo-sorvete"]
    assert falhas == [] and cli.falhas == 1


async def test_todas_as_lojas_falham_levanta_o_erro_de_sempre():
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "createCart", {"loja-demo-japones", "loja-demo-sorvete"})
        falhas: list[dict] = []
        with pytest.raises(ErroCheckout) as erro:
            await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO, falhas=falhas)
    assert "Não deu para montar o carrinho de" in erro.value.mensagem
    assert len(falhas) == 2
    assert isinstance(erro.value.__cause__, ErroMCP)


async def test_uma_loja_so_falhando_mantem_a_mensagem_de_sempre():
    comb = _combinacao(_cand("ana", "loja-demo-sorvete", "sv-chocolate500"))
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "createCart", {"loja-demo-sorvete"})
        with pytest.raises(ErroCheckout) as erro:
            await montar_carrinhos(cli, comb, ENDERECO, falhas=[])
    assert erro.value.mensagem.startswith("Não deu para montar o carrinho de ")
    assert "MERCH-007" in erro.value.mensagem


async def test_sem_lista_de_falhas_continua_derrubando_tudo():
    """Remover itens / remontar loja não passam a lista: a 1ª loja com erro derruba, como antes."""
    async with abrir_cliente(carregar()) as base:
        cli = IFoodComFalha(base, "createCart", {"loja-demo-sorvete"})
        with pytest.raises(ErroCheckout):
            await montar_carrinhos(cli, _combinacao_roteiro(), ENDERECO)


# ---------- rota /escolher ----------
@pytest.fixture
def c():
    with TestClient(app) as cliente:
        yield cliente


def _falhar_no_ifood(monkeypatch, tool: str, lojas, erro=MERCH_007) -> None:
    original = rotas_match.abrir_cliente

    @asynccontextmanager
    async def com_falha(cfg):
        async with original(cfg) as cli:
            yield IFoodComFalha(cli, tool, lojas() if callable(lojas) else lojas, erro)

    monkeypatch.setattr(rotas_match, "abrir_cliente", com_falha)


def _sala_com_duas_lojas(c) -> tuple[Sala, dict]:
    s = Sala(c)
    resultado = s.pronta_para_escolher()
    comb = resultado["combinacoes"][0]
    assert len(comb["lojas"]) >= 2, "o roteiro do demo precisa de 2+ lojas na 1ª combinação"
    return s, comb


def _donos(comb: dict, loja_id: str) -> set[str]:
    return {slot.split("#", 1)[0] for slot, cand in comb["escolhas"].items() if cand["loja_id"] == loja_id}


@pytest.mark.parametrize("tool,erro", [("createCart", MERCH_007), ("getCart", INTERNAL)])
def test_escolher_com_uma_loja_falhando_devolve_200_com_aviso(c, monkeypatch, tool, erro):
    s, comb = _sala_com_duas_lojas(c)
    fora = comb["lojas"][0]
    _falhar_no_ifood(monkeypatch, tool, {fora}, erro)

    r = s.escolher("separado")
    assert r.status_code == 200, r.text
    dados = r.json()
    assert fora not in [k["loja_id"] for k in dados["carrinhos"]]
    assert [k["loja_id"] for k in dados["carrinhos"]] == comb["lojas"][1:]

    [loja] = dados["lojas_fora"]
    assert loja["loja_id"] == fora and loja["codigo_ifood"] == erro[1]
    nomes = {p["id"]: p["nome"] for p in s.estado()["participantes"]}
    assert {p["id"] for p in loja["participantes"]} == _donos(comb, fora)
    aviso = loja["aviso"]
    assert aviso.startswith(f"Não consegui montar o carrinho em {loja['loja_nome']} (o iFood respondeu {erro[1]})")
    assert all(nomes[pid] in aviso for pid in _donos(comb, fora))
    assert "o pedido segue com as outras lojas" in aviso
    assert aviso in dados["avisos"]

    estado = s.estado()
    assert estado["estado"] == "aguardando_pagamentos"
    assert aviso in estado["avisos"]
    # itens da loja que saiu não entram no valor de ninguém; quem ficou sem item fica fora da divisão
    assert soma_partes(estado) == soma_carrinhos(estado) > 0
    com_item = {it["participante_id"] for k in estado["carrinhos"] for it in k["itens"]}
    assert {p["participante_id"] for p in estado["partes"]} == com_item
    assert set(estado["pagamentos"]) == com_item
    for pid in _donos(comb, fora) - com_item:
        assert pid not in estado["pagamentos"]


def test_escolher_com_loja_fora_e_depois_remover_itens_nao_tenta_a_loja_que_saiu(c, monkeypatch):
    s, comb = _sala_com_duas_lojas(c)
    fora = comb["lojas"][0]
    _falhar_no_ifood(monkeypatch, "createCart", {fora})
    assert s.escolher("separado").status_code == 200
    estado = s.estado()
    org = estado["organizador_id"]
    pendente = next((p["participante_id"] for p in estado["partes"] if p["participante_id"] != org), None)
    if pendente is None:
        pytest.skip("ninguém além do organizador tem parte nesta combinação do demo")
    r = s.resolver(pendente, "remover_itens")
    # a loja que saiu não volta a ser tentada (senão o MERCH-007 derrubaria o remover com 502)
    assert r.status_code in (200, 409), r.text
    if r.status_code == 409:
        assert "esvaziaria" in r.json()["detail"]


def test_escolher_com_todas_as_lojas_falhando_continua_502_legivel(c, monkeypatch):
    s, comb = _sala_com_duas_lojas(c)
    _falhar_no_ifood(monkeypatch, "createCart", set(comb["lojas"]))
    r = s.escolher("separado")
    assert r.status_code == 502
    detalhe = r.json()["detail"]
    assert detalhe.startswith("Não deu para montar o carrinho de") and "MERCH-007" in detalhe
    assert s.estado()["estado"] == "match_pronto"  # dá para tentar de novo


def test_login_vencido_numa_loja_continua_401(c, monkeypatch):
    s, comb = _sala_com_duas_lojas(c)
    _falhar_no_ifood(monkeypatch, "createCart", {comb["lojas"][-1]}, erro=(MSG_401, None))
    r = s.escolher("separado")
    assert r.status_code == 401
    assert s.estado()["estado"] == "match_pronto"


def test_escolher_sem_falha_traz_lojas_fora_vazio(c):
    s, comb = _sala_com_duas_lojas(c)
    r = s.escolher("junto")
    assert r.status_code == 200 and r.json()["lojas_fora"] == []
    assert len(r.json()["carrinhos"]) == len(comb["lojas"])
    assert centavos(sum(k["total"] for k in r.json()["carrinhos"])) > 0
