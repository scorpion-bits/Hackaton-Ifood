"""Ajustar com o Match (C14): intérprete do ajuste (fallback e validação do LLM) e a rota POST /ajustar."""

import pytest
from fastapi.testclient import TestClient

from app import config, rotas_match
from app.ifood_mcp import resetar_demo
from app.main import app
from app.match import ajuste
from app.match.ajuste import Mudanca, interpretar_ajuste, interpretar_fallback, validar_resposta_llm

MSG_422 = 'Não entendi quem ou o quê. Ex.: "troca o sorvete do Milan por açaí"'

PARTICIPANTES = [
    {"id": "t", "nome": "Thales", "organizador": True, "respondeu": False, "texto": None, "orcamento_max": None},
    {"id": "m", "nome": "Milan", "texto": "japonês e um sorvete, até R$ 45", "orcamento_max": 45},
    {"id": "z", "nome": "Zenon", "texto": "hambúrguer e sorvete, até R$ 50", "orcamento_max": 50},
    {"id": "a", "nome": "Antônio", "texto": "algo barato e vegetariano, até R$ 25", "orcamento_max": 25},
]


def entender(frase: str, participantes=PARTICIPANTES) -> dict[str, Mudanca]:
    return {m.participante_id: m for m in interpretar_fallback(frase, participantes)}


# ---------- fallback: padrões ----------
def test_troca_x_do_fulano_por_y_mantem_o_resto_do_desejo():
    mud = entender("troca o sorvete do Milan por açaí")
    assert list(mud) == ["m"]
    assert mud["m"].novo_texto == "japonês e um açaí, até R$ 45"
    assert mud["m"].novo_orcamento is None
    assert mud["m"].resumo == "Milan: açaí no lugar do sorvete"


def test_troca_sem_acento_e_caixa_e_com_sinonimo_da_categoria():
    assert entender("TROCAR O SORVETE DO MILAN POR ACAI")["m"].novo_texto == "japonês e um acai, até R$ 45"
    assert entender("troca o sorvete do milan por AÇAÍ")["m"].novo_texto == "japonês e um açaí, até R$ 45"
    # "sushi" não está no texto, mas é da mesma categoria de "japonês"
    mud = entender("troca o sushi do Milan por poke")
    assert mud["m"].novo_texto == "poke e um sorvete, até R$ 45"
    assert mud["m"].resumo == "Milan: poke no lugar do japonês"


def test_nome_acentuado_casa_com_ou_sem_acento():
    for frase in ("Antonio quer pizza", "antônio quer pizza", "ANTÔNIO quer pizza"):
        mud = entender(frase)
        assert list(mud) == ["a"], frase
        # o desejo vira pizza, mas a restrição e o orçamento escritos continuam
        assert mud["a"].novo_texto == "pizza, vegetariano, até R$ 25"
        assert mud["a"].resumo == "Antônio: agora quer pizza"


def test_troca_de_item_que_nao_esta_no_texto_vira_o_novo_desejo_mantendo_orcamento():
    mud = entender("troca o pastel do Milan por açaí")
    assert mud["m"].novo_texto == "açaí, até R$ 45"
    assert mud["m"].resumo == "Milan: agora quer açaí"


def test_fulano_quer_e_pro_fulano():
    assert entender("Milan quer pizza")["m"].novo_texto == "pizza, até R$ 45"
    mud = entender("pro Zenon uma coxinha")  # termo livre vale com "pro Fulano"
    assert mud["z"].novo_texto == "coxinha, até R$ 50"
    assert mud["z"].resumo == "Zenon: agora quer coxinha"


def test_mais_barato_pra_todo_mundo_acrescenta_a_palavra_sem_inventar_valor():
    mud = entender("mais barato pra todo mundo")
    assert set(mud) == {"m", "z", "a"}  # o organizador não respondeu: fica de fora
    assert mud["m"].novo_texto == "japonês e um sorvete, mais barato, até R$ 45"
    assert all(m.novo_orcamento is None for m in mud.values())
    assert mud["z"].resumo == "Zenon: opção mais barata"
    # ajuste seguinte troca o marcador em vez de empilhar
    texto = mud["m"].novo_texto
    outro = interpretar_fallback("mais rápido pro Milan", [{"id": "m", "nome": "Milan", "texto": texto}])
    assert outro[0].novo_texto == "japonês e um sorvete, mais rápido, até R$ 45"
    assert outro[0].resumo == "Milan: entrega mais rápida"


