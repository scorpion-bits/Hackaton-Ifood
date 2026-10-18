"""API da sala do Match (C7): fluxo inteiro com TestClient, MCP de demonstração e LLM mock."""

import json

import pytest
from fastapi.testclient import TestClient

from app import rotas_match
from app.ifood_mcp import resetar_demo
from app.main import app
from app.match import checkout, salas
from app.match.acerto import centavos
from app.match.checkout import ErroCheckout
from app.match.pix import crc16_ccitt_false, ler_campos

CHAVE = "milan.pix@example.com"
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


class Sala:
    """Atalhos para o fluxo (o cliente HTTP já tem lifespan/portal único)."""

    def __init__(self, c: TestClient, chave: str | None = CHAVE, organizador: str = "Thales"):
        self.c = c
        r = c.post("/api/salas", json={"organizador_nome": organizador, "chave_pix": chave})
        assert r.status_code == 200, r.text
        dados = r.json()
        self.id, self.token = dados["sala_id"], dados["token_organizador"]
        assert dados["link_convite"] == f"#/s/{self.id}"
        self.org = {"X-Organizador": self.token}
        self.pids: dict[str, str] = {}

    def url(self, caminho: str = "") -> str:
        return f"/api/salas/{self.id}{caminho}"

    def estado(self) -> dict:
        r = self.c.get(self.url())
        assert r.status_code == 200, r.text
        return r.json()

    def convidar(self, desejos: dict | None = None) -> None:
        for nome, desejo in (desejos or DESEJOS).items():
            pid = self.c.post(self.url("/participantes"), json={"nome": nome}).json()["participante_id"]
            self.pids[nome] = pid
            r = self.c.put(self.url(f"/participantes/{pid}/desejo"), json=desejo)
            assert r.json() == {"ok": True}

    def rodar(self):
        return self.c.post(self.url("/rodar"), headers=self.org)

    def escolher(self, modo: str = "separado", combinacao: int = 0):
        return self.c.post(self.url("/escolher"), json={"combinacao": combinacao, "modo_pagamento": modo},
                           headers=self.org)

    def pagar(self, pid: str, forma: str):
        return self.c.post(self.url(f"/pagamentos/{pid}"), json={"forma": forma})

    def recebi(self, pid: str):
        return self.c.post(self.url(f"/pagamentos/{pid}/recebi"), headers=self.org)

    def resolver(self, pid: str, acao: str):
        return self.c.post(self.url(f"/pagamentos/{pid}/resolver"), json={"acao": acao}, headers=self.org)

    def enviar(self, confirmo=True):
        return self.c.post(self.url("/enviar"), json={"confirmo": confirmo}, headers=self.org)

    def pronta_para_escolher(self) -> dict:
        self.convidar()
        r = self.rodar()
        assert r.status_code == 200, r.text
        return r.json()


def soma_partes(estado: dict) -> int:
    return sum(centavos(p["total"]) for p in estado["partes"])


def soma_carrinhos(estado: dict) -> int:
    return sum(centavos(k["total"]) for k in estado["carrinhos"])


