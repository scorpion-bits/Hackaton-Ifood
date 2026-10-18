"""Leilão de agentes por loja (C11/C12): validação dura, fallback, patrocinado, agrupamento e caminho LLM."""

import asyncio
import json

import httpx
import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.ifood_mcp.demo_server import ARQUIVO_DADOS
from app.match import leilao, llm
from app.match import motor as motor_mod
from app.match.modelos import Candidato, Desejo, Intencao
from app.match.motor import rodar_match

ROTEIRO = [
    Desejo("milan", "Milan", "japonês e um sorvete, até R$ 45"),
    Desejo("zenon", "Zenon", "hambúrguer e sorvete, até R$ 50"),
    Desejo("antonio", "Antonio", "algo barato e vegetariano, até R$ 25", None, ["vegetariano"]),
]
TOP1_ROTEIRO = {"milan": "jp-guioza", "milan#2": "sv-sundae", "zenon": "bg-smash", "zenon#2": "sv-sundae",
                "antonio": "jp-sunomono"}
VENCEDORAS = {"loja-demo-japones", "loja-demo-burger", "loja-demo-sorvete"}


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


async def _rodar(desejos):
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        return await rodar_match(cfg, cli, desejos)


def _itens_do_demo() -> dict[tuple[str, str], dict]:
    dados = json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
    return {(l["id"], i["id"]): i for l in dados["lojas"] for i in l["itens"]}


# ---------- roteiro da demo (LLM mock) ----------
async def test_roteiro_mock_mantem_top1_e_preenche_leilao():
    r = await _rodar(ROTEIRO)
    melhor = r["combinacoes"][0]
    assert {s: e["item_id"] for s, e in melhor["escolhas"].items()} == TOP1_ROTEIRO
    assert all(0 <= c["afinidade"] <= 100 and 0 <= c["felizes"] <= 3 for c in r["combinacoes"])
    assert melhor["felizes"] == 3 and melhor["afinidade"] == 82

    bloco = r["leilao"]
    assert bloco["llm"] is False and bloco["demonstracao"] is True
    assert set(bloco["vencedoras"]) == set(melhor["lojas"]) == VENCEDORAS
    falas = bloco["falas"]
    assert falas[0]["quem"] == "ibits" and falas[0]["tipo"] == "abertura" and "3 pessoas" in falas[0]["texto"]
    assert falas[-1]["tipo"] == "fechamento" and set(falas[-1]["vencedoras"]) == VENCEDORAS
    assert "as taxas aparecem no carrinho antes do seu ok" in falas[-1]["texto"]
    assert "82% de afinidade e 3 de 3 bem atendidos" in falas[-1]["texto"]
    # só uma loja tem a maior nota (4,9): só ela diz "a melhor da sala"
    assert sum("a melhor da sala" in f["texto"] for f in falas) == 1
    assert "R$" not in falas[-1]["texto"]  # taxa nunca aparece nas falas
    lances = [f for f in falas if f["tipo"] == "lance"]
    assert 1 <= len(lances) <= 5 and sum(f["tipo"] == "passe" for f in falas) <= 2
    assert {f["quem"] for f in lances} >= VENCEDORAS
    replicas = [f for f in falas if f["tipo"] == "replica"]
    assert replicas == [{"quem": "loja-demo-sorvete", "tipo": "replica",
                         "texto": "Fecho 2 sorvetes num pedido só: 1 entrega em vez de 2."}]

    # patrocinado do demo: só tinha suco (bebida) dentro do orçamento do Antonio, que pediu comida → não oferta
    # bebida; passa com fala honesta e, por ser patrocinado, fala primeiro. Não vence.
    lojas = {l["loja_id"]: l for l in bloco["lojas"]}
    poke = lojas["loja-demo-poke"]
    assert poke["patrocinado"] is True and poke["vencedora"] is False and poke["passou"] and poke["ofertas"] == []
    assert falas[1] == {"quem": "loja-demo-poke", "tipo": "passe",
                        "texto": "Aqui não tem o que Antonio pediu dentro de R$ 25. Passo."}
    assert sum(l["patrocinado"] for l in lojas.values()) == 1
    assert not any(o["item_id"] == "pk-suco" for l in bloco["lojas"] for o in l["ofertas"])

    demo = _itens_do_demo()
    for loja in bloco["lojas"]:
        assert loja["fonte_fala"] == "modelo" and loja["imagem_url"] is None
        if loja["passou"]:
            assert loja["ofertas"] == [] and loja["agrupa"] is None
            continue
        assert loja["avaliacao"] is not None and loja["eta_min"] is not None
        por_slot: dict[str, int] = {}
        for o in loja["ofertas"]:
            assert o["preco"] == demo[(loja["loja_id"], o["item_id"])]["preco"]  # preço só da tool
            assert len(o["motivo"]) <= 90
            por_slot[o["slot_id"]] = por_slot.get(o["slot_id"], 0) + 1
        assert all(n <= 2 for n in por_slot.values())
        assert loja["atende"] == len({o["participante_id"] for o in loja["ofertas"]})
    assert lojas["loja-demo-sorvete"]["fala"] == ("Eu atendo todo mundo com Sundae de morango, R$ 18,90. "
                                                  "Nota 4,9, a melhor da sala.")
    assert lojas["loja-demo-sorvete"]["agrupa"]["pessoas"] == 3
    assert lojas["loja-demo-sorvete"]["agrupa"]["decisao"] == "regra"  # sem LLM, juntar é regra
    # o otimizador só escolheu itens ofertados
    ofertados = {(o["slot_id"], o["item_id"]) for l in bloco["lojas"] for o in l["ofertas"]}
    assert all((s, e["item_id"]) in ofertados for c in r["combinacoes"] for s, e in c["escolhas"].items())
    assert set(bloco["medicoes"]) == {"ms_total", "ms_por_loja", "chamadas_llm"}
    # só loja com algo para ofertar consulta o agente (o Poke passou sem chamada)
    assert bloco["medicoes"]["chamadas_llm"] == 0
    assert set(bloco["medicoes"]["ms_por_loja"]) == set(lojas) - {"loja-demo-poke"}
    json.dumps(r)


