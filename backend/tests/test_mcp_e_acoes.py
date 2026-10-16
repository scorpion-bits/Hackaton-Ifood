import json

import pytest
from mcp import Client

from app import acoes
from app.ifood import ErroIFood
from app.mcp_server import criar_servidor


async def chamar(nome, args):
    async with Client(criar_servidor()) as c:
        r = await c.call_tool(nome, args)
        texto = "\n".join(x.text for x in r.content)
        return r.is_error, (texto if r.is_error else json.loads(texto))


async def test_servidor_expoe_ferramentas_dos_dois_lados():
    async with Client(criar_servidor()) as c:
        nomes = {t.name for t in (await c.list_tools()).tools}
    assert {"vendedor_listar_cardapio", "vendedor_propor_promocao", "comprador_buscar_itens",
            "comprador_propor_pedido", "consultar_acao"} <= nomes


async def test_busca_respeita_preco_max():
    erro, dados = await chamar("comprador_buscar_itens", {"termo": "burger", "preco_max": 30})
    assert not erro
    nomes = [i["nome"] for i in dados["itens"]]
    assert "Burger clássico" in nomes and "Burger duplo" not in nomes
    assert all(i["preco"] <= 30 for i in dados["itens"])
    assert dados["fonte"] == "demonstração"


async def test_promocao_acima_do_limite_e_recusada():
    erro, texto = await chamar("vendedor_propor_promocao",
                               {"loja_id": "loja-demo-1", "item_id": "it-101", "desconto_pct": 80, "motivo": "x"})
    assert erro and "70%" in texto


async def test_pedido_acima_do_orcamento_e_recusado():
    erro, texto = await chamar("comprador_propor_pedido", {
        "loja_id": "loja-demo-3", "itens": [{"item_id": "it-301", "quantidade": 1}],
        "motivo": "x", "orcamento_max": 50})
    assert erro and "orçamento" in texto


async def test_proposta_nao_executa_ate_confirmar():
    erro, acao = await chamar("comprador_propor_pedido", {
        "loja_id": "loja-demo-2", "itens": [{"item_id": "it-201", "quantidade": 2}], "motivo": "teste"})
    assert not erro and acao["status"] == "pendente"
    _, antes = await chamar("vendedor_listar_cardapio", {"loja_id": "loja-demo-2"})
    assert next(i for i in antes["itens"] if i["id"] == "it-201")["estoque"] == 30

    feita = acoes.confirmar(acao["id"])
    assert feita["status"] == "executada"
    assert feita["resultado"]["total"] == round(29.9 * 2 + 4.99, 2)
    _, depois = await chamar("vendedor_listar_cardapio", {"loja_id": "loja-demo-2"})
    assert next(i for i in depois["itens"] if i["id"] == "it-201")["estoque"] == 28

    with pytest.raises(ErroIFood):
        acoes.confirmar(acao["id"])


async def test_recusar_acao():
    _, acao = await chamar("vendedor_propor_disponibilidade",
                           {"loja_id": "loja-demo-1", "item_id": "it-102", "disponivel": False, "motivo": "acabou"})
    assert acoes.recusar(acao["id"])["status"] == "recusada"