# ---------- fluxo inteiro ----------
def test_fluxo_completo_separado_ate_o_pedido_concluido(c):
    s = Sala(c)
    inicial = s.estado()
    assert inicial["estado"] == "coletando" and inicial["demonstracao"] is True
    assert [p["nome"] for p in inicial["participantes"]] == ["Thales"]  # organizador é participantes[0]
    assert inicial["organizador_id"] == inicial["participantes"][0]["id"]

    s.convidar()
    estado = s.estado()
    assert [p["nome"] for p in estado["participantes"]] == ["Thales", "Milan", "Zenon", "Antonio"]
    assert [p["respondeu"] for p in estado["participantes"]] == [False, True, True, True]

    resultado = s.rodar().json()
    assert 1 <= len(resultado["combinacoes"]) <= 3
    assert [p["participante_id"] for p in resultado["pessoas"]] == list(s.pids.values())
    assert resultado["rastro"], "o rastro das tools MCP vem junto"
    estado = s.estado()
    assert estado["estado"] == "match_pronto"
    assert len(estado["rastro"]) >= len(resultado["rastro"])

    r = s.escolher("separado")
    assert r.status_code == 200, r.text
    estado = s.estado()
    assert estado["estado"] == "aguardando_pagamentos" and estado["modo_pagamento"] == "separado"
    assert estado["prazo_fim"].endswith("Z") and len(estado["prazo_fim"]) == 20
    # as partes batem com o total dos carrinhos, ao centavo
    assert soma_partes(estado) == soma_carrinhos(estado) > 0
    pids = [p["participante_id"] for p in estado["partes"]]
    assert set(pids) == set(s.pids.values())  # os 3 convidados têm parte; o organizador não pediu nada
    assert all(estado["pagamentos"][pid] == {"forma": None, "status": "pendente"} for pid in pids)

    # enviar antes de 100% pago → 409
    r = s.enviar()
    assert r.status_code == 409 and "aguardando os pagamentos" in r.json()["detail"]

    # Pix (BR Code válido) · cartão simulado · dinheiro
    pix_pid, cartao_pid, dinheiro_pid = pids[0], pids[1], pids[2]
    r = s.pagar(pix_pid, "pix").json()
    assert r["status"] == "aguardando_confirmacao"
    codigo = r["pix_copia_e_cola"]
    assert crc16_ccitt_false(codigo[:-4]) == int(codigo[-4:], 16)
    campos = ler_campos(codigo)
    parte_pix = next(p for p in estado["partes"] if p["participante_id"] == pix_pid)
    assert campos["54"] == f"{parte_pix['total']:.2f}"
    assert campos["59"] == "THALES" and campos["60"] == "SAO CARLOS" and campos["58"] == "BR"
    conta = ler_campos(campos["26"])
    assert conta["00"] == "br.gov.bcb.pix" and conta["01"] == CHAVE

    r = s.pagar(cartao_pid, "cartao_simulado").json()
    assert r["status"] == "pago" and r["demonstracao"] is True
    assert s.pagar(dinheiro_pid, "dinheiro").json() == {"status": "aguardando_confirmacao"}

    estado = s.estado()
    assert estado["pagamentos"][pix_pid]["pix"] == codigo  # o front lê `pix` no polling
    assert estado["estado"] == "aguardando_pagamentos"
    assert s.recebi(pix_pid).json() == {"status": "pago"}
    assert s.enviar().status_code == 409  # falta o dinheiro
    assert s.recebi(dinheiro_pid).json() == {"status": "pago"}
    assert s.estado()["estado"] == "pronto_para_enviar"

    r = s.enviar()
    assert r.status_code == 200, r.text
    estado = s.estado()
    assert estado["estado"] == "enviado"
    assert len(estado["pedidos"]) == len(estado["carrinhos"])
    pedido = estado["pedidos"][0]
    assert {"order_id", "loja_id", "loja_nome", "total", "status", "itens"} <= pedido.keys()
    assert pedido["status"]["code"] == "SUBMITTED" and pedido["encerrado"] is False

    # acompanhar cada pedido até CONCLUDED
    for p in estado["pedidos"]:
        ultimo = None
        for _ in range(6):
            ultimo = s.c.post(s.url(f"/pedidos/{p['order_id']}/atualizar")).json()
            if ultimo["status"]["code"] == "CONCLUDED":
                break
        assert ultimo["status"]["code"] == ultimo["status_code"] == "CONCLUDED"
        assert ultimo["encerrado"] is True
    final = s.estado()
    assert {p["status"]["code"] for p in final["pedidos"]} == {"CONCLUDED"}
    # cada chamada ficou no rastro, com as tools do checkout
    tools = [r["tool"] for r in final["rastro"]]
    for t in ("searchOffers", "createCart", "setCartPayment", "submitOrder", "trackOrder"):
        assert t in tools


def test_modo_junto_vai_direto_para_pronto_e_envia(c):
    s = Sala(c, chave=None)
    s.pronta_para_escolher()
    assert s.escolher("junto").status_code == 200
    estado = s.estado()
    assert estado["estado"] == "pronto_para_enviar" and estado["modo_pagamento"] == "junto"
    assert estado["pagamentos"] == {} and estado["prazo_fim"] is None
    assert soma_partes(estado) == soma_carrinhos(estado)  # as partes servem para acertar depois
    assert s.pagar(s.pids["Milan"], "dinheiro").status_code == 409  # não há vaquinha no modo junto
    assert s.enviar().status_code == 200
    assert s.estado()["estado"] == "enviado"