def test_sem_x_pra_fulano():
    mud = entender("sem cebola pro Zenon")
    assert mud["z"].novo_texto == "hambúrguer e sorvete, sem cebola, até R$ 50"
    assert mud["z"].resumo == "Zenon: sem cebola"
    assert entender("Antonio sem lactose")["a"].novo_texto.endswith("sem lactose, até R$ 25")


def test_tira_x_do_fulano_remove_o_trecho_e_recusa_se_esvaziar():
    mud = entender("tira o sorvete do Milan")
    assert mud["m"].novo_texto == "japonês, até R$ 45"
    assert mud["m"].resumo == "Milan: sem sorvete"
    assert entender("tira o japonês do Milan")["m"].novo_texto == "um sorvete, até R$ 45"
    # tirar o único desejo de verdade esvaziaria o pedido → recusa
    assert entender("tira o vegetariano do Antonio") == {}
    assert interpretar_fallback("tira a pizza da Ana", [{"id": "x", "nome": "Ana", "texto": "pizza"}]) == []


def test_ate_n_e_orcamento_de_n():
    mud = entender("até 30 pro Zenon")
    assert mud["z"].novo_orcamento == 30
    assert mud["z"].novo_texto == "hambúrguer e sorvete, até R$ 30"  # o texto não fica dizendo outro valor
    assert mud["z"].resumo == "Zenon: orçamento até R$ 30"
    assert entender("orçamento de 60 pro Antonio")["a"].novo_orcamento == 60
    # fora de 1..1000 → não aplica
    assert entender("até 5000 pro Zenon") == {}


def test_pra_mim_e_eu_sao_o_organizador():
    participantes = [{"id": "t", "nome": "Thales", "organizador": True, "texto": "pizza"},
                     {"id": "m", "nome": "Milan", "texto": "sushi"}]
    assert interpretar_fallback("pra mim açaí", participantes)[0].participante_id == "t"
    assert interpretar_fallback("eu quero hambúrguer", participantes)[0].novo_texto == "hambúrguer"
    assert interpretar_fallback("troca a minha pizza por sushi", participantes)[0].novo_texto == "sushi"
    # organizador que ainda não respondeu não é ajustado, nem a frase cai em outra pessoa
    assert entender("pra mim açaí") == {}
    assert entender("Thales quer pizza") == {}


def test_uma_pessoa_so_dispensa_o_nome():
    so_milan = [PARTICIPANTES[0], PARTICIPANTES[1]]
    mud = entender("troca o sorvete por açaí", so_milan)
    assert mud["m"].novo_texto == "japonês e um açaí, até R$ 45"
    # com várias pessoas e sem nome: não adivinha
    assert entender("troca o sorvete por açaí") == {}


def test_varios_comandos_e_varias_pessoas_numa_frase():
    mud = entender("troca o sorvete do Zenon e do Milan por açaí")
    assert mud["z"].novo_texto == "hambúrguer e açaí, até R$ 50"
    assert mud["m"].novo_texto == "japonês e um açaí, até R$ 45"
    mud = entender("Milan quer açaí e Zenon quer pizza")
    assert mud["m"].novo_texto == "açaí, até R$ 45" and mud["z"].novo_texto == "pizza, até R$ 50"
    mud = entender("troca o sorvete do Milan por açaí e batata")
    assert mud["m"].novo_texto == "japonês e um açaí e batata, até R$ 45"
    # o segundo comando sem nome vale para a mesma pessoa
    mud = entender("troca o sorvete do Milan por açaí, e mais barato")
    assert mud["m"].resumo == "Milan: açaí no lugar do sorvete; opção mais barata"
    # "de todo mundo": só muda quem tem sorvete
    mud = entender("troca o sorvete de todo mundo por açaí")
    assert set(mud) == {"m", "z"}


def test_por_favor_e_orcamento_junto():
    mud = entender("por favor, troca o sorvete do milan por açaí até 40")
    assert mud["m"].novo_texto == "japonês e um açaí, até R$ 40"
    assert mud["m"].novo_orcamento == 40


def test_frases_que_nao_entende():
    for frase in ("o Milan é legal", "Milan não vem mais", "troca o sorvete do Milan", "bom dia", "", "   "):
        assert entender(frase) == {}, frase


