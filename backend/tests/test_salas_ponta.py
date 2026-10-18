"""Sala inteira pela API com as novidades da Trilha A′ (Z18 b): Ajustar com combo/2 itens, loja fora com combo e
vaquinha com a taxa de serviço do iFood (bug 29). Invariante de sempre: as partes somam os carrinhos ao centavo."""

import pytest

from app.match import checkout
from test_loja_falha import INTERNAL, MERCH_007, _falhar_no_ifood
from test_salas import Sala, c, demo_limpo, soma_carrinhos, soma_partes  # noqa: F401 (fixtures)

SERVICO = 0.99


def _com_taxa_de_servico(monkeypatch):
    """O demo não cobra taxa de serviço; o real cobra ~R$ 1 por carrinho (docs/mcp-real/bug25-whopper-carrinho.json)."""
    original = checkout._ler_totais

    def ler(resp):
        t = original(resp)
        return {**t, "servico": SERVICO, "total": round(t["total"] + SERVICO, 2)}

    monkeypatch.setattr(checkout, "_ler_totais", ler)


def _fechar_vaquinha(s: Sala) -> dict:
    estado = s.estado()
    for p in estado["partes"]:
        pid = p["participante_id"]
        if estado["pagamentos"].get(pid, {}).get("status") != "pago":
            assert s.pagar(pid, "dinheiro").status_code == 200
            assert s.recebi(pid).status_code == 200
    return s.estado()


def test_vaquinha_com_taxa_de_servico_soma_ao_centavo_e_envia(c, monkeypatch):
    _com_taxa_de_servico(monkeypatch)
    s = Sala(c)
    s.pronta_para_escolher()
    r = s.escolher("separado")
    assert r.status_code == 200, r.text
    estado = s.estado()
    assert all(k["servico"] == SERVICO for k in estado["carrinhos"])
    assert soma_partes(estado) == soma_carrinhos(estado)
    estado = _fechar_vaquinha(s)
    assert soma_partes(estado) == soma_carrinhos(estado)
    r = s.enviar()
    assert r.status_code == 200, r.text
    assert len(s.estado()["pedidos"]) == len(estado["carrinhos"])


def test_ajustar_para_combo_e_dois_itens_mantem_as_partes_ao_centavo(c, monkeypatch):
    _com_taxa_de_servico(monkeypatch)
    s = Sala(c)
    s.convidar({"Ana": {"texto": "pizza"}, "Bia": {"texto": "japonês, até R$ 60", "orcamento_max": 60}})
    assert s.rodar().status_code == 200
    r = s.c.post(s.url("/ajustar"), json={"texto": "a Ana quer hambúrguer com batata e refri"}, headers=s.org)
    assert r.status_code == 200, r.text
    r = s.c.post(s.url("/ajustar"), json={"texto": "a Bia quer japonês e um sorvete"}, headers=s.org)
    assert r.status_code == 200, r.text
    assert len(s.estado()["ajustes"]) == 2
    assert s.escolher("separado").status_code == 200
    estado = s.estado()
    assert soma_partes(estado) == soma_carrinhos(estado)
    itens = [(i["participante_id"], i["item_id"]) for k in estado["carrinhos"] for i in k["itens"]]
    assert len(itens) == len(set(itens))  # nenhum item (combo incluído) entra duas vezes para a mesma pessoa


@pytest.mark.parametrize("tool,erro", [("createCart", MERCH_007), ("getCart", INTERNAL)])
def test_loja_fora_com_combo_na_outra_loja_fecha_a_vaquinha_ao_centavo(c, monkeypatch, tool, erro):
    _com_taxa_de_servico(monkeypatch)
    s = Sala(c)
    s.convidar({"Ana": {"texto": "hambúrguer com batata e refri"},
                "Bia": {"texto": "sushi, até R$ 70", "orcamento_max": 70}})
    r = s.rodar()
    assert r.status_code == 200, r.text
    assert r.json()["combinacoes"][0]["lojas"] == ["loja-demo-burger", "loja-demo-japones"]
    _falhar_no_ifood(monkeypatch, tool, {"loja-demo-japones"}, erro)

    r = s.escolher("separado")
    assert r.status_code == 200, r.text
    assert [f["loja_id"] for f in r.json()["lojas_fora"]] == ["loja-demo-japones"]
    estado = s.estado()
    [carrinho] = estado["carrinhos"]
    assert carrinho["loja_id"] == "loja-demo-burger" and carrinho["servico"] == SERVICO
    assert [i["item_id"] for i in carrinho["itens"]] == ["bg-combo"]  # o combo vai uma vez só
    assert soma_partes(estado) == soma_carrinhos(estado)
    estado = _fechar_vaquinha(s)
    assert s.enviar().status_code == 200