def test_organizador_com_desejo_nasce_pago(c):
    s = Sala(c)
    # o id do organizador vem da criação da sala; um convidado com o mesmo nome NÃO vira o organizador
    pid_org = s.estado()["organizador_id"]
    impostor = c.post(s.url("/participantes"), json={"nome": "thales"}).json()["participante_id"]
    assert impostor != pid_org
    c.put(s.url(f"/participantes/{pid_org}/desejo"), json={"texto": "pizza até R$ 40", "chips": []})
    s.convidar({"Milan": DESEJOS["Milan"]})
    assert len(s.estado()["participantes"]) == 3
    assert s.rodar().status_code == 200
    assert s.escolher("separado").status_code == 200
    estado = s.estado()
    pag = estado["pagamentos"].get(pid_org)
    if pag:  # o organizador só tem parte se a combinação deu item a ele
        assert pag == {"forma": "organizador", "status": "pago"}
        assert s.pagar(pid_org, "dinheiro").status_code == 409


# ---------- segurança e regras ----------
def test_acoes_do_organizador_exigem_token(c):
    s = Sala(c)
    s.pronta_para_escolher()
    ruim = {"X-Organizador": "token-errado"}
    pid = s.pids["Milan"]
    for caminho, corpo in [
        ("/rodar", None),
        ("/escolher", {"combinacao": 0, "modo_pagamento": "junto"}),
        (f"/pagamentos/{pid}/recebi", None),
        (f"/pagamentos/{pid}/resolver", {"acao": "organizador_cobre"}),
        ("/enviar", {"confirmo": True}),
    ]:
        assert c.post(s.url(caminho), json=corpo).status_code == 403, caminho  # sem header
        assert c.post(s.url(caminho), json=corpo, headers=ruim).status_code == 403, caminho
    assert s.estado()["estado"] == "match_pronto"  # nada mudou


def test_maquina_de_estados_recusa_transicao_invalida_com_mensagem(c):
    s = Sala(c)
    r = s.rodar()  # ninguém respondeu
    assert r.status_code == 409 and "Ninguém respondeu" in r.json()["detail"]
    s.convidar()
    assert s.escolher().status_code == 409  # antes de rodar
    assert s.pagar(s.pids["Milan"], "dinheiro").status_code == 409
    assert s.enviar().status_code == 409
    assert s.rodar().status_code == 200
    assert s.rodar().status_code == 200  # pode rodar de novo enquanto em match_pronto
    # depois do Match ninguém entra nem muda o desejo
    assert c.post(s.url("/participantes"), json={"nome": "Atrasado"}).status_code == 409
    assert c.put(s.url(f"/participantes/{s.pids['Milan']}/desejo"),
                 json={"texto": "outra coisa", "chips": []}).status_code == 409
    assert s.escolher(combinacao=9).status_code == 400
    assert s.escolher(modo="qualquer").status_code == 400
    assert s.escolher("separado").status_code == 200
    assert s.rodar().status_code == 409 and "Não dá para" in s.rodar().json()["detail"]
    assert s.escolher("junto").status_code == 409


def test_enviar_exige_confirmo_e_100_por_cento_pago(c):
    s = Sala(c)
    s.pronta_para_escolher()
    s.escolher("junto")
    assert s.enviar(confirmo=False).status_code == 400
    assert s.enviar(confirmo="sim").status_code == 400
    assert c.post(s.url("/enviar"), json={}, headers=s.org).status_code == 400
    assert c.post(s.url("/enviar"), headers=s.org).status_code == 400
    assert s.estado()["estado"] == "pronto_para_enviar"  # nada foi enviado
    assert s.estado()["pedidos"] == []


def test_pix_sem_chave_e_pagamento_invalido(c):
    s = Sala(c, chave=None)
    s.pronta_para_escolher()
    s.escolher("separado")
    pid = s.estado()["partes"][0]["participante_id"]
    r = s.pagar(pid, "pix")
    assert r.status_code == 409 and "chave Pix" in r.json()["detail"]
    assert s.pagar(pid, "bitcoin").status_code == 400
    assert s.pagar("nao-existe", "dinheiro").status_code == 404
    assert s.recebi(pid).status_code == 409  # ainda não escolheu forma
    assert s.pagar(pid, "cartao_simulado").status_code == 200
    assert s.pagar(pid, "dinheiro").status_code == 409  # já pago


