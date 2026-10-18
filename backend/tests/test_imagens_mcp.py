"""M9: foto do prato (`itemImageUrl`) e logo da loja (`merchantLogoUrl`) do MCP real chegam ao candidato e ao leilão.

Usa as amostras sanitizadas de docs/mcp-real/. No modo demonstração (lojas fictícias) tudo continua None (emoji).
"""

import dataclasses
import json
from pathlib import Path

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.match.busca import _candidato, _itens_do_menu, _ler_item
from app.match.modelos import Candidato, Desejo, Intencao, para_dict
from app.match.motor import rodar_match

AMOSTRAS = Path(__file__).resolve().parents[2] / "docs" / "mcp-real"
PREFIXO = "https://static.ifood-static.com.br/"


def _resposta(tool: str, indice: int = 0) -> dict:
    return json.loads((AMOSTRAS / f"{tool}.json").read_text(encoding="utf-8"))["chamadas"][indice]["resposta"]


def test_item_do_searchoffers_real_traz_foto_e_logo_da_loja():
    r = next(x for x in _resposta("searchOffers")["results"] if x.get("itemImageUrl"))
    item = _ler_item(r)
    assert item["imagem_url"] == r["itemImageUrl"] and item["imagem_url"].startswith(PREFIXO)
    assert item["loja_logo_url"] == r["merchant"]["merchantLogoUrl"]
    c = _candidato(item, Intencao("ana", consultas=["pizza"]))
    assert (c.imagem_url, c.loja_logo_url) == (item["imagem_url"], item["loja_logo_url"])
    assert para_dict(c)["imagem_url"] == item["imagem_url"]  # o resultado da API serializa o campo


def test_destaques_do_getmerchant_real_trazem_foto_e_logo_da_raiz():
    menu = _resposta("getMerchant")
    itens = _itens_do_menu(menu)
    assert itens and all(i["loja_logo_url"] == menu["merchantLogoUrl"] for i in itens)
    assert any(i["imagem_url"] and i["imagem_url"].startswith(PREFIXO) for i in itens)


def test_url_que_nao_e_do_ifood_vira_none():
    r = {**_resposta("searchOffers")["results"][0], "itemImageUrl": "https://exemplo.com/x.jpg"}
    r["merchant"] = {**r["merchant"], "merchantLogoUrl": "javascript:alert(1)"}
    item = _ler_item(r)
    assert item["imagem_url"] is None and item["loja_logo_url"] is None


def test_modo_demonstracao_continua_sem_imagem():
    resetar_demo()
    import asyncio

    async def rodar():
        cfg = carregar()
        async with abrir_cliente(cfg) as cli:
            return await rodar_match(cfg, cli, [Desejo("ana", "Ana", "uma pizza e uma coca")])

    r = asyncio.run(rodar())
    escolhas = r["combinacoes"][0]["escolhas"].values()
    assert all(e["imagem_url"] is None and e["loja_logo_url"] is None for e in escolhas)
    assert all(l["imagem_url"] is None for l in r["leilao"]["lojas"])


def test_leilao_usa_a_logo_do_mcp_da_loja():
    from app.match import leilao
    base = Candidato("ana", "L1", "Loja 1", "i1", "Pizza", 30.0, 40, "RESTAURANT", False, nota=0.9)
    com_logo = dataclasses.replace(base, item_id="i2", loja_logo_url=PREFIXO + "logo.png")
    slots = [(Desejo("ana", "Ana", "pizza"), Intencao("ana", consultas=["pizza"]))]
    import asyncio

    _, bloco = asyncio.run(leilao.rodar_leilao(carregar(), slots, {"ana": [base, com_logo]}, {}, {"ana": "Ana"}, {}))
    assert bloco["lojas"][0]["imagem_url"] == PREFIXO + "logo.png"