async def test_patrocinado_nao_muda_a_combinacao(monkeypatch):
    def assinatura(r):
        return [({s: (e["loja_id"], e["item_id"]) for s, e in c["escolhas"].items()}, c["score"])
                for c in r["combinacoes"]]

    resultados = []
    for politica in ({}, {"loja-demo-poke": {"patrocinado": True}}, {"loja-demo-burger": {"patrocinado": True}},
                     {"loja-demo-acai": {"patrocinado": True}}):
        monkeypatch.setattr(motor_mod, "carregar_politica", lambda p=politica: p)
        resultados.append(await _rodar(ROTEIRO))
    base = assinatura(resultados[0])
    assert all(assinatura(r) == base for r in resultados[1:])
    assert not any(l["patrocinado"] for l in resultados[0]["leilao"]["lojas"])
    burger = next(l for l in resultados[2]["leilao"]["lojas"] if l["loja_id"] == "loja-demo-burger")
    assert burger["patrocinado"] and burger["afinidade"] == next(
        l for l in resultados[0]["leilao"]["lojas"] if l["loja_id"] == "loja-demo-burger")["afinidade"]
    assert [f for f in resultados[2]["leilao"]["falas"] if f["tipo"] == "lance"][0]["quem"] == "loja-demo-burger"


async def test_patrocinada_fora_do_top_8_nao_entra(monkeypatch):
    """Patrocínio é só visibilidade: com > 8 lojas, pagar não compra vaga no corte (nem muda o conjunto)."""
    _agentes(monkeypatch, {})
    desejo, intencao = Desejo("p", "Paula", "pizza"), Intencao("p", consultas=["pizza"])
    lista = [Candidato("p", f"loja-{n:02d}", f"Loja {n}", f"i{n}", f"Pizza {n}", 10.0, 30, "RESTAURANT", False,
                       nota=round(0.95 - n * 0.05, 2)) for n in range(12)]
    assert leilao._escolher_lojas({"p": lista}, {"p": intencao}) == [f"loja-{n:02d}" for n in range(8)]
    for politica in ({}, {"loja-11": {"patrocinado": True}}, {"loja-09": {"patrocinado": True}}):
        _, bloco = await leilao.rodar_leilao(carregar(), [(desejo, intencao)], {"p": lista}, {}, {"p": "Paula"},
                                             politica)
        assert [l["loja_id"] for l in bloco["lojas"]] == [f"loja-{n:02d}" for n in range(8)]
        assert not any(f["quem"] in politica for f in bloco["falas"])
    # patrocinada dentro do top 8: o lance dela vem primeiro, com o rótulo
    _, bloco = await leilao.rodar_leilao(carregar(), [(desejo, intencao)], {"p": lista}, {}, {"p": "Paula"},
                                         {"loja-06": {"patrocinado": True}})
    lances = [f for f in bloco["falas"] if f["tipo"] == "lance"]
    assert lances[0]["quem"] == "loja-06" and lances[0]["patrocinado"] is True


async def test_leilao_desligado_volta_ao_motor_sem_leilao(monkeypatch):
    monkeypatch.setenv("MATCH_LEILAO", "off")
    r = await _rodar(ROTEIRO)
    assert "leilao" not in r
    assert {s: e["item_id"] for s, e in r["combinacoes"][0]["escolhas"].items()} == TOP1_ROTEIRO


async def test_sem_candidatos_leilao_vazio_com_abertura_e_fechamento():
    r = await _rodar([Desejo("ana", "Ana", "pizza, até R$ 5")])
    bloco = r["leilao"]
    assert bloco["lojas"] == [] and bloco["vencedoras"] == []
    assert [f["tipo"] for f in bloco["falas"]] == ["abertura", "fechamento"]
    assert "para você" in bloco["falas"][0]["texto"] and "sem vencedor" in bloco["falas"][1]["texto"]