def test_criar_sala_valida_nome_e_chave(c):
    assert c.post("/api/salas", json={"organizador_nome": "  "}).status_code == 400
    r = c.post("/api/salas", json={"organizador_nome": "Thales", "chave_pix": "chave com acento ção"})
    assert r.status_code == 400 and "Pix" in r.json()["detail"]
    assert c.get("/api/salas/inexistente").status_code == 404


def test_get_nao_vaza_token_nem_chave_pix(c):
    s = Sala(c)
    bruto = json.dumps(s.estado())
    assert s.token not in bruto and CHAVE not in bruto
    estado = s.estado()
    assert estado["tem_chave_pix"] is True
    assert estado["chave_pix_mascarada"] and estado["chave_pix_mascarada"] != CHAVE
    assert "token" not in estado and "chave_pix" not in estado

    s.pronta_para_escolher()
    s.escolher("separado")
    pid = s.estado()["partes"][0]["participante_id"]
    s.pagar(pid, "pix")
    estado = s.estado()
    assert s.token not in json.dumps(estado)
    # a chave só aparece dentro do código Pix do pagador (por definição do BR Code), em nenhum outro lugar
    estado["pagamentos"][pid].pop("pix"), estado["pagamentos"][pid].pop("pix_copia_e_cola")
    assert CHAVE not in json.dumps(estado)
    # desejos de cada um e endereço completo também não são publicados
    assert "japonês e um sorvete" not in json.dumps(estado)
    assert "texto" not in estado["resultado"]["endereco"]


# ---------- resolver ----------
def test_resolver_organizador_cobre_libera_o_envio(c):
    s = Sala(c)
    s.pronta_para_escolher()
    s.escolher("separado")
    partes = s.estado()["partes"]
    for p in partes[:-1]:
        assert s.pagar(p["participante_id"], "cartao_simulado").status_code == 200
    ultimo = partes[-1]["participante_id"]
    assert s.estado()["estado"] == "aguardando_pagamentos"
    assert s.resolver(ultimo, "inexistente").status_code == 400
    assert s.resolver(ultimo, "organizador_cobre").status_code == 200
    estado = s.estado()
    assert estado["pagamentos"][ultimo] == {"forma": "organizador", "status": "pago"}
    assert estado["estado"] == "pronto_para_enviar"
    assert s.resolver(ultimo, "organizador_cobre").status_code == 409  # já pago
    assert s.enviar().status_code == 200


def test_resolver_remover_itens_recalcula_partes_e_carrinhos(c):
    s = Sala(c)
    s.pronta_para_escolher()
    s.escolher("separado")
    antes = s.estado()
    assert len(antes["partes"]) >= 2
    removido = antes["partes"][-1]["participante_id"]
    pagou = antes["partes"][0]["participante_id"]
    assert s.pagar(pagou, "cartao_simulado").status_code == 200
    ids_carrinhos_antes = {k["cart_id"] for k in antes["carrinhos"]}

    r = s.resolver(removido, "remover_itens")
    assert r.status_code == 200, r.text
    depois = s.estado()
    assert removido not in [p["participante_id"] for p in depois["partes"]]
    assert removido not in depois["pagamentos"]
    assert soma_partes(depois) == soma_carrinhos(depois) > 0
    assert soma_carrinhos(depois) < soma_carrinhos(antes)
    assert {k["cart_id"] for k in depois["carrinhos"]}.isdisjoint(ids_carrinhos_antes)  # carrinhos remontados
    assert all(i["participante_id"] != removido for k in depois["carrinhos"] for i in k["itens"])
    assert any("saíram do pedido" in a for a in depois["avisos"])

    # quem pagou um valor que não mudou continua pago; quem teve o valor alterado volta a pendente
    for parte in depois["partes"]:
        antigo = next((p for p in antes["partes"] if p["participante_id"] == parte["participante_id"]), None)
        pag = depois["pagamentos"][parte["participante_id"]]
        if parte["participante_id"] == pagou and antigo and centavos(antigo["total"]) != centavos(parte["total"]):
            assert pag["status"] == "pendente"
        elif parte["participante_id"] == pagou:
            assert pag["status"] == "pago"

    # termina o fluxo: todos pagam e envia
    for parte in depois["partes"]:
        if depois["pagamentos"][parte["participante_id"]]["status"] != "pago":
            assert s.pagar(parte["participante_id"], "cartao_simulado").status_code == 200
    assert s.estado()["estado"] == "pronto_para_enviar"
    assert s.enviar().status_code == 200


