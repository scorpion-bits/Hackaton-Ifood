"""Motor do Match (C5): intérprete, busca, juiz e LLM — com o MCP de demonstração e LLM mock ou HTTP falso."""

import json

import httpx
import httpx2
import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.ifood_mcp.demo_server import ARQUIVO_DADOS
from app.match import busca as busca_mod
from app.match import interprete, juiz, llm
from app.match import motor as motor_mod
from app.match.busca import buscar, buscar_detalhado, ler_endereco
from app.match.interprete import interpretar, interpretar_fallback
from app.match.modelos import Candidato, Desejo, Intencao
from app.match.motor import rodar_match

ROTEIRO = [
    Desejo("milan", "Milan", "japonês e um sorvete, até R$ 45"),
    Desejo("zenon", "Zenon", "hambúrguer e sorvete, até R$ 50"),
    Desejo("antonio", "Antonio", "algo barato e vegetariano, até R$ 25", None, ["vegetariano"]),
]
ORCAMENTOS = {"milan": 45.0, "zenon": 50.0, "antonio": 25.0}


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


def _itens_do_demo() -> dict[tuple[str, str], dict]:
    dados = json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))
    return {(l["id"], i["id"]): {**i, "loja": l} for l in dados["lojas"] for i in l["itens"]}


async def _rodar(desejos):
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        return await rodar_match(cfg, cli, desejos)


# ---------- roteiro da demo (LLM mock) ----------
async def test_roteiro_da_demo_gera_top3_coerente_com_precos_do_demo():
    r = await _rodar(ROTEIRO)
    combos = r["combinacoes"]
    assert 1 <= len(combos) <= 3
    demo = _itens_do_demo()

    for comb in combos:
        for slot, esc in comb["escolhas"].items():
            original = demo[(esc["loja_id"], esc["item_id"])]
            assert esc["preco"] == original["preco"]  # preço só da tool, nunca inventado
            assert esc["item_nome"] == original["nome"]
            assert esc["loja_nome"] == original["loja"]["nome"]
            assert esc["eta_min"] == original["loja"]["tempo_entrega_min"]
            assert 0 <= esc["nota"] <= 1 and esc["motivo"] and len(esc["motivo"]) <= 90
            assert not esc["viola"]

    melhor = combos[0]
    assert len(melhor["lojas"]) <= 3
    gasto: dict[str, float] = {}
    for slot, esc in melhor["escolhas"].items():
        gasto[slot.split("#")[0]] = gasto.get(slot.split("#")[0], 0.0) + esc["preco"]
    assert set(gasto) == {"milan", "zenon", "antonio"}  # ninguém fica sem nada
    for pid, total in gasto.items():
        assert total <= ORCAMENTOS[pid] + 1e-9
    antonio = [e for s, e in melhor["escolhas"].items() if s.split("#")[0] == "antonio"]
    assert antonio and all("vegetariano" in demo[(e["loja_id"], e["item_id"])]["tags"] for e in antonio)
    # "momento uau": os sorvetes de Milan e Zenon vêm da MESMA sorveteria; os pratos principais, de lojas diferentes
    esc = melhor["escolhas"]
    assert set(esc) == {"milan", "milan#2", "zenon", "zenon#2", "antonio"}
    assert esc["milan#2"]["loja_id"] == esc["zenon#2"]["loja_id"] == "loja-demo-sorvete"
    assert esc["milan"]["loja_id"] == "loja-demo-japones" and esc["zenon"]["loja_id"] == "loja-demo-burger"
    assert set(melhor["lojas"]) == {"loja-demo-japones", "loja-demo-burger", "loja-demo-sorvete"}
    assert [c["score"] for c in combos] == sorted((c["score"] for c in combos), reverse=True)

    # intenções por slot (C4b) e pessoas
    slots = [i["participante_id"] for i in r["intencoes"]]
    assert slots == ["milan", "milan#2", "zenon", "zenon#2", "antonio"]
    assert {p["participante_id"]: p["slots"] for p in r["pessoas"]}["milan"] == ["milan", "milan#2"]
    # avisos legíveis sobre o que ficou de fora e sobre lojas/taxas
    assert not any("ficou de fora" in a for a in r["avisos"])  # ninguém perdeu item
    assert any("3 lojas = 3 pedidos, 3 taxas de entrega e 3 entregas" in a for a in r["avisos"])
    # rastro: listAddresses primeiro, depois as buscas; endereço do demo
    assert r["rastro"][0]["tool"] == "listAddresses"
    assert {c["tool"] for c in r["rastro"][1:]} <= {"searchOffers", "getMerchant", "browseOffers"}
    assert all(c["ok"] for c in r["rastro"])
    assert r["endereco"]["id"] == "end-demo-sao-carlos"
    # relevância: o roteiro não ganha aviso de "opção aproximada" nem de restrição sem confirmação
    assert not any("Não achei" in a or "Nenhum item confirma" in a for a in r["avisos"])
    # 3 lojas + taxa estimada + "o orçamento vale para os itens" (o roteiro tem orçamento)
    assert len(r["avisos"]) == 3
    assert "O orçamento de cada pessoa vale para os itens; a taxa de entrega é somada à parte." in r["avisos"]
    assert not any(e["motivo"].startswith("Opção aproximada") for c in combos for e in c["escolhas"].values())
    json.dumps(r)