# ---------- agentes com LLM falso (validação dura) ----------
L1, L2, L3 = "loja-sorvete", "loja-japa", "loja-praca"


def _cenario():
    slots = [(Desejo("ana", "Ana", "um sorvete"), Intencao("ana", consultas=["sorvete"])),
             (Desejo("bia", "Bia", "japonês"), Intencao("bia", consultas=["japonês"]))]

    def c(pid, loja, nome_loja, item, preco, nota):
        return Candidato(pid, loja, nome_loja, item, item.upper(), preco, 30, "RESTAURANT", False, nota=nota,
                         motivo=f"motivo do juiz {item}")

    candidatos = {
        "ana": [c("ana", L1, "Gelato", "sv1", 20.0, 0.9), c("ana", L1, "Gelato", "sv2", 15.5, 0.8),
                c("ana", L1, "Gelato", "sv3", 12.9, 0.7), c("ana", L3, "Praça", "pr1", 18.0, 0.5)],
        "bia": [c("bia", L2, "Japa", "jp1", 30.9, 0.9), c("bia", L2, "Japa", "jp2", 25.0, 0.6),
                c("bia", L3, "Praça", "pr2", 22.0, 0.5)],
    }
    detalhes = {(L1, "sv1"): {"tags": ["vegano"], "avaliacao": 4.7, "descricao": "Pote 500 ml"},
                (L1, "sv2"): {"tags": [], "avaliacao": 4.7, "preco_original": 19.9},
                (L1, "sv3"): {"tags": [], "avaliacao": 4.7},
                (L2, "jp1"): {"tags": [], "avaliacao": 4.5}, (L2, "jp2"): {"tags": [], "avaliacao": 4.5},
                (L3, "pr1"): {"tags": []}, (L3, "pr2"): {"tags": []}}
    return slots, candidatos, detalhes, {"ana": "Ana", "bia": "Bia"}


def _agentes(monkeypatch, respostas: dict[str, object]):
    """Troca o LLM por respostas fixas por loja (chave = nome da loja que o agente recebe)."""
    async def falso(cfg, sistema, usuario, timeout=None):
        assert "agente vendedor" in sistema and timeout == leilao.TIMEOUT_AGENTE_S
        return respostas.get(json.loads(usuario)["loja"])

    monkeypatch.setattr(leilao, "completar_json", falso)


async def _leilao(monkeypatch, respostas):
    _agentes(monkeypatch, respostas)
    slots, candidatos, detalhes, nomes = _cenario()
    filtrados, bloco = await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes, {})
    return filtrados, bloco, {l["loja_id"]: l for l in bloco["lojas"]}


async def test_agente_so_enxerga_os_proprios_itens(monkeypatch):
    vistos = {}

    async def falso(cfg, sistema, usuario, timeout=None):
        dados = json.loads(usuario)
        vistos[dados["loja"]] = {p["slot_id"]: [i["item_id"] for i in p["itens"]] for p in dados["pedidos"]}
        return None

    monkeypatch.setattr(leilao, "completar_json", falso)
    slots, candidatos, detalhes, nomes = _cenario()
    await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes, {})
    assert vistos == {"Gelato": {"ana": ["sv1", "sv2", "sv3"]}, "Japa": {"bia": ["jp1", "jp2"]},
                      "Praça": {"ana": ["pr1"], "bia": ["pr2"]}}


async def test_fala_com_numero_inventado_cai_no_modelo(monkeypatch):
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv1", "motivo": "Cremoso"}],
                   "fala": "SV1 por R$ 9,90 só hoje!"},
        "Japa": {"ofertas": [{"slot_id": "bia", "item_id": "jp1", "motivo": "Fresquinho"}],
                 "fala": "JP1 por R$ 30,90, chego em 30 min. Nota 4,5."}})
    assert lojas[L1]["fonte_ofertas"] == "llm" and lojas[L1]["fonte_fala"] == "modelo"
    assert lojas[L1]["fala"].startswith("Eu atendo 1 de 2 com SV1, R$ 20.")
    assert lojas[L2]["fonte_fala"] == "llm" and lojas[L2]["fala"] == "JP1 por R$ 30,90, chego em 30 min. Nota 4,5."
    assert lojas[L2]["ofertas"][0]["motivo"] == "Fresquinho"
    assert lojas[L3]["fonte_ofertas"] == "modelo"  # sem resposta → fallback