# ---------- falhas do iFood ----------
def test_erro_de_checkout_vira_502_legivel_e_mantem_a_sala(c, monkeypatch):
    async def quebrada(cliente, combinacao, endereco_id, pagamento_id=None):
        raise ErroCheckout("loja-x", "Não deu para montar o carrinho de Kaigan Sushi: item indisponível.")

    s = Sala(c)
    s.pronta_para_escolher()
    monkeypatch.setattr(rotas_match.checkout, "montar_carrinhos", quebrada)
    r = s.escolher("separado")
    assert r.status_code == 502 and "Kaigan Sushi" in r.json()["detail"]
    assert s.estado()["estado"] == "match_pronto"  # dá para tentar de novo


def test_falha_no_segundo_pedido_preserva_o_primeiro_e_permite_continuar(c, monkeypatch):
    s = Sala(c)
    s.pronta_para_escolher()
    s.escolher("junto")
    carrinhos = s.estado()["carrinhos"]
    if len(carrinhos) < 2:
        pytest.skip("a combinação do roteiro tem uma loja só")
    original = checkout.enviar_pedidos

    async def falha_na_segunda(cliente, cs, consentimento, ja_enviados=None):
        feitos = await original(cliente, cs[:1], consentimento, ja_enviados=ja_enviados)
        feitos.append({"loja_id": cs[1]["loja_id"], "loja_nome": cs[1]["loja_nome"], "status": "falhou",
                       "erro": "A loja fechou."})
        return feitos

    monkeypatch.setattr(rotas_match.checkout, "enviar_pedidos", falha_na_segunda)
    r = s.enviar()
    assert r.status_code == 502
    detalhe = r.json()["detail"]
    assert carrinhos[1]["loja_nome"] in detalhe and "A loja fechou." in detalhe and "1 de" in detalhe
    estado = s.estado()
    assert estado["estado"] == "pronto_para_enviar"
    assert [p["loja_id"] for p in estado["pedidos"]] == [carrinhos[0]["loja_id"]]
    assert estado["ultimo_erro_envio"]["status"] == "falhou"

    monkeypatch.setattr(rotas_match.checkout, "enviar_pedidos", original)
    assert s.enviar().status_code == 200
    final = s.estado()
    assert final["estado"] == "enviado" and final["ultimo_erro_envio"] is None
    assert len(final["pedidos"]) == len(carrinhos)
    assert len({p["order_id"] for p in final["pedidos"]}) == len(carrinhos)  # nenhum pedido em dobro


def test_total_que_mudou_para_remonta_e_pede_nova_confirmacao(c, monkeypatch):
    s = Sala(c)
    s.pronta_para_escolher()
    s.escolher("junto")
    antes = s.estado()["carrinhos"]
    alvo = antes[0]
    original = checkout.enviar_pedidos
    chamadas = {"n": 0}

    async def total_mudou(cliente, cs, consentimento, ja_enviados=None):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return [{"loja_id": alvo["loja_id"], "loja_nome": alvo["loja_nome"], "status": "total_mudou",
                     "total_antes": alvo["total"], "total_agora": alvo["total"] + 3.5}]
        return await original(cliente, cs, consentimento, ja_enviados=ja_enviados)

    monkeypatch.setattr(rotas_match.checkout, "enviar_pedidos", total_mudou)
    r = s.enviar()
    assert r.status_code == 409 and "mudou" in r.json()["detail"] and "confirme" in r.json()["detail"]
    estado = s.estado()
    assert estado["estado"] == "pronto_para_enviar" and estado["pedidos"] == []
    assert estado["carrinhos"][0]["cart_id"] != alvo["cart_id"]  # remontado
    assert soma_partes(estado) == soma_carrinhos(estado)
    assert s.enviar().status_code == 200
    assert s.estado()["estado"] == "enviado"