async def test_acai_e_sorvete_nao_sao_cortados_com_folga_de_lojas_e_aviso_diz_o_motivo_real():
    """Regressão (A5, etapa 05): Milan pede açaí, Zenon sorvete. Antes o top 1 usava 2 lojas, cortava os dois e
    culpava o limite de 3 lojas. Agora usa as 3 lojas; só o que exige a 4ª loja fica de fora (e o aviso diz isso)."""
    r = await _rodar([Desejo("milan", "Milan", "japonês e um açaí, até 45"), *ROTEIRO[1:]])
    melhor = r["combinacoes"][0]
    assert len(melhor["lojas"]) == 3
    assert melhor["componentes"]["slots_fora"] == 1  # japonês + açaí + burger + sorvete = 4 lojas: um não cabe
    assert {"milan", "zenon", "antonio"} <= {s.split("#")[0] for s in melhor["escolhas"]}
    fora = [a for a in r["avisos"] if "ficou de fora" in a]
    assert len(fora) == 1 and "em até 3 lojas" in fora[0]
    assert any(a.startswith("Com 4 lojas dá para incluir") for a in r["avisos"])


async def test_pessoa_sem_opcao_vira_aviso_legivel():
    r = await _rodar([Desejo("milan", "Milan", "japonês, até R$ 45"),
                      Desejo("ana", "Ana", "algo vegano, até R$ 5")])
    # diz também quanto custa o mais barato que a busca achou (acima do orçamento)
    assert any(a.startswith("Não achei nada vegano até R$ 5 para Ana: o mais barato custa R$ ") for a in r["avisos"])
    assert r["combinacoes"]
    assert set(r["combinacoes"][0]["escolhas"]) == {"milan"}
    assert "sem opção válida para Ana" in r["combinacoes"][0]["explicacao"]


async def test_nada_cabe_vira_aviso_e_lista_vazia():
    r = await _rodar([Desejo("ana", "Ana", "pizza, até R$ 5")])
    assert r["combinacoes"] == []
    assert any("Nenhuma combinação coube" in a for a in r["avisos"])
    assert any("Não achei pizza até R$ 5 para Ana" in a for a in r["avisos"])


@pytest.fixture
def sem_consulta_livre(monkeypatch):
    """Força o intérprete a não gerar consulta para item fora do dicionário (pedido vai para a exploração)."""
    monkeypatch.setattr(interprete, "_consulta_livre", lambda *a, **k: "")


async def test_item_fora_do_dicionario_busca_pelo_proprio_texto(monkeypatch):
    # T17c: "feijoada completa" vira a consulta do searchOffers (no MCP real, é o que a pessoa pediu)
    consultas: list[str] = []
    original = busca_mod.buscar_detalhado

    async def espiao(cliente, intencao, endereco, **kw):
        consultas.append(intencao.consultas)
        return await original(cliente, intencao, endereco, **kw)

    monkeypatch.setattr(motor_mod, "buscar_detalhado", espiao)
    r = await _rodar([Desejo("milan", "Milan", "japonês, até R$ 45"),
                      Desejo("ana", "Ana", "feijoada completa, até R$ 60")])
    assert ["feijoada completa"] in consultas
    # o demo não tem feijoada: a busca específica volta vazia, cai no browseOffers perto do endereço (C16) e o
    # aviso é honesto ("a opção mais próxima é X"); a pessoa que achou o que queria segue
    assert "browseOffers" in [c["tool"] for c in r["rastro"]]
    assert any(a.startswith("Não achei feijoada completa para Ana; a opção mais próxima é ") for a in r["avisos"])
    assert r["combinacoes"]


async def test_pedido_fora_do_cardapio_avisa_opcao_aproximada(sem_consulta_livre):
    # Milan acha o que quer; a feijoada da Ana não existe nos cardápios do demo
    r = await _rodar([Desejo("milan", "Milan", "japonês, até R$ 45"),
                      Desejo("ana", "Ana", "feijoada completa, até R$ 60")])
    aviso = next(a for a in r["avisos"] if a.startswith("Não achei feijoada completa para Ana"))
    assert "a opção mais próxima é " in aviso and aviso.endswith("Quer mudar o pedido?")
    assert "R$" not in aviso  # o orçamento não entra no nome do que foi pedido
    assert r["combinacoes"]  # a pessoa que achou o que queria segue
    escolhas = r["combinacoes"][0]["escolhas"]
    assert escolhas["ana"]["motivo"].startswith("Opção aproximada: ") and len(escolhas["ana"]["motivo"]) <= 90
    assert f"{escolhas['ana']['item_nome']} ({escolhas['ana']['loja_nome']})" in aviso
    assert not escolhas["milan"]["motivo"].startswith("Opção aproximada")
    assert not any("Nada do que foi pedido" in a for a in r["avisos"])