async def test_item_de_outra_loja_ou_slot_e_rejeitado(monkeypatch):
    filtrados, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "bia", "item_id": "jp1"}, {"slot_id": "ana", "item_id": "jp1"},
                               {"slot_id": "ana", "item_id": "nao-existe"}, {"slot_id": "zz", "item_id": "sv1"},
                               {"slot_id": "ana", "item_id": "sv2"}], "fala": "Tenho SV2."},
        "Japa": {"ofertas": [{"slot_id": "ana", "item_id": "sv1"}], "fala": "Tenho SV1."}})
    assert [(o["slot_id"], o["item_id"]) for o in lojas[L1]["ofertas"]] == [("ana", "sv2")]
    # nada válido e sem "passo" → fallback determinístico (top-2 por nota)
    assert lojas[L2]["fonte_ofertas"] == "modelo" and lojas[L2]["fonte_fala"] == "modelo"
    assert [o["item_id"] for o in lojas[L2]["ofertas"]] == ["jp1", "jp2"]
    assert [c.item_id for c in filtrados["ana"]] == ["sv2", "pr1"]


async def test_mais_de_2_por_slot_e_cortado(monkeypatch):
    filtrados, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": i} for i in ("sv3", "sv3", "sv2", "sv1")],
                   "fala": "Três sabores pra Ana."}})
    assert [o["item_id"] for o in lojas[L1]["ofertas"]] == ["sv3", "sv2"]
    assert [c.item_id for c in filtrados["ana"] if c.loja_id == L1] == ["sv2", "sv3"]  # ordem original da busca


def test_ler_resposta_corta_e_valida_motivo():
    _, candidatos, detalhes, _ = _cenario()
    por_slot = {"ana": [c for c in candidatos["ana"] if c.loja_id == L1]}
    ofertas, passo = leilao.ler_resposta(
        {"ofertas": [{"slot_id": "ana", "item_id": "sv2", "motivo": "x" * 200},
                     {"slot_id": "ana", "item_id": "sv1", "motivo": "Só R$ 5"}], "passo": "sim"},
        por_slot, {"ana": "ana"}, {"ana": "Ana"}, detalhes)
    assert passo is False and len(ofertas[0]["motivo"]) == 90
    assert ofertas[1]["motivo"] == "motivo do juiz sv1"  # número no motivo → motivo do juiz
    assert leilao.ler_resposta("lixo", por_slot, {}, {}) == ([], False)


@pytest.mark.parametrize("fala, item, fonte", [
    ("Meu SV2 é vegano.", "sv2", "modelo"),          # restrição sem tag que confirme
    ("Meu SV1 é vegano.", "sv1", "llm"),             # tag "vegano" confirma
    ("SV1 sem lactose, do jeito que pediu.", "sv1", "llm"),  # vegano confirma sem lactose
    ("SV1 sem glúten!", "sv1", "modelo"),
    ("SV1 zero açúcar.", "sv1", "modelo"),           # não existe tag que confirme
    ("O SV1 mais barato da cidade.", "sv1", "modelo"),  # comparativo só no template
    ("Sou a melhor loja da sala.", "sv1", "modelo"),
    ("Chego mais rápido que todo mundo.", "sv1", "modelo"),
    ("Pote de 500 ml por R$ 20,00.", "sv1", "llm"),  # número do item e preço ofertado
])
async def test_fala_validada_semanticamente(monkeypatch, fala, item, fonte):
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": item}], "fala": fala}})
    assert lojas[L1]["fonte_ofertas"] == "llm" and lojas[L1]["fonte_fala"] == fonte
    if fonte == "llm":
        assert lojas[L1]["fala"] == fala


async def test_motivo_com_restricao_sem_tag_ou_superlativo_fica_o_do_juiz(monkeypatch):
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv2", "motivo": "Opção sem lactose"},
                               {"slot_id": "ana", "item_id": "sv1", "motivo": "Vegano e cremoso"}],
                   "fala": "Dois potes pra Ana."},
        "Japa": {"ofertas": [{"slot_id": "bia", "item_id": "jp1", "motivo": "O melhor temaki"}], "fala": "Oi!"}})
    motivos = {o["item_id"]: o["motivo"] for o in lojas[L1]["ofertas"]}
    assert motivos == {"sv2": "motivo do juiz sv2", "sv1": "Vegano e cremoso"}
    assert lojas[L2]["ofertas"][0]["motivo"] == "motivo do juiz jp1"


async def test_preco_promocional_pode_ser_citado(monkeypatch):
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv2"}], "fala": "SV2 de R$ 19,90 por R$ 15,50."}})
    oferta = lojas[L1]["ofertas"][0]
    assert oferta["preco"] == 15.5 and oferta["preco_original"] == 19.9
    assert lojas[L1]["fonte_fala"] == "llm"
    # template (sem LLM) também mostra o "de"
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv2"}], "fala": "SV2 por R$ 12,00."}})
    assert lojas[L1]["fonte_fala"] == "modelo" and "R$ 15,50 (de R$ 19,90)" in lojas[L1]["fala"]
    assert leilao.preco_cheio({"preco_original": 15.5}, 15.5) is None