# ---------- reset ----------
def test_resetar_demo_limpa_as_salas(c):
    s = Sala(c)
    assert c.post("/api/demo/resetar").json() == {"ok": True}
    assert c.get(s.url()).status_code == 404


def test_atualizar_pedido_desconhecido_e_404(c):
    s = Sala(c)
    assert c.post(s.url("/pedidos/xyz/atualizar")).status_code == 404


def test_persistencia_em_sqlite_sobrevive_ao_cache_do_processo(c):
    s = Sala(c)
    s.convidar({"Milan": DESEJOS["Milan"]})
    # lê direto da tabela: a sala é só JSON no SQLite
    assert salas.obter(s.id)["participantes"][1]["desejo"]["texto"].startswith("japonês")
    salas.limpar()
    assert c.get(s.url()).status_code == 404


# ---------- correções do QA (T17b) ----------
def test_status_inicial_do_pedido_no_demo_tem_selo_de_demonstracao(c):
    s = Sala(c)
    s.pronta_para_escolher()
    assert s.escolher("junto").status_code == 200
    assert s.enviar().status_code == 200
    pedidos = s.estado()["pedidos"]
    assert pedidos and all(p["status"]["description"] == "Pedido enviado ao iFood (demonstração)." for p in pedidos)
    assert all(p["demonstracao"] is True for p in pedidos)


def test_problema_de_endereco_nao_diz_que_nenhum_pedido_serve(c, monkeypatch):
    from app.match import motor

    async def sem_coordenadas(cfg, cliente, desejos):
        return {"combinacoes": [], "avisos": [motor.MSG_ENDERECO_SEM_COORDENADAS], "problema": "endereco",
                "rastro": []}

    s = Sala(c)
    s.convidar()
    monkeypatch.setattr(rotas_match.motor, "rodar_match", sem_coordenadas)
    r = s.rodar()
    assert r.status_code == 409
    assert r.json()["detail"] == motor.MSG_ENDERECO_SEM_COORDENADAS
    assert "não encontrou um pedido" not in r.json()["detail"]
    assert s.estado()["estado"] == "coletando"


def test_sem_combinacao_por_regra_continua_com_o_prefixo(c, monkeypatch):
    async def nada(cfg, cliente, desejos):
        return {"combinacoes": [], "avisos": ["Não achei pizza até R$ 1 para Ana."], "rastro": []}

    s = Sala(c)
    s.convidar()
    monkeypatch.setattr(rotas_match.motor, "rodar_match", nada)
    r = s.rodar()
    assert r.status_code == 409 and r.json()["detail"].startswith("O Match não encontrou um pedido que sirva")


def test_envio_real_desligado_devolve_409_legivel_e_mantem_a_sala(c, monkeypatch):
    from contextlib import asynccontextmanager

    original = rotas_match.abrir_cliente

    @asynccontextmanager
    async def conta_de_teste(cfg):
        async with original(cfg) as cli:
            cli._permitir_envio = False  # como no modo real sem IFOOD_MCP_PERMITIR_ENVIO=true
            yield cli

    s = Sala(c)
    s.pronta_para_escolher()
    assert s.escolher("junto").status_code == 200
    carrinhos = [k["cart_id"] for k in s.estado()["carrinhos"]]
    monkeypatch.setattr(rotas_match, "abrir_cliente", conta_de_teste)
    r = s.enviar()
    assert r.status_code == 409
    assert r.json()["detail"] == ("Conta de teste: o envio real está desligado (IFOOD_MCP_PERMITIR_ENVIO). "
                                  "Os carrinhos ficaram prontos no iFood.")
    estado = s.estado()
    assert estado["estado"] == "pronto_para_enviar" and estado["pedidos"] == []
    assert estado["ultimo_erro_envio"]["status"] == "envio_desligado"
    assert estado["ultimo_erro_envio"]["nao_enviados"] == carrinhos
    assert any(p["tool"] == "submitOrder" and not p["ok"] for p in estado["rastro"])

    monkeypatch.setattr(rotas_match, "abrir_cliente", original)  # envio ligado: a mesma sala segue
    assert s.enviar().status_code == 200
    assert s.estado()["estado"] == "enviado"