# ---------- LLM: validação ----------
async def test_llm_valido_e_usado(monkeypatch):
    async def llm(cfg, sistema, usuario, timeout=None, max_tokens=None):
        assert "Milan" in usuario and "japonês e um sorvete" in usuario
        return {"mudancas": [{"participante_id": "m", "novo_texto": "japonês e um açaí, até R$ 45",
                              "novo_orcamento": None, "resumo": "açaí no lugar do sorvete"}]}

    monkeypatch.setattr(ajuste, "completar_json", llm)
    mud = await interpretar_ajuste(config.carregar(), "o Milan prefere açaí", PARTICIPANTES)
    assert mud == [Mudanca("m", "japonês e um açaí, até R$ 45", None, "Milan: açaí no lugar do sorvete")]


@pytest.mark.parametrize("resposta", [
    {"mudancas": [{"participante_id": "fantasma", "novo_texto": "pizza", "resumo": "x"}]},  # pessoa inexistente
    {"mudancas": [{"participante_id": "t", "novo_texto": "pizza", "resumo": "x"}]},  # não respondeu
    {"mudancas": [{"participante_id": "m", "novo_texto": "açaí", "novo_orcamento": 99}]},  # número fora da frase
    {"mudancas": [{"participante_id": "m", "novo_texto": "açaí", "novo_orcamento": "barato"}]},
    {"mudancas": [{"participante_id": "m", "novo_texto": "x" * 200}]},  # texto longo demais
    {"mudancas": "Milan"},
    None,
])
async def test_llm_invalido_e_descartado_e_o_fallback_entende(monkeypatch, resposta):
    async def llm(cfg, sistema, usuario, timeout=None, max_tokens=None):
        return resposta

    monkeypatch.setattr(ajuste, "completar_json", llm)
    mud = await interpretar_ajuste(config.carregar(), "troca o sorvete do Milan por açaí", PARTICIPANTES)
    assert [(m.participante_id, m.novo_texto, m.novo_orcamento) for m in mud] == \
        [("m", "japonês e um açaí, até R$ 45", None)]


def test_validacao_aceita_orcamento_escrito_na_frase():
    dados = {"mudancas": [{"participante_id": "z", "novo_texto": None, "novo_orcamento": 30, "resumo": "até 30"}]}
    mud = validar_resposta_llm(dados, "Zenon até 30", PARTICIPANTES)
    assert mud == [Mudanca("z", PARTICIPANTES[2]["texto"], 30.0, "Zenon: até 30")]
    dados["mudancas"][0]["novo_orcamento"] = 0
    assert validar_resposta_llm(dados, "Zenon até 0", PARTICIPANTES) is None


# ---------- rota ----------
DESEJOS = {
    "Milan": {"texto": "japonês e um sorvete, até R$ 45", "orcamento_max": 45, "chips": []},
    "Zenon": {"texto": "hambúrguer e sorvete, até R$ 50", "orcamento_max": 50, "chips": []},
    "Antonio": {"texto": "algo barato e vegetariano, até R$ 25", "orcamento_max": 25, "chips": ["vegetariano"]},
}


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


@pytest.fixture
def c():
    with TestClient(app) as cliente:
        yield cliente


def sala_com_match(c, rodar=True):
    r = c.post("/api/salas", json={"organizador_nome": "Thales"}).json()
    sid, org = r["sala_id"], {"X-Organizador": r["token_organizador"]}
    pids = {}
    for nome, desejo in DESEJOS.items():
        pids[nome] = c.post(f"/api/salas/{sid}/participantes", json={"nome": nome}).json()["participante_id"]
        assert c.put(f"/api/salas/{sid}/participantes/{pids[nome]}/desejo", json=desejo).status_code == 200
    if rodar:
        assert c.post(f"/api/salas/{sid}/rodar", headers=org).status_code == 200
    return sid, org, pids


def itens_de(resultado: dict, pid: str) -> list[str]:
    return [e["item_nome"] for slot, e in resultado["combinacoes"][0]["escolhas"].items()
            if slot.split("#", 1)[0] == pid]