async def test_agrupamento_vira_replica(monkeypatch):
    slots, _, _, nomes = _cenario()
    _, bloco, lojas = await _leilao(monkeypatch, {
        "Praça": {"ofertas": [{"slot_id": "ana", "item_id": "pr1"}, {"slot_id": "bia", "item_id": "pr2"}],
                  "fala": "Atendo as 2 aqui.", "replica": "Junto Ana e Bia num pedido só: 1 entrega em vez de 2."}})
    agrupa = lojas[L3]["agrupa"]
    assert agrupa["pessoas"] == 2 and agrupa["entregas_a_menos"] == 1 and agrupa["fonte"] == "llm"
    assert lojas[L1]["agrupa"] is None  # atende só 1 pessoa
    combinacao = {"lojas": [L3], "escolhas": {"ana": {"loja_id": L3, "item_id": "pr1", "nota": 0.5},
                                               "bia": {"loja_id": L3, "item_id": "pr2", "nota": 0.5}}}
    pessoa_de = {"ana": "ana", "bia": "bia"}
    combinacao["afinidade"], combinacao["felizes"] = leilao.afinidade_e_felizes(combinacao, list(nomes), pessoa_de)
    assert (combinacao["afinidade"], combinacao["felizes"]) == (50, 2)
    leilao.fechar_leilao(bloco, [combinacao], slots, pessoa_de, nomes)
    assert bloco["vencedoras"] == [L3] and lojas[L3]["vencedora"]
    replica = next(f for f in bloco["falas"] if f["tipo"] == "replica")
    assert replica == {"quem": L3, "tipo": "replica", "texto": "Junto Ana e Bia num pedido só: 1 entrega em vez de 2."}
    assert bloco["falas"][-1]["texto"].startswith("Rodada fechada. Melhor opção: Praça, com 50% de afinidade e 2 de 2")


async def test_passe_do_agente_e_rede_de_seguranca(monkeypatch):
    filtrados, bloco, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [], "passo": True, "fala": "Hoje não, passo."},
        "Japa": {"ofertas": [], "passo": True, "fala": "Passo."},
        "Praça": {"ofertas": [{"slot_id": "bia", "item_id": "pr2"}], "fala": "PR2 pra Bia."}})
    assert lojas[L1]["passou"] and lojas[L1]["ofertas"] == [] and lojas[L1]["fala"] == "Hoje não, passo."
    assert lojas[L1]["fonte_fala"] == "llm"
    assert {f["quem"] for f in bloco["falas"] if f["tipo"] == "passe"} == {L1, L2}
    assert not any(c.loja_id == L1 for c in filtrados["ana"])
    # Ana ficaria sem nenhuma oferta: a rede de segurança devolve o fallback da Praça para o slot dela
    assert [c.item_id for c in filtrados["ana"]] == ["pr1"]
    assert [c.item_id for c in filtrados["bia"]] == ["pr2"]