async def test_tudo_irrelevante_devolve_combinacoes_vazias_com_aviso(sem_consulta_livre):
    r = await _rodar([Desejo("ana", "Ana", "feijoada completa, até R$ 60")])
    assert r["combinacoes"] == []
    assert "Não achei feijoada completa para Ana." in r["avisos"]
    assert not any("a opção mais próxima" in a for a in r["avisos"])  # bug 14: sem combinação, nada de "mais próxima"
    assert any("Nada do que foi pedido está nos cardápios" in a for a in r["avisos"])
    # pizza sem glúten: as pizzas violam a restrição e o resto não tem nada a ver com o pedido
    r = await _rodar([Desejo("ana", "Ana", "pizza", None, ["sem_gluten"])])
    assert r["combinacoes"] == []
    aviso = next(a for a in r["avisos"] if a.startswith("Não achei pizza sem glúten para Ana"))
    assert "Refrigerante" not in aviso and "Suco" not in aviso  # bebida nunca é a "mais próxima" de comida
    assert r["avisos"][-1] == "Nada do que foi pedido está nos cardápios das lojas. Quer mudar o pedido?"
    assert sum("Quer mudar o pedido?" in a for a in r["avisos"]) == 1  # a pergunta não se repete


async def test_restricao_sem_tag_que_confirme_avisa_sem_eliminar(monkeypatch):
    original = motor_mod.buscar_detalhado

    async def sem_tags(cliente, intencao, endereco, **kw):  # como uma loja que não informa nenhuma tag
        candidatos, detalhes = await original(cliente, intencao, endereco)
        return candidatos, {k: {**v, "tags": []} for k, v in detalhes.items()}

    with monkeypatch.context() as m:
        m.setattr(motor_mod, "buscar_detalhado", sem_tags)
        r = await _rodar([Desejo("ana", "Ana", "hambúrguer", None, ["vegetariano"])])
        assert "Nenhum item confirma 'vegetariano' — confirme com a loja." in r["avisos"]
        assert r["combinacoes"] and not any("Não achei" in a for a in r["avisos"])  # o item segue na lista
        # com mais de uma pessoa, o aviso diz de quem é
        r = await _rodar([Desejo("ana", "Ana", "smash burger", None, ["sem_gluten"]),
                          Desejo("milan", "Milan", "japonês, até R$ 45")])
        assert "Nenhum item confirma 'sem glúten' para Ana — confirme com a loja." in r["avisos"]
    # com tag confirmando (vegetariano no demo) não há aviso
    r = await _rodar([Desejo("ana", "Ana", "hambúrguer", None, ["vegetariano"])])
    assert not any("Nenhum item confirma" in a for a in r["avisos"])


# ---------- intérprete (fallback) ----------
def test_fallback_separa_slots_e_le_orcamento():
    milan = interpretar_fallback(Desejo("m", "Milan", "Japonês e um sorvete, até R$ 45"))
    assert [i.participante_id for i in milan] == ["m", "m#2"]
    assert milan[0].consultas[0] == "japonês" and milan[1].consultas[0] == "sorvete"
    assert all(i.orcamento_max == 45 for i in milan)
    assert all(i.verticais == ["RESTAURANT"] for i in milan)

    antonio = interpretar_fallback(Desejo("a", "Antonio", "algo barato e vegetariano, até R$ 25", None,
                                          ["vegetariano"]))
    assert len(antonio) == 1  # "barato e vegetariano" não são dois itens
    assert antonio[0].restricoes == ["vegetariano"] and antonio[0].perfil == "barato"
    assert antonio[0].consultas == ["vegetariano"] and antonio[0].orcamento_max == 25

    tres = interpretar_fallback(Desejo("p", "P", "pizza + refri, açaí; 40 reais, rápido"))
    assert [i.participante_id for i in tres] == ["p", "p#2", "p#3"]
    assert tres[0].orcamento_max == 40 and tres[0].perfil == "rapido"

    alternativa = interpretar_fallback(Desejo("p", "P", "sushi ou poke sem lactose"))
    assert len(alternativa) == 1 and alternativa[0].restricoes == ["sem_lactose"]
    assert {"sushi", "poke"} <= {c.split()[0] for c in alternativa[0].consultas} | set(alternativa[0].vontades)

    # orçamento do formulário vence o do texto; "30 min" não é orçamento
    assert interpretar_fallback(Desejo("p", "P", "pizza até 99", 50))[0].orcamento_max == 50
    assert interpretar_fallback(Desejo("p", "P", "pizza que chegue até 30 min"))[0].orcamento_max is None
    mercado = interpretar_fallback(Desejo("p", "P", "ingredientes pra fazer o jantar"))
    assert mercado[0].verticais == ["GROCERIES"]


# ---------- busca e juiz ----------
async def test_busca_marca_violacao_so_quando_claro_e_juiz_avisa_sem_tag():
    cfg = carregar()
    intencao = Intencao("p", consultas=["hambúrguer"], verticais=["RESTAURANT"], restricoes=["vegetariano"],
                        vontades=["hambúrguer", "burger"], orcamento_max=None)
    async with abrir_cliente(cfg) as cli:
        endereco = ler_endereco(await cli.chamar("listAddresses"))
        candidatos, detalhes = await buscar_detalhado(cli, intencao, endereco)
        assert await buscar(cli, intencao, endereco)  # mesma busca, só a lista
    por_id = {c.item_id: c for c in candidatos}
    assert len(candidatos) <= 8 and len(por_id) == len(candidatos)
    assert por_id["bg-smash"].viola == ["vegetariano"]  # "carne smash", sem tag
    assert por_id["bg-grao"].viola == []  # tag vegetariano
    demo = _itens_do_demo()
    assert all(c.preco == demo[(c.loja_id, c.item_id)]["preco"] for c in candidatos)

    # item sem tag e sem carne no texto: não elimina, o juiz avisa
    duvida = Candidato("p", "loja-demo-japones", "Kaigan Sushi (demo)", "jp-missoshiru", "Missoshiru", 9.9, 45,
                       "RESTAURANT", False)
    detalhe = {"descricao": "Sopa de missô com tofu e cebolinha", "categoria": "Entradas", "tags": ["sem_lactose"]}
    julgado = (await juiz.avaliar(cfg, Desejo("p", "P", "algo vegetariano"),
                                  Intencao("p", consultas=["vegetariano"], restricoes=["vegetariano"]),
                                  [duvida], {("loja-demo-japones", "jp-missoshiru"): detalhe}))[0]
    assert "pode não estar informado — confirme com a loja" in julgado.motivo
    assert len(julgado.motivo) <= 90 and julgado.viola == [] and duvida.motivo == ""