def test_rota_ajustar_roteiro_roda_o_match_de_novo_e_grava_o_ajuste(c):
    sid, org, pids = sala_com_match(c)
    antes = c.get(f"/api/salas/{sid}").json()
    assert antes["ajustes"] == []
    assert any("Sundae" in i for i in itens_de(antes["resultado"], pids["Zenon"]))

    frase = "troca o sorvete do Milan e do Zenon por açaí"
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": frase}, headers=org)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["entendido"] == [
        {"participante_id": pids["Milan"], "nome": "Milan", "resumo": "Milan: açaí no lugar do sorvete"},
        {"participante_id": pids["Zenon"], "nome": "Zenon", "resumo": "Zenon: açaí no lugar do sorvete"},
    ]
    resultado = corpo["resultado"]
    assert resultado["combinacoes"] and resultado["rastro"]
    assert any("Açaí" in i for i in itens_de(resultado, pids["Zenon"]))
    assert not any("Sundae" in i for i in itens_de(resultado, pids["Zenon"]))

    depois = c.get(f"/api/salas/{sid}").json()
    assert depois["estado"] == "match_pronto"
    assert depois["resultado"]["combinacoes"] == resultado["combinacoes"]
    assert len(depois["ajustes"]) == 1
    assert depois["ajustes"][0]["texto"] == frase
    assert depois["ajustes"][0]["entendido"] == corpo["entendido"]
    assert depois["ajustes"][0]["em"].endswith("Z")
    from app.match import salas
    milan = salas.participante(salas.obter(sid), pids["Milan"])
    assert milan["desejo"]["texto"] == "japonês e um açaí, até R$ 45"
    # dá para seguir o fluxo: escolher depois do ajuste
    assert c.post(f"/api/salas/{sid}/escolher", json={"combinacao": 0, "modo_pagamento": "junto"},
                  headers=org).status_code == 200


def test_rota_ajustar_exemplo_do_contrato(c):
    sid, org, pids = sala_com_match(c)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"}, headers=org)
    assert r.status_code == 200, r.text
    assert r.json()["entendido"][0]["resumo"] == "Milan: açaí no lugar do sorvete"


def test_rota_ajustar_orcamento_grava_no_desejo(c):
    sid, org, pids = sala_com_match(c)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "até 40 pro Zenon"}, headers=org)
    assert r.status_code == 200, r.text
    from app.match import salas
    zenon = salas.participante(salas.obter(sid), pids["Zenon"])
    assert zenon["desejo"]["orcamento_max"] == 40
    assert zenon["desejo"]["texto"] == "hambúrguer e sorvete, até R$ 40"


def test_rota_ajustar_guarda_so_os_ultimos_10(c):
    sid, org, _ = sala_com_match(c)
    for i in range(12):
        frase = "mais barato pro Milan" if i % 2 else "mais rápido pro Milan"
        assert c.post(f"/api/salas/{sid}/ajustar", json={"texto": frase}, headers=org).status_code == 200
    ajustes = c.get(f"/api/salas/{sid}").json()["ajustes"]
    assert len(ajustes) == 10 and ajustes[-1]["texto"] == "mais barato pro Milan"


def test_rota_ajustar_exige_o_organizador(c):
    sid, org, _ = sala_com_match(c)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"})
    assert r.status_code == 403
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"},
               headers={"X-Organizador": "errado"})
    assert r.status_code == 403
    assert c.get(f"/api/salas/{sid}").json()["ajustes"] == []


def test_rota_ajustar_so_em_match_pronto(c):
    sid, org, _ = sala_com_match(c, rodar=False)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"}, headers=org)
    assert r.status_code == 409
    assert r.json()["detail"] == "Não dá para ajustar o pedido agora: a sala está recebendo os desejos."
    # depois de escolher também não
    assert c.post(f"/api/salas/{sid}/rodar", headers=org).status_code == 200
    assert c.post(f"/api/salas/{sid}/escolher", json={"combinacao": 0, "modo_pagamento": "separado"},
                  headers=org).status_code == 200
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"}, headers=org)
    assert r.status_code == 409 and "aguardando os pagamentos" in r.json()["detail"]


def test_rota_ajustar_nao_entendeu_e_422(c):
    sid, org, _ = sala_com_match(c)
    antes = c.get(f"/api/salas/{sid}").json()
    for frase in ("bom dia", "troca o sorvete por açaí", "Thales quer pizza"):
        r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": frase}, headers=org)
        assert r.status_code == 422, frase
        assert r.json() == {"detail": MSG_422}
    assert c.post(f"/api/salas/{sid}/ajustar", json={"texto": "  "}, headers=org).status_code == 400
    depois = c.get(f"/api/salas/{sid}").json()
    assert depois["resultado"] == antes["resultado"] and depois["ajustes"] == []