# ---------- caminho LLM com provedor HTTP falso ----------
def _resposta_openai(conteudo: str) -> dict:
    return {"id": "x", "object": "chat.completion", "created": 0, "model": "m", "choices": [
        {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": conteudo}}]}


def _provedor_falso(monkeypatch, lenta: str | None = None):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")
    monkeypatch.setenv("LLM_API_KEY", "chave-teste")

    async def handler(request):
        corpo = json.loads(request.content)
        sistema, usuario = corpo["messages"][0]["content"], corpo["messages"][1]["content"]
        if "agente vendedor" not in sistema:  # intérprete e juiz: sem JSON → fallback determinístico
            return httpx.Response(200, json=_resposta_openai("sem json aqui"))
        dados = json.loads(usuario)
        if dados["loja"] == lenta:
            await asyncio.sleep(5)
        ofertas = [{"slot_id": p["slot_id"], "item_id": i["item_id"], "motivo": "Combina com o pedido"}
                   for p in dados["pedidos"] for i in sorted(p["itens"], key=lambda i: (-i["nota"], i["preco"]))[:2]]
        primeiro = sorted(dados["pedidos"][0]["itens"], key=lambda i: (-i["nota"], i["preco"]))[0]
        preco = f"{primeiro['preco']:.2f}".replace(".", ",")
        resposta = {"ofertas": ofertas, "passo": False,
                    "fala": f"Aqui tem {primeiro['nome']} por R$ {preco}, chego em {dados['tempo_entrega_min']} min.",
                    "replica": "Junto todo mundo num pedido só: 1 entrega."}
        return httpx.Response(200, json=_resposta_openai(json.dumps(resposta, ensure_ascii=False)))

    monkeypatch.setattr(llm, "_cliente_http", lambda _p: httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_caminho_llm_gera_fala_do_llm(monkeypatch):
    _provedor_falso(monkeypatch)
    r = await _rodar(ROTEIRO)
    bloco = r["leilao"]
    # o Poke (só bebida para quem pediu comida) passa sem gastar chamada; as outras lojas falam pelo LLM
    ativas = [l for l in bloco["lojas"] if l["loja_id"] != "loja-demo-poke"]
    assert bloco["llm"] is True and bloco["medicoes"]["chamadas_llm"] == len(ativas)
    assert all(l["fonte_fala"] == "llm" and l["fonte_ofertas"] == "llm" for l in ativas)
    sorvete = next(l for l in bloco["lojas"] if l["loja_id"] == "loja-demo-sorvete")
    assert sorvete["fala"] == "Aqui tem Sundae de morango por R$ 18,90, chego em 25 min."
    replica = next(f for f in bloco["falas"] if f["tipo"] == "replica")
    assert replica["quem"] == "loja-demo-sorvete"
    assert {s: e["item_id"] for s, e in r["combinacoes"][0]["escolhas"].items()} == TOP1_ROTEIRO


async def test_agente_lento_usa_fallback_sem_derrubar_o_leilao(monkeypatch):
    monkeypatch.setattr(leilao, "TIMEOUT_AGENTE_S", 0.3)
    _provedor_falso(monkeypatch, lenta="Kaigan Sushi (demo)")
    r = await _rodar(ROTEIRO)
    lojas = {l["loja_id"]: l for l in r["leilao"]["lojas"]}
    japones = lojas.pop("loja-demo-japones")
    assert japones["fonte_ofertas"] == "modelo" and japones["fonte_fala"] == "modelo" and japones["ofertas"]
    assert lojas.pop("loja-demo-poke")["passou"]  # nada para ofertar: passa sem chamar o LLM
    assert all(l["fonte_fala"] == "llm" for l in lojas.values())
    assert r["leilao"]["llm"] is True
    assert r["leilao"]["medicoes"]["ms_por_loja"]["loja-demo-japones"] < 2000
    # a tentativa que estourou o tempo não conta como chamada ao LLM
    assert r["leilao"]["medicoes"]["chamadas_llm"] == len(r["leilao"]["lojas"]) - 2
    assert r["combinacoes"] and set(r["leilao"]["vencedoras"]) == VENCEDORAS


# ---------- correções do QA (T17b) ----------
def _com_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")


async def test_chamadas_llm_conta_so_resposta_json_valida(monkeypatch):
    _com_llm(monkeypatch)
    _, bloco, _ = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv1"}], "fala": "SV1 pra Ana."},
        "Japa": None,  # erro/timeout → completar_json devolve None
        "Praça": "lixo"})  # não é objeto JSON
    assert bloco["medicoes"]["chamadas_llm"] == 1 and bloco["llm"] is True
    _, bloco, _ = await _leilao(monkeypatch, {})  # nenhum agente respondeu
    assert bloco["medicoes"]["chamadas_llm"] == 0 and bloco["llm"] is False


async def test_llm_falso_coerente_quando_so_veio_lixo(monkeypatch):
    _com_llm(monkeypatch)
    # JSON válido mas sem nenhuma oferta válida e sem "passo": fallback em tudo → leilão não é "llm"
    _, bloco, lojas = await _leilao(monkeypatch, {"Gelato": {"ofertas": [{"slot_id": "zz", "item_id": "x"}]}})
    assert bloco["medicoes"]["chamadas_llm"] == 1
    assert bloco["llm"] is False and all(l["fonte_fala"] == "modelo" for l in lojas.values())


def test_item_cortado_conta_zero_na_afinidade_e_nos_felizes():
    pessoa_de = {"ana": "ana", "ana#2": "ana", "bia": "bia"}
    combinacao = {"escolhas": {"ana": {"nota": 0.8}, "bia": {"nota": 0.8}}}  # o 2º item da Ana ficou de fora
    assert leilao.afinidade_e_felizes(combinacao, ["ana", "bia"], pessoa_de) == (60, 1)
    combinacao["escolhas"]["ana#2"] = {"nota": 0.8}
    assert leilao.afinidade_e_felizes(combinacao, ["ana", "bia"], pessoa_de) == (80, 2)


async def test_fechamento_nao_diz_todos_bem_atendidos_com_item_cortado():
    seis = [Desejo(f"p{i}", n, t) for i, (n, t) in enumerate([
        ("Ana", "pizza"), ("Beto", "hambúrguer"), ("Caio", "sushi"), ("Duda", "sorvete"), ("Eva", "salada vegana"),
        ("Fabio", "pizza e sorvete")])]
    r = await _rodar(seis)
    melhor = r["combinacoes"][0]
    fora = [s for p in r["pessoas"] for s in p["slots"] if s not in melhor["escolhas"]]
    if not fora:
        pytest.skip("nenhum item ficou de fora neste cenário")
    pessoas_com_corte = {s.split("#", 1)[0] for s in fora}
    assert melhor["felizes"] <= len(seis) - len(pessoas_com_corte)
    assert f"{melhor['felizes']} de {len(seis)} bem atendidos" in r["leilao"]["falas"][-1]["texto"]


@pytest.mark.parametrize("fala, item, fonte", [
    ("SV1 com frete grátis.", "sv1", "modelo"),
    ("Ganhe um brinde com o SV1.", "sv1", "modelo"),
    ("Use o cupom e leve SV1.", "sv1", "modelo"),
    ("SV1 sem taxa hoje.", "sv1", "modelo"),
    ("SV1 em promoção!", "sv1", "modelo"),                     # sem preço "de" real
    ("SV2 em promoção: de R$ 19,90 por R$ 15,50.", "sv2", "llm"),  # preço "de" real nos dados
    ("SV3 sem leite.", "sv3", "modelo"),
    ("SV3 lactose zero.", "sv3", "modelo"),
    ("SV3 plant-based.", "sv3", "modelo"),
    ("SV3 sem carne.", "sv3", "modelo"),
    ("SV3 orgânico e fresquinho.", "sv3", "modelo"),
    ("SV3 light, bem fit.", "sv3", "modelo"),
    ("SV1 sem carne nenhuma.", "sv1", "llm"),                   # tag "vegano" confirma
    ("SV1 por dezenove e noventa.", "sv1", "modelo"),          # número por extenso fora dos dados
    ("SV1 por R$ 20 e noventa.", "sv1", "modelo"),
    ("Chego em trinta minutos com o SV1.", "sv1", "llm"),       # 30 min é o ETA da loja
    ("Um SV1 cremoso pra Ana.", "sv1", "llm"),                  # "um" = 1
    ("Atendo todo mundo com SV1.", "sv1", "modelo"),           # atende 1 de 2
    ("SV1 pra todos vocês.", "sv1", "modelo"),
    ("Fecho 2 sorvetes pra Ana.", "sv1", "modelo"),             # é 1 sorvete só
    ("Tenho dois potes de SV1.", "sv1", "modelo"),
    ("Atendo 1 de 2 pessoas com SV1.", "sv1", "llm"),
    ("Atendo 2 pessoas com SV1.", "sv1", "modelo"),
])
async def test_fala_sem_promessa_extenso_ou_contagem_errada(monkeypatch, fala, item, fonte):
    _, _, lojas = await _leilao(monkeypatch, {
        "Gelato": {"ofertas": [{"slot_id": "ana", "item_id": item}], "fala": fala}})
    assert lojas[L1]["fonte_ofertas"] == "llm" and lojas[L1]["fonte_fala"] == fonte, lojas[L1]["fala"]


async def test_replica_com_contagem_certa_passa_e_errada_cai_no_modelo(monkeypatch):
    for replica, fonte in (("Fecho os 2 pedidos num só: 1 entrega em vez de 2.", "llm"),
                           ("Fecho 3 pedidos num só: 1 entrega em vez de 3.", "modelo"),
                           ("Junto tudo e o frete sai grátis.", "modelo")):
        _, _, lojas = await _leilao(monkeypatch, {
            "Praça": {"ofertas": [{"slot_id": "ana", "item_id": "pr1"}, {"slot_id": "bia", "item_id": "pr2"}],
                      "fala": "Atendo as 2.", "replica": replica}})
        assert lojas[L3]["agrupa"]["fonte"] == fonte, replica


def test_motivo_sem_extenso_e_sem_promessa():
    assert leilao._motivo_valido("Dois sabores cremosos", set()) == ""
    assert leilao._motivo_valido("Frete grátis", set()) == ""
    assert leilao._motivo_valido("Opção fit", set()) == ""
    assert leilao._motivo_valido("Um clássico gelado", set()) == "Um clássico gelado"
    assert leilao._motivo_valido("Salada fit fresquinha", set(), ["Salada fit"]) == "Salada fit fresquinha"


async def test_melhor_da_sala_so_com_nota_unica(monkeypatch):
    _agentes(monkeypatch, {})
    slots, candidatos, detalhes, nomes = _cenario()
    _, bloco = await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes, {})
    lojas = {l["loja_id"]: l for l in bloco["lojas"]}
    assert "Nota 4,7, a melhor da sala." in lojas[L1]["fala"]
    assert "a melhor da sala" not in lojas[L2]["fala"]
    # empate na maior nota: ninguém é "a melhor da sala"; as duas só dizem a nota
    for chave in ((L2, "jp1"), (L2, "jp2")):
        detalhes[chave]["avaliacao"] = 4.7
    _, bloco = await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes, {})
    lojas = {l["loja_id"]: l for l in bloco["lojas"]}
    assert not any("a melhor da sala" in l["fala"] for l in lojas.values())
    assert lojas[L1]["fala"].endswith("Nota 4,7.") and lojas[L2]["fala"].endswith("Nota 4,7.")


