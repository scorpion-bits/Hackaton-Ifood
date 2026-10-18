"""OAuth do iFood (PKCE S256 + client secret), rotas de login, cliente MCP real e sanitização do diagnóstico.

Nada aqui fala com a internet: o /token é um `httpx.MockTransport` e o "MCP real" é o servidor de demonstração
servido por Streamable HTTP via ASGI, atrás de um porteiro que exige `Authorization: Bearer`.
"""

import base64
import hashlib
import json
from urllib.parse import parse_qs, unquote, urlparse

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient
from mcp.server.transport_security import TransportSecuritySettings

from app import rotas_oauth
from app.config import carregar
from app.ifood_mcp import ErroMCP, abrir_cliente, cliente, criar_servidor_demo, oauth, resetar_demo
from app.ifood_mcp.diagnostico import MASCARA, executar, sanitizar
from app.main import app

ACCESS = "ACCESS-SECRETO-123456"
REFRESH = "REFRESH-SECRETO-abcdef"
CODE = "CODE-SECRETO-xyz"
SECRET = "segredo-do-portal"


@pytest.fixture(autouse=True)
def oauth_isolado(tmp_path, monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    monkeypatch.setenv("IFOOD_MCP_CLIENT_ID", "id-do-agente")
    monkeypatch.setenv("IFOOD_MCP_CLIENT_SECRET", SECRET)
    monkeypatch.setenv("IFOOD_MCP_REDIRECT", "http://localhost:8000/oauth/callback")
    monkeypatch.setenv("IFOOD_MCP_SCOPE", "")
    monkeypatch.setattr(oauth, "ARQUIVO_TOKENS", tmp_path / ".tokens_ifood.json")
    monkeypatch.setattr(oauth, "_metodo_auth", "basic")
    monkeypatch.setattr(oauth, "_transporte", None)
    monkeypatch.setattr(oauth, "_enviar_resource", True)
    monkeypatch.setattr(cliente, "_transporte_real", None)
    oauth._estados.clear()
    yield
    oauth._estados.clear()


class FalsoIFood:
    """Imita o /token e o /revoke do id.ifood.com.br e guarda o que recebeu."""

    def __init__(self, respostas=None):
        self.respostas = list(respostas or [])
        self.pedidos: list[httpx.Request] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if pedido.url.path == "/revoke":
            return httpx.Response(200)
        if self.respostas:
            status, corpo = self.respostas.pop(0)
            return httpx.Response(status, json=corpo)
        return httpx.Response(200, json={"access_token": ACCESS, "refresh_token": REFRESH, "expires_in": 3600,
                                         "token_type": "Bearer"})

    def form(self, i: int = -1) -> dict[str, str]:
        return {k: v[0] for k, v in parse_qs(self.pedidos[i].content.decode()).items()}


@pytest.fixture
def falso(monkeypatch):
    f = FalsoIFood()
    monkeypatch.setattr(oauth, "_transporte", httpx.MockTransport(f))
    return f


def _salvar(access=ACCESS, refresh=REFRESH, segundos=3600, conta=None):
    import time

    oauth.salvar_tokens(oauth.Tokens(access_token=access, refresh_token=refresh,
                                     expires_at=time.time() + segundos, conta=conta))


def _params(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


# ---------- URL de login e PKCE ----------
def test_url_de_login_tem_pkce_s256_e_state():
    url = oauth.url_login(carregar())
    assert url.startswith("https://id.ifood.com.br/authorize?")
    p = _params(url)
    assert p["response_type"] == "code" and p["client_id"] == "id-do-agente"
    assert p["redirect_uri"] == "http://localhost:8000/oauth/callback"
    assert p["code_challenge_method"] == "S256"
    assert p["resource"] == "https://consumer-mcp.ifood.com.br/marketplace"
    assert "scope" not in p  # IFOOD_MCP_SCOPE vazio = não envia
    verifier = oauth._estados[p["state"]][0]
    esperado = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert p["code_challenge"] == esperado and "=" not in p["code_challenge"]
    assert 43 <= len(verifier) <= 128
    assert SECRET not in url


def test_scope_vai_separado_por_espaco(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_SCOPE", "openid,discovery:read  cart:write")
    assert _params(oauth.url_login(carregar()))["scope"] == "openid discovery:read cart:write"


def test_rota_login_redireciona_para_o_ifood():
    r = TestClient(app).get("/oauth/login", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("https://id.ifood.com.br/authorize?")


def test_sem_credenciais_mensagem_legivel(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_CLIENT_ID", "")
    with pytest.raises(oauth.SemCredenciais, match="IFOOD_MCP_CLIENT_ID"):
        oauth.url_login(carregar())
    r = TestClient(app).get("/oauth/login", follow_redirects=False)
    assert r.status_code == 302
    destino = unquote(r.headers["location"])
    assert destino.startswith("/#/conectado?erro=") and "IFOOD_MCP_CLIENT_ID" in destino
    status = TestClient(app).get("/api/ifood/status").json()
    assert status["configurado"] is False and "IFOOD_MCP_CLIENT_ID" in status["mensagem"]


def test_state_expira_em_10_minutos(monkeypatch):
    p = _params(oauth.url_login(carregar()))
    verifier, criado, redirect = oauth._estados[p["state"]]
    oauth._estados[p["state"]] = (verifier, criado - 601, redirect)
    with pytest.raises(oauth.EstadoInvalido):
        oauth._consumir_estado(p["state"])


# ---------- callback ----------
def test_callback_com_state_invalido_da_400(falso):
    r = TestClient(app).get(f"/oauth/callback?code={CODE}&state=inventado", follow_redirects=False)
    assert r.status_code == 400 and "Conectar iFood" in r.text
    assert CODE not in r.text and not falso.pedidos and oauth.carregar_tokens() is None


def test_callback_com_erro_do_provedor_volta_com_mensagem():
    r = TestClient(app).get("/oauth/callback?error=access_denied&state=x", follow_redirects=False)
    assert r.status_code == 302
    destino = unquote(r.headers["location"])
    assert destino.startswith("/#/conectado?erro=") and "cancelou" in destino


def test_callback_troca_o_codigo_salva_e_nao_vaza_token(falso, monkeypatch):
    async def sem_conta(_cfg):
        return None

    monkeypatch.setattr(rotas_oauth, "_descobrir_conta", sem_conta)
    api = TestClient(app)
    state = _params(api.get("/oauth/login", follow_redirects=False).headers["location"])["state"]
    verifier = oauth._estados[state][0]

    r = api.get(f"/oauth/callback?code={CODE}&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/#/conectado"
    for segredo in (ACCESS, REFRESH, CODE, SECRET):
        assert segredo not in r.text and segredo not in json.dumps(dict(r.headers))

    form = falso.form()
    assert form == {"grant_type": "authorization_code", "code": CODE, "code_verifier": verifier,
                    "redirect_uri": "http://localhost:8000/oauth/callback",
                    "resource": "https://consumer-mcp.ifood.com.br/marketplace"}
    esperado = "Basic " + base64.b64encode(f"id-do-agente:{SECRET}".encode()).decode()
    assert falso.pedidos[-1].headers["authorization"] == esperado
    tokens = oauth.carregar_tokens()
    assert tokens.access_token == ACCESS and tokens.refresh_token == REFRESH
    assert ACCESS not in repr(tokens) and REFRESH not in repr(tokens)

    # o mesmo state não vale duas vezes
    assert api.get(f"/oauth/callback?code={CODE}&state={state}", follow_redirects=False).status_code == 400

    status = api.get("/api/ifood/status")
    assert status.json()["conectado"] is True and status.json()["modo"] == "demo"
    assert ACCESS not in status.text and REFRESH not in status.text


async def test_invalid_client_no_basic_tenta_client_secret_post_uma_vez(falso):
    falso.respostas = [(401, {"error": "invalid_client"})]
    state = _params(oauth.url_login(carregar()))["state"]
    await oauth.trocar_codigo(carregar(), CODE, state)
    assert len(falso.pedidos) == 2
    assert "authorization" in falso.pedidos[0].headers
    assert "authorization" not in falso.pedidos[1].headers
    assert falso.form(1)["client_id"] == "id-do-agente" and falso.form(1)["client_secret"] == SECRET
    assert oauth._metodo_auth == "post"


async def test_client_recusado_nos_dois_metodos_vira_mensagem_sem_segredo(falso):
    falso.respostas = [(401, {"error": "invalid_client"}), (401, {"error": "invalid_client"})]
    state = _params(oauth.url_login(carregar()))["state"]
    with pytest.raises(oauth.ErroOAuth) as erro:
        await oauth.trocar_codigo(carregar(), CODE, state)
    assert "IFOOD_MCP_CLIENT_ID" in str(erro.value)
    assert SECRET not in str(erro.value) and CODE not in str(erro.value)
    assert len(falso.pedidos) == 2 and oauth.carregar_tokens() is None


def test_callback_com_troca_recusada_volta_com_erro(falso):
    falso.respostas = [(400, {"error": "invalid_grant"})]
    api = TestClient(app)
    state = _params(api.get("/oauth/login", follow_redirects=False).headers["location"])["state"]
    r = api.get(f"/oauth/callback?code={CODE}&state={state}", follow_redirects=False)
    assert r.status_code == 302 and unquote(r.headers["location"]).startswith("/#/conectado?erro=")
    assert CODE not in unquote(r.headers["location"])


# ---------- renovação ----------
async def test_token_valido_nao_renova_longe_de_expirar(falso):
    _salvar(segundos=3600)
    assert await oauth.token_valido(carregar()) == ACCESS
    assert falso.pedidos == []


async def test_token_valido_renova_5_min_antes(falso):
    falso.respostas = [(200, {"access_token": "NOVO", "expires_in": 3600})]  # sem refresh novo: mantém o antigo
    _salvar(access="VELHO", segundos=240)
    assert await oauth.token_valido(carregar()) == "NOVO"
    form = falso.form()
    assert form["grant_type"] == "refresh_token" and form["refresh_token"] == REFRESH
    assert form["resource"] == "https://consumer-mcp.ifood.com.br/marketplace"
    salvo = oauth.carregar_tokens()
    assert salvo.access_token == "NOVO" and salvo.refresh_token == REFRESH and salvo.segundos_restantes() > 3000
    assert await oauth.token_valido(carregar()) == "NOVO" and len(falso.pedidos) == 1


async def test_refresh_morto_apaga_login_e_pede_para_conectar(falso):
    falso.respostas = [(400, {"error": "invalid_grant"})]
    _salvar(segundos=10)
    with pytest.raises(oauth.SemToken, match="Conecte"):
        await oauth.token_valido(carregar())
    assert oauth.carregar_tokens() is None


async def test_sem_login_salvo():
    with pytest.raises(oauth.SemToken, match="Conecte o iFood primeiro"):
        await oauth.token_valido(carregar())


# ---------- status e sair ----------
def test_status_nao_vaza_token_e_mostra_so_o_primeiro_nome():
    _salvar(conta="Maria")
    r = TestClient(app).get("/api/ifood/status")
    corpo = r.json()
    assert corpo["conectado"] is True and corpo["conta"] == "Maria" and corpo["renovavel"] is True
    assert "expira_em" in corpo and corpo["configurado"] is True
    assert ACCESS not in r.text and REFRESH not in r.text and SECRET not in r.text


def test_sair_apaga_o_login_e_revoga(falso):
    _salvar()
    r = TestClient(app).post("/api/ifood/sair")
    assert r.status_code == 200 and r.json()["conectado"] is False
    assert oauth.carregar_tokens() is None
    assert falso.pedidos and falso.pedidos[-1].url.path == "/revoke"
    assert ACCESS not in r.text and REFRESH not in r.text


def test_primeiro_nome_do_getuser():
    assert oauth.primeiro_nome({"fullName": "Maria da Silva", "email": "m@x.com"}) == "Maria"
    assert oauth.primeiro_nome({"user": {"name": "  João  Souza"}}) == "João"
    assert oauth.primeiro_nome({"email": "m@x.com"}) is None


# ---------- cliente MCP real ----------
async def test_abrir_cliente_real_sem_token_da_erro_legivel(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    with pytest.raises(ErroMCP, match=r"Conecte o iFood primeiro \(botão Conectar iFood\)"):
        async with abrir_cliente(carregar()):
            pass


class Porteiro:
    """ASGI: só deixa passar quem manda o Bearer aceito; o resto leva 401 como o iFood real."""

    def __init__(self, app_mcp, aceito: str | None):
        self.app_mcp = app_mcp
        self.aceito = aceito
        self.vistos: list[str] = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            auth = dict(scope["headers"]).get(b"authorization", b"").decode()
            self.vistos.append(auth)
            if self.aceito is None or auth != f"Bearer {self.aceito}":
                corpo = b'{"error": "invalid_token"}'
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"www-authenticate", b'Bearer error="invalid_token"')]})
                await send({"type": "http.response.body", "body": corpo})
                return
        await self.app_mcp(scope, receive, send)


@pytest.fixture
def mcp_real_falso(monkeypatch):
    """Servidor de demonstração exposto como se fosse o MCP real (Streamable HTTP em /marketplace)."""
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    resetar_demo()
    servidor = criar_servidor_demo()
    app_mcp = servidor.streamable_http_app(
        streamable_http_path="/marketplace", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

    def montar(aceito: str | None) -> Porteiro:
        porteiro = Porteiro(app_mcp, aceito)
        monkeypatch.setattr(cliente, "_transporte_real", httpx2.ASGITransport(app=porteiro))
        return porteiro

    return servidor, montar


async def test_cliente_real_manda_bearer_e_usa_a_mesma_interface(mcp_real_falso, falso):
    servidor, montar = mcp_real_falso
    porteiro = montar(ACCESS)
    _salvar()
    async with servidor.session_manager.run():
        async with abrir_cliente(carregar()) as cli:
            assert cli.modo == "real" and cli.demonstracao is False
            usuario = await cli.chamar("getUser")
            nomes = {t["name"] for t in await cli.listar_tools()}
    assert usuario["fullName"] and {"searchOffers", "getCart", "submitOrder"} <= nomes
    assert [c.tool for c in cli.rastro] == ["getUser"] and cli.rastro[0].ok
    assert porteiro.vistos and all(v == f"Bearer {ACCESS}" for v in porteiro.vistos)
    assert falso.pedidos == []  # token ainda válido: sem refresh


async def test_cliente_real_401_renova_uma_vez_e_reabre(mcp_real_falso, falso):
    servidor, montar = mcp_real_falso
    falso.respostas = [(200, {"access_token": "NOVO", "refresh_token": "REFRESH2", "expires_in": 3600})]
    porteiro = montar("NOVO")
    _salvar(access="REVOGADO", segundos=3600)  # parece válido, mas o servidor recusa
    async with servidor.session_manager.run():
        async with abrir_cliente(carregar()) as cli:
            await cli.chamar("listAddresses")
    assert len([p for p in falso.pedidos if p.url.path == "/token"]) == 1
    assert "Bearer REVOGADO" in porteiro.vistos and porteiro.vistos[-1] == "Bearer NOVO"
    assert oauth.carregar_tokens().refresh_token == "REFRESH2"


async def test_cliente_real_401_de_novo_apos_renovar_vira_erro_legivel(mcp_real_falso, falso):
    servidor, montar = mcp_real_falso
    montar(None)  # recusa tudo
    _salvar(segundos=3600)
    async with servidor.session_manager.run():
        with pytest.raises(ErroMCP, match="Conecte o iFood de novo"):
            async with abrir_cliente(carregar()):
                pass
    assert len([p for p in falso.pedidos if p.url.path == "/token"]) == 1  # renovou só 1 vez


async def test_modo_demo_continua_em_processo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    async with abrir_cliente(carregar()) as cli:
        assert cli.demonstracao is True
        assert (await cli.chamar("listAddresses"))["demonstracao"] is True


# ---------- diagnóstico ----------
PAYLOAD_PESSOAL = {
    "user": {"name": "Maria da Silva", "fullName": "Maria da Silva", "email": "maria@exemplo.com",
             "phone": "+55 16 99123-4567", "taxPayerIdentificationNumber": "123.456.789-09",
             "cpf": "12345678909", "accessToken": "eyJhbGciOi.eyJzdWIiOi.assinatura"},
    "addresses": [{
        "addressId": "end-1", "alias": "Casa da Maria", "streetName": "Rua das Flores", "number": "123",
        "complement": "apto 4", "formattedAddress": "Rua das Flores, 123, Centro", "zipCode": "13560-000",
        "location": "Rua das Flores, 123 - Centro, São Carlos", "neighborhood": "Centro", "city": "São Carlos",
        "coordinates": {"latitude": -22.017834, "longitude": -47.890912},
    }],
    "paymentMethods": [{"id": "pm-1", "name": "Visa **** 4242", "type": "CREDIT_CARD", "lastDigits": "4242"},
                       {"id": "pm-2", "name": "Pix", "type": "PIX"}],
    "merchant": {"name": "Pizzaria Boa", "price": 39.9, "lat": -22.0123456, "lng": -47.8987654},
    "observacao": "contato: maria@exemplo.com ou 123.456.789-09, Bearer abcdefghijklmnop",
    "refresh_token": "REFRESH-SECRETO",
}


def test_sanitizacao_remove_dados_pessoais_e_arredonda_coordenadas():
    limpo = sanitizar(PAYLOAD_PESSOAL)
    texto = json.dumps(limpo, ensure_ascii=False)
    for proibido in ("Maria", "maria@exemplo.com", "99123", "123.456.789-09", "12345678909", "eyJhbGciOi",
                     "Rua das Flores", "123", "apto", "13560", "4242", "REFRESH-SECRETO", "abcdefghijklmnop"):
        assert proibido not in texto, proibido
    end = limpo["addresses"][0]
    assert end["coordinates"] == {"latitude": -22.02, "longitude": -47.89}
    assert end["neighborhood"] == "Centro" and end["city"] == "São Carlos" and end["addressId"] == "end-1"
    assert end["alias"] == MASCARA and end["location"] == MASCARA
    assert limpo["merchant"] == {"name": "Pizzaria Boa", "price": 39.9, "lat": -22.01, "lng": -47.9}
    assert [m["type"] for m in limpo["paymentMethods"]] == ["CREDIT_CARD", "PIX"]
    assert limpo["paymentMethods"][1]["name"] == "Pix"
    assert set(limpo) == set(PAYLOAD_PESSOAL)  # a forma continua igual para a 03.5


def test_getuser_inteiro_e_tratado_como_pessoal():
    # getUser: TODA string é mascarada (inclusive id e dicas), a forma do JSON continua.
    limpo = sanitizar({"name": "Maria", "id": "u-1", "agentHints": {"next": "listAddresses"}}, "pessoal")
    assert limpo == {"name": MASCARA, "id": MASCARA, "agentHints": {"next": MASCARA}}


async def test_diagnostico_no_demo_grava_amostras_sanitizadas_e_nunca_envia_pedido(tmp_path):
    resetar_demo()
    async with abrir_cliente(carregar()) as cli:
        resumo = await executar(cli, tmp_path, carrinho=True)
    chamadas = [c.tool for c in cli.rastro]
    assert "submitOrder" not in chamadas and "setCartPayment" not in chamadas
    assert chamadas.count("createCart") == 2
    assert resumo["carrinho"]["dois_carrinhos_abertos"] is True
    assert "createAddress" in resumo["faltando_vs_doc"] and resumo["total_tools"] >= 17
    assert "getCart" in resumo["campos_de_preco_ou_taxa"]
    for nome in ("tools.json", "getUser.json", "listAddresses.json", "searchOffers.json", "getMerchant.json",
                 "getItem.json", "getRecommendations.json", "getCart.json", "resumo.json"):
        assert (tmp_path / nome).exists(), nome
    usuario = json.loads((tmp_path / "getUser.json").read_text(encoding="utf-8"))
    assert usuario["chamadas"][0]["resposta"]["fullName"] == MASCARA
    enderecos = (tmp_path / "listAddresses.json").read_text(encoding="utf-8")
    assert "-22.01" in enderecos and "-22.0178" not in enderecos


def test_log_de_acesso_nao_mostra_o_code():
    import logging

    registro = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                                 ("127.0.0.1:5000", "GET", f"/oauth/callback?code={CODE}&state=abc", "1.1", 302),
                                 None)
    for filtro in logging.getLogger("uvicorn.access").filters:
        filtro.filter(registro)
    assert CODE not in registro.getMessage() and "/oauth/callback?code=***" in registro.getMessage()


async def test_invalid_target_repete_sem_resource_e_desliga_no_login(falso):
    falso.respostas = [(400, {"error": "invalid_target"})]
    state = _params(oauth.url_login(carregar()))["state"]
    await oauth.trocar_codigo(carregar(), CODE, state)
    assert "resource" in falso.form(0) and "resource" not in falso.form(1)
    assert "resource" not in _params(oauth.url_login(carregar()))


def test_authorize_com_invalid_target_desliga_resource():
    r = TestClient(app).get("/oauth/callback?error=invalid_target", follow_redirects=False)
    assert "resource" in unquote(r.headers["location"])
    assert "resource" not in _params(oauth.url_login(carregar()))


# ---------- 03.1b: erros de login → 401 legível, sem traceback, gravação atômica ----------
def _sala_com_desejo(c: TestClient) -> tuple[str, dict]:
    r = c.post("/api/salas", json={"organizador_nome": "Thales"})
    sala, org = r.json()["sala_id"], {"X-Organizador": r.json()["token_organizador"]}
    pid = r.json()["participante_id"]
    assert c.put(f"/api/salas/{sala}/participantes/{pid}/desejo", json={"texto": "pizza"}).status_code == 200
    return sala, org


def test_api_sem_login_no_modo_real_responde_401_legivel(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    with TestClient(app) as c:
        sala, org = _sala_com_desejo(c)
        r = c.post(f"/api/salas/{sala}/rodar", headers=org)
    assert r.status_code == 401 and r.json()["detail"] == oauth.MSG_SEM_TOKEN
    assert "Traceback" not in r.text


def test_api_refresh_morto_responde_401_sessao_expirada(monkeypatch, falso):
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    falso.respostas = [(400, {"error": "invalid_grant"})]
    _salvar(segundos=10)
    with TestClient(app) as c:
        sala, org = _sala_com_desejo(c)
        r = c.post(f"/api/salas/{sala}/rodar", headers=org)
    assert r.status_code == 401 and r.json()["detail"] == oauth.MSG_SESSAO_EXPIRADA
    assert ACCESS not in r.text and REFRESH not in r.text and SECRET not in r.text


async def test_renovacao_recusada_por_outro_motivo_vira_sem_token_sem_segredo(falso):
    falso.respostas = [(401, {"error": "invalid_client"}), (401, {"error": "invalid_client"})]
    _salvar(segundos=10)
    with pytest.raises(oauth.SemToken) as info:
        await oauth.token_valido(carregar())
    assert "expirou" in str(info.value) and SECRET not in str(info.value) and REFRESH not in str(info.value)


async def test_sem_internet_no_login_vira_sem_conexao(monkeypatch):
    def cai(_pedido):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(oauth, "_transporte", httpx.MockTransport(cai))
    _salvar(segundos=10)
    with pytest.raises(oauth.SemConexao, match="Confira a internet"):
        await oauth.token_valido(carregar())


def test_salvar_tokens_e_atomico_e_falha_na_escrita_preserva_o_login(monkeypatch):
    _salvar(access="ANTIGO-123456")
    trocas = []
    original = oauth.os.replace
    monkeypatch.setattr(oauth.os, "replace", lambda o, d: (trocas.append((str(o), str(d))), original(o, d)))
    _salvar(access="NOVO-123456")
    assert trocas == [(str(oauth.ARQUIVO_TOKENS) + ".tmp", str(oauth.ARQUIVO_TOKENS))]
    assert oauth.carregar_tokens().access_token == "NOVO-123456"

    def disco_cheio(_fd):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(oauth.os, "fsync", disco_cheio)
    with pytest.raises(oauth.ErroOAuth, match="Não consegui gravar o login") as info:
        _salvar(access="QUEBRADO-123456")
    assert "QUEBRADO" not in str(info.value)
    assert oauth.carregar_tokens().access_token == "NOVO-123456"  # o login anterior continua inteiro
    assert not list(oauth.ARQUIVO_TOKENS.parent.glob("*.tmp"))


def test_callback_com_erro_inesperado_volta_legivel_sem_traceback(monkeypatch):
    async def explode(*_a, **_k):
        raise RuntimeError(f"falhou com access_token={ACCESS}")

    monkeypatch.setattr(oauth, "trocar_codigo", explode)
    r = TestClient(app).get("/oauth/callback?code=abc&state=xyz", follow_redirects=False)
    assert r.status_code == 302
    destino = unquote(r.headers["location"])
    assert "RuntimeError" in destino and "Conectar iFood de novo" in destino
    assert ACCESS not in destino and "Traceback" not in destino


def test_sair_com_arquivo_preso_responde_409_legivel(monkeypatch):
    _salvar()

    def preso(self, *a, **k):
        raise PermissionError("em uso")

    monkeypatch.setattr(type(oauth.ARQUIVO_TOKENS), "unlink", preso)
    r = TestClient(app).post("/api/ifood/sair")
    assert r.status_code == 409 and "Feche o arquivo" in r.json()["detail"]
    assert ACCESS not in r.text and REFRESH not in r.text


def test_sem_segredos_tira_bearer_jwt_e_token_igual():
    texto = oauth.sem_segredos(f"Bearer {ACCESS} | eyJhbGciOi.eyJzdWIiOi.assinatura | refresh_token={REFRESH} "
                               f"| client_secret: {SECRET} | invalid_grant (código de erro)")
    assert ACCESS not in texto and REFRESH not in texto and SECRET not in texto and "eyJ" not in texto
    assert "invalid_grant" in texto