def test_rota_ajustar_sem_combinacao_e_409_e_a_sala_volta_ao_anterior(c, monkeypatch):
    sid, org, pids = sala_com_match(c)
    from app.match import salas
    antes_pub = c.get(f"/api/salas/{sid}").json()
    antes_desejos = [p["desejo"] for p in salas.obter(sid)["participantes"]]

    async def nada(cfg, cliente, desejos):
        assert any(d.texto == "japonês e um açaí, até R$ 45" for d in desejos)  # rodou com o desejo novo
        return {"combinacoes": [], "avisos": ["Não achei açaí até R$ 45 para Milan."], "rastro": []}

    monkeypatch.setattr(rotas_match.motor, "rodar_match", nada)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete do Milan por açaí"}, headers=org)
    assert r.status_code == 409
    assert r.json()["detail"].startswith("O Match não encontrou um pedido que sirva para todos.")
    assert "Não achei açaí" in r.json()["detail"]

    depois_pub = c.get(f"/api/salas/{sid}").json()
    assert depois_pub["estado"] == "match_pronto"
    assert depois_pub["resultado"] == antes_pub["resultado"]
    assert depois_pub["ajustes"] == []
    assert [p["desejo"] for p in salas.obter(sid)["participantes"]] == antes_desejos


def test_rota_ajustar_erro_do_ifood_mantem_a_sala(c, monkeypatch):
    from app.ifood_mcp.cliente import ErroMCP

    sid, org, _ = sala_com_match(c)
    antes = c.get(f"/api/salas/{sid}").json()

    async def quebra(cfg, cliente, desejos):
        raise ErroMCP("searchOffers falhou (500)")

    monkeypatch.setattr(rotas_match.motor, "rodar_match", quebra)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "Milan quer pizza"}, headers=org)
    assert r.status_code == 502 and r.json()["detail"].startswith("O iFood respondeu com erro:")
    depois = c.get(f"/api/salas/{sid}").json()
    assert depois["resultado"] == antes["resultado"] and depois["ajustes"] == []


def test_rodar_continua_igual_depois_da_refatoracao(c):
    sid, org, _ = sala_com_match(c, rodar=False)
    r = c.post(f"/api/salas/{sid}/rodar", headers=org)
    assert r.status_code == 200 and r.json()["combinacoes"] and r.json()["rastro"]


def test_troca_sem_nome_acha_o_dono_do_item():
    from app.match.ajuste import interpretar_fallback
    participantes = [
        {"id": "a", "nome": "Milan", "texto": "japonês e um açaí", "respondeu": True, "organizador": True},
        {"id": "b", "nome": "Zenon", "texto": "pizza e um sorvete", "respondeu": True},
    ]
    m = interpretar_fallback("troca o sorvete por açaí", participantes)
    assert len(m) == 1 and "açaí" in m[0].novo_texto and "sorvete" not in m[0].novo_texto


def test_sala_de_1_pessoa_nao_usa_nome_de_outro_no_exemplo_nem_para_todos(c, monkeypatch):
    r = c.post("/api/salas", json={"organizador_nome": "Thales"}).json()
    sid, org = r["sala_id"], {"X-Organizador": r["token_organizador"]}
    pid = c.post(f"/api/salas/{sid}/participantes", json={"nome": "Ana"}).json()["participante_id"]
    assert c.put(f"/api/salas/{sid}/participantes/{pid}/desejo", json=DESEJOS["Milan"]).status_code == 200
    assert c.post(f"/api/salas/{sid}/rodar", headers=org).status_code == 200
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "bom dia"}, headers=org)
    assert r.status_code == 422 and r.json() == {"detail": rotas_match.MSG_AJUSTE_NAO_ENTENDIDO_1}

    async def nada(cfg, cliente, desejos):
        return {"combinacoes": [], "avisos": ["Nada serve."], "rastro": []}

    monkeypatch.setattr(rotas_match.motor, "rodar_match", nada)
    r = c.post(f"/api/salas/{sid}/ajustar", json={"texto": "troca o sorvete por açaí"}, headers=org)
    assert r.status_code == 409 and r.json()["detail"].startswith("O Match não encontrou um pedido para você.")