async def test_abertura_usa_o_texto_da_pessoa_sem_categoria(monkeypatch):
    _agentes(monkeypatch, {})
    _, candidatos, detalhes, nomes = _cenario()
    slots = [(Desejo("ana", "Ana", "feijoada completa, até R$ 40"), Intencao("ana")),
             (Desejo("bia", "Bia", "japonês"), Intencao("bia", consultas=["japonês"]))]
    _, bloco = await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes, {})
    abertura = bloco["falas"][0]["texto"]
    assert abertura == "Pedido novo para 2 pessoas: feijoada completa, japonês. Quem topa?"
    r = await _rodar([Desejo("a", "Ana", "feijoada completa")])
    assert "feijoada completa" in r["leilao"]["falas"][0]["texto"]
    assert "surpreenda-me" not in r["leilao"]["falas"][0]["texto"]


# ---------- avaliação 2 do jurado (T17d) ----------
async def test_bebida_nunca_e_oferta_para_quem_pediu_comida_e_patrocinada_passa_primeiro(monkeypatch):
    vistos = {}

    async def falso(cfg, sistema, usuario, timeout=None):
        dados = json.loads(usuario)
        vistos[dados["loja"]] = [i["item_id"] for p in dados["pedidos"] for i in p["itens"]]
        return None

    monkeypatch.setattr(leilao, "completar_json", falso)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")
    slots, candidatos, detalhes, nomes = _cenario()
    slots[0] = (Desejo("ana", "Ana", "um sorvete, até R$ 21"), Intencao("ana", consultas=["sorvete"],
                                                                           orcamento_max=21.0))
    # Praça só tem, para a Ana, um suco (bebida) dentro do orçamento; o pr1 vira bebida também
    candidatos["ana"].append(Candidato("ana", L3, "Praça", "pr-suco", "Suco verde", 9.9, 30, "RESTAURANT", False,
                                       nota=0.6, motivo="m"))
    detalhes[(L3, "pr-suco")] = {"tags": ["vegano"], "categoria": "Bebidas"}
    detalhes[(L3, "pr1")] = {"tags": [], "categoria": "Bebidas"}
    candidatos["bia"] = [c for c in candidatos["bia"] if c.loja_id != L3]  # Praça não tem nada para a Bia
    _, bloco = await leilao.rodar_leilao(carregar(), slots, candidatos, detalhes, nomes,
                                         {L3: {"patrocinado": True}})
    lojas = {l["loja_id"]: l for l in bloco["lojas"]}
    assert "Praça" not in vistos  # nada para ofertar: passa sem gastar chamada (e o agente nunca vê a bebida)
    assert lojas[L3]["passou"] and lojas[L3]["ofertas"] == [] and lojas[L3]["patrocinado"]
    assert bloco["falas"][1] == {"quem": L3, "tipo": "passe",
                                 "texto": "Aqui não tem o que Ana pediu dentro de R$ 21. Passo."}
    # sem orçamento, a fala não cita valor
    assert leilao._fala_passe({"ana": [c for c in candidatos["ana"] if c.loja_id == L3]},
                              {"ana": (Desejo("ana", "Ana", "um sorvete"), Intencao("ana", consultas=["sorvete"]))},
                              detalhes) == "Aqui não tem o que Ana pediu. Passo."
    # quem pediu bebida pode receber bebida
    pediu = Intencao("ana", consultas=["suco"])
    suco = next(c for c in candidatos["ana"] if c.item_id == "pr-suco")
    assert leilao._ofertavel(suco, pediu, detalhes) and not leilao._ofertavel(suco, slots[0][1], detalhes)