# ---------- caminho LLM com HTTP falso ----------
def _resposta_openai(conteudo: str) -> dict:
    return {"id": "x", "object": "chat.completion", "created": 0, "model": "m", "choices": [
        {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": conteudo}}]}


def _usar_provedor(monkeypatch, provedor: str, handler, http=httpx):
    monkeypatch.setenv("LLM_PROVIDER", provedor)
    monkeypatch.setenv("LLM_MODEL", "modelo-teste")
    monkeypatch.setenv("LLM_API_KEY", "chave-teste")
    monkeypatch.setattr(llm, "_cliente_http", lambda _p: http.AsyncClient(transport=http.MockTransport(handler)))


async def test_interprete_usa_json_do_llm_openai_compativel(monkeypatch):
    pedidas = []
    intencao_llm = {
        "itens": [{"consultas": ["temaki"], "verticais": ["RESTAURANT"], "vontades": ["temaki", "salmão"]},
                  {"consultas": ["sorvete"], "verticais": ["MARTE"], "vontades": ["chocolate"]}],
        "restricoes": ["sem lactose"], "orcamento_max": 99, "perfil": "qualidade",
    }

    def handler(request):
        pedidas.append(json.loads(request.content))
        return httpx.Response(200, json=_resposta_openai(json.dumps(intencao_llm)))

    _usar_provedor(monkeypatch, "groq", handler)
    desejo = Desejo("m", "Milan", "um temaki caprichado e um sorvete de chocolate, até 45", None, ["vegetariano"])
    intencoes = await interpretar(carregar(), desejo)
    assert [i.participante_id for i in intencoes] == ["m", "m#2"]
    assert intencoes[0].consultas == ["temaki"] and intencoes[1].vontades == ["chocolate"]
    assert intencoes[1].verticais == ["RESTAURANT"]  # vertical inválida do LLM é descartada
    assert set(intencoes[0].restricoes) == {"vegetariano", "sem_lactose"}  # chip sempre entra
    assert all(i.orcamento_max == 45 for i in intencoes)  # número do texto, não o 99 do LLM
    assert intencoes[0].perfil == "qualidade"
    corpo = pedidas[0]
    assert corpo["response_format"] == {"type": "json_object"} and corpo["model"] == "modelo-teste"
    assert "temaki caprichado" in corpo["messages"][1]["content"]


async def test_motor_com_llm_usa_notas_e_motivos_do_juiz(monkeypatch):
    def handler(request):
        corpo = json.loads(request.content)
        sistema = corpo["messages"][0]["content"]
        if "interpreta" in sistema:
            resposta = {"itens": [{"consultas": ["sorvete"], "verticais": ["RESTAURANT"], "vontades": ["pistache"]}],
                        "restricoes": [], "orcamento_max": None, "perfil": "equilibrado"}
        else:
            itens = json.loads(corpo["messages"][1]["content"])["itens"]
            resposta = {"avaliacoes": [
                {"i": it["i"], "nota": 0.95 if "pistache" in it["nome"].lower() else 0.3,
                 "motivo": "Gelato de pistache, como pediu" if "pistache" in it["nome"].lower() else "Outro sabor"}
                for it in itens]}
        return httpx.Response(200, json=_resposta_openai("Aqui está: " + json.dumps(resposta)))

    _usar_provedor(monkeypatch, "openai", handler)
    r = await _rodar([Desejo("b", "Bia", "um sorvete de pistache")])
    melhor = r["combinacoes"][0]["escolhas"]["b"]
    assert melhor["item_id"] == "sv-pistache300" and melhor["nota"] == 0.95
    assert melhor["motivo"] == "Gelato de pistache, como pediu"
    assert melhor["preco"] == _itens_do_demo()[("loja-demo-sorvete", "sv-pistache300")]["preco"]


async def test_completar_json_anthropic_extrai_objeto_do_texto(monkeypatch):
    pedidas = []

    def handler(request):
        pedidas.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "m1", "type": "message", "role": "assistant", "model": "modelo-teste", "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "content": [{"type": "text", "text": 'Claro!\n```json\n{"ok": true, "n": 2}\n```'}]})

    _usar_provedor(monkeypatch, "anthropic", handler, http=httpx2)
    assert await llm.completar_json(carregar(), "sistema", "usuario") == {"ok": True, "n": 2}
    assert pedidas[0]["system"].startswith("sistema") and pedidas[0]["messages"][0]["content"] == "usuario"


async def test_llm_falhando_ou_mock_cai_no_fallback(monkeypatch):
    assert await llm.completar_json(carregar(), "s", "u") is None  # mock

    _usar_provedor(monkeypatch, "groq", lambda request: httpx.Response(500, json={"error": "fora do ar"}))
    assert await llm.completar_json(carregar(), "s", "u") is None
    desejo = Desejo("m", "Milan", "japonês e um sorvete, até R$ 45")
    assert await interpretar(carregar(), desejo) == interpretar_fallback(desejo)

    _usar_provedor(monkeypatch, "groq", lambda request: httpx.Response(200, json=_resposta_openai("sem json aqui")))
    assert await llm.completar_json(carregar(), "s", "u") is None
    assert interprete.validar_resposta_llm({"itens": []}, desejo) is None


def test_extrair_json():
    assert llm.extrair_json('texto {"a": 1} fim') == {"a": 1}
    assert llm.extrair_json('[1, 2] e depois {"b": {"c": 2}}') == {"b": {"c": 2}}
    assert llm.extrair_json("{quebrado") is None
    assert llm.extrair_json(None) is None


# ---------- correções do QA (T17b): intérprete e endereço ----------
@pytest.mark.parametrize("texto", ["qualquer coisa barata", "o mais barato", "algo baratinho", "o de menor preço"])
def test_frases_de_barato_ativam_o_perfil_barato(texto):
    assert all(i.perfil == "barato" for i in interpretar_fallback(Desejo("a", "Ana", texto)))


def test_perfil_barato_do_texto_vale_mesmo_se_o_llm_disser_outro():
    dados = {"itens": [{"consultas": ["lanche"], "verticais": ["RESTAURANT"], "vontades": []}],
             "restricoes": [], "orcamento_max": None, "perfil": "equilibrado"}
    intencoes = interprete.validar_resposta_llm(dados, Desejo("a", "Ana", "o mais barato"))
    assert intencoes[0].perfil == "barato"


def test_quantidade_vira_slots_repetidos_ate_3():
    intencoes = interpretar_fallback(Desejo("a", "Ana", "2 sorvetes"))
    assert [(i.participante_id, i.consultas) for i in intencoes] == [("a", ["sorvete"]), ("a#2", ["sorvete"])]
    duas = interpretar_fallback(Desejo("a", "Ana", "dois hambúrgueres e um açaí"))
    assert [i.consultas[0] for i in duas] == ["hambúrguer", "hambúrguer", "açaí"]
    assert [i.participante_id for i in duas] == ["a", "a#2", "a#3"]


def test_quantidade_acima_do_limite_ou_sem_item_gera_aviso(monkeypatch):
    desejo = Desejo("a", "Ana", "5 pizzas e um sorvete")
    intencoes, avisos = interprete.aplicar_quantidades(desejo, interpretar_fallback(desejo))
    assert [i.consultas[0] for i in intencoes] == ["pizza", "pizza", "pizza", "sorvete"]
    assert avisos == ["Ana pediu '5 pizzas': o Match põe 3 no pedido (até 3 iguais por pessoa); o resto foi ignorado."]
    desejo = Desejo("a", "Ana", "2 sorvetes e 3 coxinhas até 99")
    intencoes, avisos = interprete.aplicar_quantidades(desejo, interpretar_fallback(desejo))
    # "coxinhas" agora é um slot com consulta própria; o limite de 4 slots por pessoa corta a 3ª coxinha
    assert [i.consultas[0] for i in intencoes] == ["sorvete", "sorvete", "coxinhas", "coxinhas"]
    assert all(i.orcamento_max == 99 for i in intencoes)
    assert avisos == ["Ana pediu '3 coxinhas': o Match põe 2 no pedido (até 3 iguais por pessoa); o resto foi ignorado."]
    # sem consulta livre (comportamento antigo), item que o Match não separa continua avisando
    monkeypatch.setattr(interprete, "_consulta_livre", lambda *a, **k: "")
    intencoes, avisos = interprete.aplicar_quantidades(desejo, interpretar_fallback(desejo))
    assert len(intencoes) == 2 and all(i.orcamento_max == 99 for i in intencoes)
    assert avisos == ["A quantidade em '3 coxinhas' (Ana) foi ignorada: o Match escolhe 1 item para esse pedido."]


def test_quantidade_e_idempotente_e_ignora_numero_do_nome_do_prato():
    desejo = Desejo("a", "Ana", "2 sorvetes")
    uma_vez = interpretar_fallback(desejo)
    assert interprete.aplicar_quantidades(desejo, uma_vez) == (uma_vez, [])
    pizza = Desejo("a", "Ana", "pizza 4 queijos até 60 reais")
    assert interprete.aplicar_quantidades(pizza, interpretar_fallback(pizza)) == (interpretar_fallback(pizza), [])


async def test_motor_avisa_quantidade_ignorada_e_monta_os_dois_itens(sem_consulta_livre):
    r = await _rodar([Desejo("a", "Ana", "2 sorvetes"), Desejo("b", "Bia", "duas coxinhas")])
    assert next(p for p in r["pessoas"] if p["participante_id"] == "a")["slots"] == ["a", "a#2"]
    assert any("'duas coxinhas' (Bia) foi ignorada" in a for a in r["avisos"])
    assert len(r["avisos"]) == len(set(r["avisos"]))  # slots repetidos não repetem aviso


class _ClienteEndereco:
    """Cliente de demonstração com o `listAddresses` trocado; sem coordenadas, a busca não acha nada."""

    def __init__(self, cliente, enderecos):
        self._cli, self._enderecos, self.modo = cliente, enderecos, "demo"

    async def chamar(self, tool, **args):
        if tool == "listAddresses":
            return self._enderecos
        if tool in ("searchOffers", "browseOffers") and "latitude" not in args:
            return {"items": [], "merchants": []}
        return await self._cli.chamar(tool, **args)

    def rastro_como_dicts(self):
        return self._cli.rastro_como_dicts()


async def _rodar_com_endereco(enderecos, desejos=None):
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        return await rodar_match(cfg, _ClienteEndereco(cli, enderecos), desejos or ROTEIRO)


async def test_sem_endereco_marca_problema_de_endereco():
    r = await _rodar_com_endereco({"addresses": []})
    assert r["problema"] == "endereco" and r["avisos"] == [motor_mod.MSG_SEM_ENDERECO]


async def test_endereco_sem_coordenadas_avisa_em_vez_de_nao_achei():
    r = await _rodar_com_endereco({"addresses": [{"addressId": "a1", "formattedAddress": "Rua X, 1"}]})
    assert r["problema"] == "endereco" and r["combinacoes"] == []
    assert r["avisos"] == [motor_mod.MSG_ENDERECO_SEM_COORDENADAS]
    assert not any(a.startswith("Não achei") for a in r["avisos"])


async def test_endereco_sem_id_avisa_ja_ao_rodar():
    r = await _rodar_com_endereco({"addresses": [{"formattedAddress": "Rua X, 1",
                                                  "coordinates": {"latitude": -22.0, "longitude": -47.9}}]})
    assert "problema" not in r and r["combinacoes"]
    assert motor_mod.MSG_ENDERECO_SEM_ID in r["avisos"]


async def test_sem_endereco_com_mock_busca_no_local_do_env(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", "-22.0025,-47.8986")
    r = await _rodar_com_endereco({"addresses": []})
    assert "problema" not in r and r["combinacoes"]
    assert r["endereco"]["id"] == motor_mod.ID_ENDERECO_MOCK
    assert motor_mod.MSG_ENDERECO_MOCK in r["avisos"]


async def test_mock_nao_substitui_endereco_salvo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", "-22.0025,-47.8986")
    r = await _rodar_com_endereco({"addresses": [{"addressId": "a1", "formattedAddress": "Rua X, 1",
                                                  "coordinates": {"latitude": -22.0, "longitude": -47.9}}]})
    assert r["endereco"]["id"] == "a1" and motor_mod.MSG_ENDERECO_MOCK not in r["avisos"]


async def test_mock_invalido_continua_pedindo_endereco(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", "São Carlos")
    r = await _rodar_com_endereco({"addresses": []})
    assert r["problema"] == "endereco" and r["avisos"] == [motor_mod.MSG_SEM_ENDERECO]


# ---------- pedido completo (Trilha A′, etapa 05) ----------
@pytest.mark.parametrize("texto", ["uma pizza e uma coca", "pizza e um guaraná, até 50", "uma pizza e um refri"])
async def test_pizza_e_refrigerante_saem_da_mesma_pizzaria(texto):
    """Regressão: "uma pizza e uma coca" virava pizza + açaí de outra loja; "guaraná" ficava de fora com 2 avisos
    que se contradiziam ("Não achei" e "não cabe no orçamento")."""
    r = await _rodar([Desejo("ana", "Ana", texto)])
    melhor = r["combinacoes"][0]
    assert set(melhor["escolhas"]) == {"ana", "ana#2"}
    assert melhor["lojas"] == ["loja-demo-pizza"]
    assert "refrigerante" in melhor["escolhas"]["ana#2"]["item_nome"].lower()
    assert not any("Não achei" in a or "ficou de fora" in a for a in r["avisos"])


async def test_busca_na_loja_usa_refinements_merchant_id_e_so_traz_o_que_bate():
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        endereco = ler_endereco(await cli.chamar("listAddresses"))
        intencao = Intencao("ana#2", consultas=["coca", "refrigerante"], vontades=["refrigerante"])
        cands, detalhes = await busca_mod.buscar_na_loja(cli, intencao, endereco, "loja-demo-pizza", "RESTAURANT")
        rastro = cli.rastro_como_dicts()
    assert [(c.loja_id, c.item_id) for c in cands] == [("loja-demo-pizza", "pz-refri")]
    assert ("loja-demo-pizza", "pz-refri") in detalhes
    chamadas = [c for c in rastro if c["tool"] == "searchOffers"]
    assert len(chamadas) == 2  # "coca" não existe na pizzaria; "refrigerante" sim (para na 1ª que acha)


async def test_segundo_item_e_procurado_na_loja_do_primeiro(monkeypatch):
    """A′F1: mesmo que a busca na cidade traga o refri só de outra loja, o Match procura o refri dentro da pizzaria
    da pizza (searchOffers + refinements.merchantId) e o pedido sai de 1 loja só."""
    original = busca_mod.buscar_detalhado

    async def sem_refri_da_pizzaria(cliente, intencao, endereco, **kw):
        cands, det = await original(cliente, intencao, endereco, **kw)
        if intencao.participante_id.endswith("#2"):  # simula a busca da cidade sem o refri da pizzaria
            cands = [c for c in cands if c.loja_id != "loja-demo-pizza"]
        return cands, det

    monkeypatch.setattr(motor_mod, "buscar_detalhado", sem_refri_da_pizzaria)
    r = await _rodar([Desejo("ana", "Ana", "uma pizza e um refri")])
    melhor = r["combinacoes"][0]
    assert melhor["lojas"] == ["loja-demo-pizza"]
    assert melhor["escolhas"]["ana#2"]["item_id"] == "pz-refri"
    assert any(c["tool"] == "searchOffers" and "merchantId" in json.dumps(c, ensure_ascii=False) for c in r["rastro"])


async def test_taxa_da_busca_entra_no_custo_e_avisa_que_e_estimada():
    """A′F4: a taxa de entrega que o searchOffers devolve entra no custo antes do carrinho."""
    r = await _rodar([Desejo("ana", "Ana", "uma pizza e um refri")])
    melhor = r["combinacoes"][0]
    assert melhor["taxa_conhecida"] is True
    assert melhor["componentes"]["custo_total"] == round(24.90 + 14.90 + 8.99, 2)
    assert "com taxa" in melhor["explicacao"]
    assert any("taxa de entrega veio da busca do iFood (estimada)" in a for a in r["avisos"])
    assert not any("só aparece no carrinho" in a for a in r["avisos"])


# ---------- Só eu além de restaurante (A′F5) ----------
@pytest.mark.parametrize("texto, loja, itens", [
    ("dipirona e protetor solar", "loja-demo-farmacia", {"fm-dipirona", "fm-protetor"}),
    ("ração de cachorro e um petisco", "loja-demo-pet", {"pt-racao-cao", "pt-petisco"}),
    ("preciso fazer compras: arroz, feijão e detergente", "loja-demo-mercado", {"mc-arroz", "mc-feijao", "mc-detergente"}),
    ("preciso de shampoo, pasta de dente e pilha", "loja-demo-farmacia", {"fm-shampoo", "fm-pasta", "fm-pilha"}),
])
async def test_lista_de_compras_sai_de_uma_loja_da_categoria_certa(texto, loja, itens):
    r = await _rodar([Desejo("ana", "Ana", texto)])
    melhor = r["combinacoes"][0]
    assert melhor["lojas"] == [loja]
    assert {e["item_id"] for e in melhor["escolhas"].values()} == itens
    buscas = [c for c in r["rastro"] if c["tool"] == "searchOffers"]
    assert any("merchantType=" in c["resumo"] for c in buscas)  # a busca do varejo vai direto na categoria


async def test_produto_que_nao_existe_no_varejo_nao_vira_opcao_aproximada():
    r = await _rodar([Desejo("ana", "Ana", "dipirona e areia de praia")])
    assert "Não achei areia de praia para Ana." in r["avisos"]
    assert not any("opção mais próxima" in a for a in r["avisos"])
    assert "browseOffers" not in [c["tool"] for c in r["rastro"]]


# ---------- combos (A′F3) ----------
@pytest.mark.parametrize("texto", ["hambúrguer com batata e refri", "quero um combo de hambúrguer com refri"])
async def test_combo_da_loja_atende_varios_itens_da_pessoa_com_um_item_so(texto):
    """Regressão: "hambúrguer com batata e refri" virava lanche + batata + combo (que já tinha os dois); "combo de
    hambúrguer com refri" trazia o refri de outra loja."""
    r = await _rodar([Desejo("ana", "Ana", texto)])
    melhor = r["combinacoes"][0]
    assert [e["item_id"] for e in melhor["escolhas"].values()] == ["bg-combo"]
    assert set(melhor["cobertos"]) == {s for s in ("ana#2", "ana#3") if s in {i["participante_id"] for i in r["intencoes"]}}
    assert melhor["componentes"]["slots_fora"] == 0 and melhor["afinidade"] > 0
    assert melhor["escolhas"]["ana"]["motivo"].startswith("Combo com ")
    assert not any("ficou de fora" in a or "Não achei" in a for a in r["avisos"])


async def test_sem_combo_na_loja_os_itens_continuam_avulsos():
    r = await _rodar([Desejo("ana", "Ana", "uma pizza e um refri")])
    melhor = r["combinacoes"][0]
    assert melhor["cobertos"] == {} and len(melhor["escolhas"]) == 2


async def test_busca_na_loja_vai_nas_lojas_de_melhor_nota_e_preco_do_primeiro_item(monkeypatch):
    """Bug 30 (P8, MCP real): a pizza escolhida (a mais barata, nota igual) era de uma loja que vinha em 3º lugar na
    busca; o refri nunca era procurado nela. Agora as lojas do 1º item são ordenadas por nota e preço."""
    def c(slot, loja, preco, nota=0.9):
        return Candidato(slot, loja, loja, f"{loja}-{slot}", "Pizza", preco, 40, "RESTAURANT", False, nota=nota)

    principal = [c("ana", "L1", 40.0), c("ana", "L2", 35.0), c("ana", "L3", 30.0), c("ana", "L4", 8.99),
                 c("ana", "L5", 5.0, nota=0.3)]
    chamadas: list[str] = []

    async def espiao(cliente, intencao, endereco, loja_id, vertical=""):
        chamadas.append(loja_id)
        return [], {}

    monkeypatch.setattr(motor_mod, "buscar_na_loja", espiao)
    slots = [(Desejo("ana", "Ana", "pizza e um refri"), Intencao("ana", consultas=["pizza"])),
             (Desejo("ana", "Ana", "pizza e um refri"), Intencao("ana#2", consultas=["refri"]))]
    await motor_mod._completar_na_mesma_loja(None, slots, [([], {}), ([], {})], [principal, []], {})
    assert chamadas == ["L4", "L3", "L2"]


# ---------- mensagens honestas (bugs 31 e 32, P8/P9 no MCP real) ----------
def _cliente_com(cli, troca):
    """Embrulha `cli.chamar`: `troca(tool, resposta)` muda a resposta; levanta ErroMCP registrado no rastro."""
    original = cli.chamar

    async def chamar(tool, **args):
        return troca(tool, await original(tool, **args))

    cli.chamar = chamar
    return cli


async def test_ifood_fora_do_ar_nao_culpa_o_pedido():
    """Bug 31: com INTERNAL em todas as buscas, a mensagem dizia "aumente o orçamento"."""
    from app.ifood_mcp import ErroMCP
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        original = cli.chamar

        async def chamar(tool, **args):
            if tool in ("searchOffers", "browseOffers", "getMerchant"):
                cli._registrar(tool, tool, 0.0, ok=False, erro="INTERNAL")
                raise ErroMCP("INTERNAL: upstream service")
            return await original(tool, **args)

        cli.chamar = chamar
        r = await rodar_match(cfg, cli, ROTEIRO)
    assert r["problema"] == "ifood" and r["combinacoes"] == []
    assert any("O iFood não respondeu" in a for a in r["avisos"])
    assert not any("orçamento" in a or "Não achei" in a for a in r["avisos"])


async def test_loja_fechada_diz_que_esta_fechada_e_nao_pede_mais_orcamento():
    """Bug 32: de madrugada o iFood acha a dipirona, mas toda loja vem isOpen: false."""
    def fechar(tool, resposta):
        if tool in ("searchOffers", "browseOffers"):
            for r in resposta.get("results") or []:
                r["isOpen"] = False
        return resposta

    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        r = await rodar_match(cfg, _cliente_com(cli, fechar), [Desejo("ana", "Ana", "dipirona e protetor solar")])
    assert r["combinacoes"] == []
    assert any("Drogaria Bem Estar (demo)" in a and "fechadas agora" in a for a in r["avisos"])
    assert "Tente de novo quando as lojas abrirem." in r["avisos"]
    assert not any("orçamento" in a for a in r["avisos"])


# ---------- rodada exploratória do agente do Zenon (18/10 ~04h) ----------
@pytest.mark.parametrize("texto, loja, itens", [
    ("2 pizzas e 2 cocas", "loja-demo-pizza", ["pz-refri", "pz-refri"]),       # o mesmo pedido repetido vale 2×
    ("quero um x-salada com fritas", "loja-demo-burger", ["bg-batata"]),        # "x-salada" não vira salada
    ("um açaí e uma água", "loja-demo-acai", ["ac-agua"]),
    ("sushi e uma cerveja", "loja-demo-japones", ["jp-cerveja"]),
])
async def test_frases_da_rodada_exploratoria(texto, loja, itens):
    r = await _rodar([Desejo("ana", "Ana", texto)])
    melhor = r["combinacoes"][0]
    assert melhor["lojas"] == [loja]
    ids = [e["item_id"] for e in melhor["escolhas"].values()]
    for item in itens:
        assert ids.count(item) >= itens.count(item)


async def test_nada_achado_nao_culpa_o_orcamento_e_pao_de_queijo_nao_vira_hamburguer():
    r = await _rodar([Desejo("ana", "Ana", "vinho e gelo")])
    assert r["combinacoes"] == [] and not any("orçamento" in a for a in r["avisos"])
    r = await _rodar([Desejo("ana", "Ana", "um pão de queijo")])
    assert not r["combinacoes"] or "Smash" not in str(r["combinacoes"][0]["escolhas"])
    assert any("Não achei pão de queijo" in a for a in r["avisos"])



def test_bebida_pelo_nome_nao_vira_opcao_aproximada_de_comida():
    """Bug 35 (P11, MCP real às 05h): sem pizza aberta, "Coca-Cola Original 350ml" (achada na busca da loja, sem
    categoria) virou a "opção mais próxima" da pizza. O nome basta para saber que é bebida; combo não conta."""
    from app.match.juiz import bebida_sem_pedir

    pizza = Intencao("p", consultas=["pizza"])
    for nome in ("Coca-Cola Original 350ml", "Refrigerante Coca-Cola Lata 350ml", "Guarana Antartica2lt",
                 "Suco de laranja 500 ml"):
        assert bebida_sem_pedir(pizza, {}, nome), nome
    for nome in ("Pizza de calabresa", "Combo X-salada + refri", "X-Bacon + Coca 350ml", "Frango tudo"):
        assert not bebida_sem_pedir(pizza, {}, nome), nome
    assert not bebida_sem_pedir(Intencao("p", consultas=["coca"]), {}, "Coca-Cola Original 350ml")