async def test_agente_decide_se_agrupa(monkeypatch):
    base = {"ofertas": [{"slot_id": "ana", "item_id": "pr1"}, {"slot_id": "bia", "item_id": "pr2"}],
            "fala": "Atendo as 2.", "replica": "Fecho os 2 pedidos num só: 1 entrega em vez de 2."}
    slots, _, _, nomes = _cenario()
    pessoa_de = {"ana": "ana", "bia": "bia"}
    combinacao = {"lojas": [L3], "afinidade": 50, "felizes": 2,
                  "escolhas": {"ana": {"loja_id": L3, "item_id": "pr1", "nota": 0.5},
                               "bia": {"loja_id": L3, "item_id": "pr2", "nota": 0.5}}}
    # o agente recusa juntar → sem agrupamento e sem réplica
    _, bloco, lojas = await _leilao(monkeypatch, {"Praça": {**base, "agrupa": False}})
    assert lojas[L3]["atende"] == 2 and lojas[L3]["agrupa"] is None
    leilao.fechar_leilao(bloco, [combinacao], slots, pessoa_de, nomes)
    assert not any(f["tipo"] == "replica" for f in bloco["falas"])
    # o agente decide juntar → decisão do agente, texto dele
    _, _, lojas = await _leilao(monkeypatch, {"Praça": {**base, "agrupa": True}})
    assert lojas[L3]["agrupa"]["decisao"] == "agente" and lojas[L3]["agrupa"]["fonte"] == "llm"
    # sem "agrupa" no JSON (ou valor inválido) → vale a regra (atende 2+ → junta)
    for extra in ({}, {"agrupa": "sim"}):
        _, _, lojas = await _leilao(monkeypatch, {"Praça": {**base, **extra}})
        assert lojas[L3]["agrupa"]["decisao"] == "regra"
    # "agrupa": true com 1 pessoa só não vale
    _, _, lojas = await _leilao(monkeypatch, {"Gelato": {"ofertas": [{"slot_id": "ana", "item_id": "sv1"}],
                                                         "fala": "SV1.", "agrupa": True}})
    assert lojas[L1]["agrupa"] is None
