"""Rotas do Match em grupo (contrato C7): sala, desejos, Match, pagamentos e envio dos pedidos.

Regras de ouro desta API:
- Ações do organizador exigem o header `X-Organizador: <token>` (403 sem ele).
- Nada vai ao iFood sem a confirmação explícita (`confirmo: true`) e, no modo "separado", sem 100% pago.
- Chamadas ao MCP acontecem FORA da trava de gravação da sala; o resultado é confirmado depois, revalidando o estado.
- Mensagens de erro são legíveis (o front mostra o `detail` como está).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Header
from pydantic import BaseModel

from . import config
from .ifood_mcp.cliente import MSG_ENVIO_DESLIGADO, ErroMCP, abrir_cliente
from .match import checkout, motor, salas
from .match.ajuste import interpretar_ajuste
from .match.acerto import calcular_partes, centavos, prazo_pagamento_min
from .match.modelos import Candidato, Desejo, para_dict
from .match.pix import gerar_pix_copia_e_cola
from .match.salas import AGUARDANDO, COLETANDO, ENVIADO, MATCH_PRONTO, PRONTO, ErroSala

router = APIRouter(prefix="/api")

CIDADE_PIX = "SAO CARLOS"
FORMAS = ("pix", "cartao_simulado", "dinheiro")
MODOS = ("junto", "separado")
STATUS_INICIAL_PEDIDO = {"code": "SUBMITTED", "description": "Pedido enviado ao iFood."}
STATUS_INICIAL_DEMO = {"code": "SUBMITTED", "description": "Pedido enviado ao iFood (demonstração)."}
MSG_ENVIO_DESLIGADO_SALA = ("Conta de teste: o envio real está desligado (IFOOD_MCP_PERMITIR_ENVIO). "
                            "Os carrinhos ficaram prontos no iFood.")

_travas: dict[str, asyncio.Lock] = {}


def _trava(sala_id: str) -> asyncio.Lock:
    """Uma trava por sala para as ações do organizador que falam com o MCP (uma de cada vez)."""
    return _travas.setdefault(sala_id, asyncio.Lock())


def _brl(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------- corpos ----------
class NovaSala(BaseModel):
    organizador_nome: str = ""
    chave_pix: str | None = None


class NovoParticipante(BaseModel):
    nome: str = ""


class CorpoDesejo(BaseModel):
    texto: str = ""
    orcamento_max: float | None = None
    chips: list[str] = []


class CorpoEscolha(BaseModel):
    combinacao: int | None = None
    modo_pagamento: str | None = None


class CorpoPagamento(BaseModel):
    forma: str | None = None


class CorpoResolver(BaseModel):
    acao: str | None = None


class CorpoAjuste(BaseModel):
    texto: str = ""


# ---------- utilidades ----------
def _desembrulhar(erro: BaseException) -> BaseException:
    """O SDK do MCP usa grupos de tarefas: uma falha pode chegar embrulhada num ExceptionGroup."""
    while isinstance(erro, BaseExceptionGroup) and len(erro.exceptions) == 1:
        erro = erro.exceptions[0]
    return erro


def _erro_do_ifood(bruto: BaseException) -> ErroSala:
    """Exceção do cliente MCP → `ErroSala` legível (nunca traceback nem token na mensagem).

    Login/token (sem login, sem client_id/secret, sessão expirada, renovação recusada, 401 do MCP) → 401;
    falta de conexão com o login → 502 sem prefixo; erro de tool → 502 "O iFood respondeu com erro: …"."""
    from .ifood_mcp import oauth
    from .ifood_mcp.cliente import MSG_401

    mensagens_de_login = {oauth.MSG_SEM_TOKEN, oauth.MSG_SEM_CREDENCIAIS, oauth.MSG_SESSAO_EXPIRADA, MSG_401}

    def de_login(x: BaseException) -> ErroSala | None:
        texto = oauth.sem_segredos(x)
        # O cliente embrulha o ErroOAuth num ErroMCP (`from None`): a origem fica em __cause__/__context__.
        origem = next((o for o in (x, x.__cause__, x.__context__) if isinstance(o, oauth.ErroOAuth)), None)
        if isinstance(origem, oauth.SemConexao):
            return ErroSala(502, texto)
        if origem is not None or (isinstance(x, ErroMCP) and texto in mensagens_de_login):
            return ErroSala(401, texto)
        if isinstance(x, ErroMCP) and "recusou o login (401)" in texto:  # MCP recusou o token no meio da sessão
            return ErroSala(401, oauth.MSG_SESSAO_EXPIRADA)
        return None

    e = _desembrulhar(bruto)
    if isinstance(e, ErroSala):
        return e
    if isinstance(e, checkout.ErroCheckout):
        causa = e.__cause__
        login = de_login(causa) if causa is not None else None
        return login if login and login.status == 401 else ErroSala(502, oauth.sem_segredos(e.mensagem))
    login = de_login(e)
    if login is not None:
        return login
    texto = oauth.sem_segredos(e)
    if isinstance(e, ErroMCP):
        return ErroSala(502, f"O iFood respondeu com erro: {texto}")
    return ErroSala(502, f"Falha ao falar com o iFood ({type(e).__name__}): {texto}")


async def _usar_cliente(sala_id: str, operacao):
    """Abre o cliente MCP, executa `operacao(cfg, cliente)` e sempre guarda o rastro na sala (mesmo com erro)."""
    cfg = config.carregar()
    rastro: list[dict] = []
    try:
        async with abrir_cliente(cfg) as cliente:
            try:
                return await operacao(cfg, cliente)
            finally:
                rastro = cliente.rastro_como_dicts()
    except Exception as bruto:
        raise _erro_do_ifood(bruto) from bruto
    finally:
        if rastro:
            salas.atualizar(sala_id, lambda s: salas.acumular_rastro(s, rastro))


def _texto_limpo(valor: str | None, rotulo: str, maximo: int) -> str:
    texto = " ".join((valor or "").split())
    if not texto:
        raise ErroSala(400, f"Informe {rotulo}.")
    if len(texto) > maximo:
        raise ErroSala(400, f"{rotulo[0].upper() + rotulo[1:]} passou de {maximo} caracteres.")
    return texto


def _candidato_de_dict(d: dict) -> Candidato:
    campos = Candidato.__dataclass_fields__
    return Candidato(**{k: v for k, v in d.items() if k in campos})


def _calcular_partes(sala: dict, carrinhos: list[dict]) -> tuple[list[dict], list[str]]:
    """Partes por pessoa a partir do que o getCart devolveu (itens, taxa e desconto por loja)."""
    nomes = {p["id"]: p["nome"] for p in sala["participantes"]}
    por_pessoa: dict[str, list[Candidato]] = {}
    for c in carrinhos:
        for it in c["itens"]:
            pid = it.get("participante_id")
            if pid not in nomes:
                raise ErroSala(502, f"O carrinho de {c['loja_nome']} tem um item sem dono; refaça o Match.")
            preco = round(float(it.get("preco") or 0) * int(it.get("quantidade") or 1), 2)
            por_pessoa.setdefault(pid, []).append(Candidato(
                participante_id=pid, loja_id=c["loja_id"], loja_nome=c["loja_nome"],
                item_id=str(it.get("item_id") or ""), item_nome=str(it.get("nome") or ""),
                preco=preco, eta_min=c.get("eta_min"), vertical="", perecivel=False,
            ))
    escolhas = {p["id"]: por_pessoa[p["id"]] for p in sala["participantes"] if p["id"] in por_pessoa}
    taxas = {c["loja_id"]: float(c["taxa"] or 0) for c in carrinhos}
    descontos = {c["loja_id"]: float(c["desconto"] or 0) for c in carrinhos}
    try:
        partes = calcular_partes(escolhas, nomes, taxas, descontos)
    except ValueError as e:
        raise ErroSala(502, f"Não consegui dividir o valor dos carrinhos: {e}") from e
    avisos = []
    soma_partes = sum(centavos(p.total) for p in partes)
    soma_carrinhos = sum(centavos(c["total"]) for c in carrinhos)
    if soma_partes != soma_carrinhos:
        dif = abs(soma_carrinhos - soma_partes) / 100
        avisos.append(f"A soma das partes difere do total dos carrinhos em {_brl(dif)} "
                      "(valores que a loja não detalhou por item); confira antes de enviar.")
    return para_dict(partes), avisos


def _aplicar_carrinhos(sala: dict, carrinhos: list[dict]) -> None:
    """Grava carrinhos + partes e reconcilia os pagamentos (usado ao escolher, remover itens e total que mudou).

    Modo "separado": o organizador paga a si mesmo (nasce `pago`, forma "organizador"). Quem já pagou um valor
    diferente do novo (ou tinha um Pix de valor antigo) volta a `pendente`, com o prazo renovado.
    Modo "junto": não há pagamentos individuais; vai direto para `pronto_para_enviar`.
    """
    partes, avisos = _calcular_partes(sala, carrinhos)
    sala["carrinhos"] = carrinhos
    sala["partes"] = partes
    sala["avisos"] = [*[a for a in sala["avisos"] if not a.startswith("A soma das partes")], *avisos]
    if sala["modo_pagamento"] != "separado":
        sala["pagamentos"] = {}
        sala["prazo_fim"] = None
        salas.transicionar(sala, PRONTO)
        return

    antigos = sala["pagamentos"]
    novos: dict[str, dict] = {}
    renovar = sala["prazo_fim"] is None
    for parte in partes:
        pid, total = parte["participante_id"], parte["total"]
        antigo = antigos.get(pid)
        if pid == sala["organizador_id"]:
            novos[pid] = {"forma": "organizador", "status": "pago", "valor": total}
        elif antigo and centavos(antigo.get("valor", -1)) == centavos(total):
            novos[pid] = antigo
        else:
            novos[pid] = {"forma": None, "status": "pendente", "valor": total}
            if antigo and (antigo.get("status") == "pago" or antigo.get("forma")):
                novos[pid]["ajuste"] = True
                renovar = renovar or antigo.get("status") == "pago"
    sala["pagamentos"] = novos
    if renovar:
        sala["prazo_fim"] = salas.prazo_em(prazo_pagamento_min(len(partes)))
    _reavaliar_pagamentos(sala)


def _reavaliar_pagamentos(sala: dict) -> None:
    """Todos pagos → pronto_para_enviar; senão aguardando_pagamentos."""
    pagamentos = sala["pagamentos"]
    tudo_pago = bool(pagamentos) and all(p["status"] == "pago" for p in pagamentos.values())
    salas.transicionar(sala, PRONTO if tudo_pago else AGUARDANDO)


def _pagamento_ou_404(sala: dict, pid: str) -> dict:
    if sala["modo_pagamento"] != "separado":
        raise ErroSala(409, "Neste pedido o organizador paga tudo junto; não há pagamento por pessoa.")
    pag = sala["pagamentos"].get(pid)
    if pag is None:
        raise ErroSala(404, "Essa pessoa não tem parte a pagar neste pedido.")
    return pag


def _marcar_pago(pag: dict) -> None:
    pag["status"] = "pago"
    pag.pop("ajuste", None)


def _parte_de(sala: dict, pid: str) -> dict:
    return next(p for p in sala["partes"] if p["participante_id"] == pid)


# ---------- sala ----------
@router.post("/salas")
def criar_sala(corpo: NovaSala):
    nome = _texto_limpo(corpo.organizador_nome, "o seu nome", 60)
    chave = (corpo.chave_pix or "").strip() or None
    if chave:
        try:
            gerar_pix_copia_e_cola(chave, nome, CIDADE_PIX, 1.0)  # só valida; o valor real vem depois
        except ValueError as e:
            raise ErroSala(400, f"Chave Pix ou nome inválido para gerar o Pix: {e}") from e
    cfg = config.carregar()
    sala = salas.criar(nome, chave, demonstracao=cfg.ifood_mcp_modo != "real")
    return {
        "sala_id": sala["id"],
        "token_organizador": sala["token"],
        "link_convite": f"#/s/{sala['id']}",
        "participante_id": sala["organizador_id"],
    }


@router.get("/salas/{sala_id}")
def estado_da_sala(sala_id: str):
    return salas.publica(salas.obter(sala_id))


@router.post("/salas/{sala_id}/participantes")
def entrar_na_sala(sala_id: str, corpo: NovoParticipante, x_organizador: str | None = Header(default=None)):
    nome = _texto_limpo(corpo.nome, "o seu nome", 40)

    def entrar(sala: dict) -> dict:
        salas.exigir_estado(sala, COLETANDO, acao="entrar na sala")
        org = sala["participantes"][0]
        # O organizador já é participante desde a criação. Se ele "entra" (com o token, ou com o mesmo nome
        # antes de ter reivindicado o lugar), devolve o mesmo id em vez de criar um duplicado.
        eh_token = bool(x_organizador) and x_organizador == sala["token"]
        eh_nome = not sala["organizador_reivindicado"] and nome.casefold() == org["nome"].casefold()
        if eh_token or eh_nome:
            sala["organizador_reivindicado"] = True
            return {"participante_id": org["id"]}
        if len(sala["participantes"]) >= salas.MAX_PARTICIPANTES:
            raise ErroSala(409, f"A sala já tem {salas.MAX_PARTICIPANTES} pessoas, o máximo para um Match.")
        pid = salas.novo_id(6)
        sala["participantes"].append({"id": pid, "nome": nome, "desejo": None, "respondeu": False})
        return {"participante_id": pid}

    return salas.atualizar(sala_id, entrar)


@router.put("/salas/{sala_id}/participantes/{pid}/desejo")
def registrar_desejo(sala_id: str, pid: str, corpo: CorpoDesejo):
    texto = _texto_limpo(corpo.texto, "o que você quer pedir", 300)
    orcamento = corpo.orcamento_max
    if orcamento is not None and not (0 < orcamento <= 10000):
        raise ErroSala(400, "O orçamento precisa ser maior que zero (e até R$ 10.000).")
    chips = [" ".join(c.split())[:30] for c in corpo.chips if c and c.strip()][:12]

    def gravar(sala: dict) -> dict:
        salas.exigir_estado(sala, COLETANDO, acao="mudar o desejo")
        p = salas.participante(sala, pid)
        p["desejo"] = {"texto": texto, "orcamento_max": orcamento, "chips": chips}
        p["respondeu"] = True
        return {"ok": True}

    return salas.atualizar(sala_id, gravar)


# ---------- Match ----------
MSG_AJUSTE_NAO_ENTENDIDO = 'Não entendi quem ou o quê. Ex.: "troca o sorvete do Milan por açaí"'
MAX_TEXTO_AJUSTE = 200


def _desejos_da_sala(sala: dict) -> list[Desejo]:
    return [
        Desejo(p["id"], p["nome"], p["desejo"]["texto"], p["desejo"]["orcamento_max"], list(p["desejo"]["chips"]))
        for p in sala["participantes"] if p["respondeu"] and p["desejo"]
    ]


async def _rodar_motor(sala_id: str, desejos: list[Desejo]) -> dict:
    """Roda o Match (leilão incluído) com o MCP e valida o resultado. Não grava nada na sala além do rastro:
    sem endereço ou sem combinação → `ErroSala` 409 legível; erro do iFood → o mesmo tratamento de sempre."""
    async def operacao(cfg, cliente):
        return await motor.rodar_match(cfg, cliente, desejos)

    resultado = await _usar_cliente(sala_id, operacao)
    resultado.pop("rastro", None)  # o rastro vai acumulado na sala

    if resultado.get("problema") == "endereco":  # sem endereço/sem coordenadas: mensagem própria e acionável
        raise ErroSala(409, " ".join(resultado.get("avisos") or []) or motor.MSG_SEM_ENDERECO)
    if not resultado.get("combinacoes"):
        avisos = " ".join(resultado.get("avisos") or []) or "Nenhuma combinação coube nas regras."
        raise ErroSala(409, f"O Match não encontrou um pedido que sirva para todos. {avisos}")
    return resultado


def _resultado_com_rastro(sala_id: str) -> dict:
    pub = salas.publica(salas.obter(sala_id))
    return {**pub["resultado"], "rastro": pub["rastro"]}


@router.post("/salas/{sala_id}/rodar")
async def rodar(sala_id: str, x_organizador: str | None = Header(default=None)):
    async with _trava(sala_id):
        sala = salas.obter(sala_id)
        salas.exigir_organizador(sala, x_organizador)
        salas.exigir_estado(sala, COLETANDO, MATCH_PRONTO, acao="rodar o Match")
        desejos = _desejos_da_sala(sala)
        if not desejos:
            raise ErroSala(409, "Ninguém respondeu ainda. Peça para o grupo escrever o que quer pedir.")

        resultado = await _rodar_motor(sala_id, desejos)

        def gravar(s: dict) -> None:
            salas.exigir_estado(s, COLETANDO, MATCH_PRONTO, acao="rodar o Match")
            s["resultado"] = resultado
            salas.transicionar(s, MATCH_PRONTO)

        salas.atualizar(sala_id, gravar)
        return _resultado_com_rastro(sala_id)


@router.post("/salas/{sala_id}/ajustar")
async def ajustar(sala_id: str, corpo: CorpoAjuste, x_organizador: str | None = Header(default=None)):
    """"Ajustar com o IBits" (C14): frase do organizador → mudanças nos desejos → Match de novo.

    Transação: os desejos novos só são gravados junto com o resultado novo. Se o Match não achar combinação (ou o
    iFood falhar), a sala continua com os desejos e o resultado anteriores."""
    async with _trava(sala_id):
        sala = salas.obter(sala_id)
        salas.exigir_organizador(sala, x_organizador)
        salas.exigir_estado(sala, MATCH_PRONTO, acao="ajustar o pedido")
        texto = _texto_limpo(corpo.texto, "o que você quer ajustar", MAX_TEXTO_AJUSTE)
        participantes = [
            {"id": p["id"], "nome": p["nome"], "organizador": p["id"] == sala["organizador_id"],
             "respondeu": bool(p["respondeu"] and p["desejo"]),
             "texto": (p["desejo"] or {}).get("texto") if p["respondeu"] else None,
             "orcamento_max": (p["desejo"] or {}).get("orcamento_max"),
             "chips": list((p["desejo"] or {}).get("chips") or [])}
            for p in sala["participantes"]
        ]
        mudancas = await interpretar_ajuste(config.carregar(), texto, participantes)
        if not mudancas:
            raise ErroSala(422, MSG_AJUSTE_NAO_ENTENDIDO)

        por_id = {m.participante_id: m for m in mudancas}
        nomes = {p["id"]: p["nome"] for p in sala["participantes"]}
        desejos = []
        for d in _desejos_da_sala(sala):
            m = por_id.get(d.participante_id)
            if m is not None:
                d = Desejo(d.participante_id, d.nome, m.novo_texto,
                           m.novo_orcamento if m.novo_orcamento is not None else d.orcamento_max, d.chips)
            desejos.append(d)
        entendido = [{"participante_id": m.participante_id, "nome": nomes[m.participante_id], "resumo": m.resumo}
                     for m in mudancas]

        resultado = await _rodar_motor(sala_id, desejos)  # 409/502 aqui: nada dos desejos novos foi gravado

        def gravar(s: dict) -> None:
            salas.exigir_estado(s, MATCH_PRONTO, acao="ajustar o pedido")
            for p in s["participantes"]:
                m = por_id.get(p["id"])
                if m is not None and p["desejo"]:
                    p["desejo"]["texto"] = m.novo_texto
                    if m.novo_orcamento is not None:
                        p["desejo"]["orcamento_max"] = m.novo_orcamento
            s["resultado"] = resultado
            salas.registrar_ajuste(s, texto, entendido)

        salas.atualizar(sala_id, gravar)
        return {"entendido": entendido, "resultado": _resultado_com_rastro(sala_id)}


@router.post("/salas/{sala_id}/escolher")
async def escolher(sala_id: str, corpo: CorpoEscolha, x_organizador: str | None = Header(default=None)):
    async with _trava(sala_id):
        sala = salas.obter(sala_id)
        salas.exigir_organizador(sala, x_organizador)
        salas.exigir_estado(sala, MATCH_PRONTO, acao="escolher a combinação")
        if corpo.modo_pagamento not in MODOS:
            raise ErroSala(400, "Escolha como pagar: 'junto' ou 'separado'.")
        combinacoes = sala["resultado"]["combinacoes"]
        idx = corpo.combinacao
        if idx is None or isinstance(idx, bool) or not (0 <= idx < len(combinacoes)):
            raise ErroSala(400, f"Combinação inexistente: escolha de 0 a {len(combinacoes) - 1}.")
        combinacao = combinacoes[idx]
        endereco_id = (sala["resultado"].get("endereco") or {}).get("id")
        if not endereco_id:
            raise ErroSala(409, motor.MSG_ENDERECO_SEM_ID if sala["resultado"].get("endereco") else
                           "O Match não achou um endereço de entrega; rode o Match de novo.")

        async def operacao(cfg, cliente):
            return await checkout.montar_carrinhos(cliente, combinacao, endereco_id)

        carrinhos = await _usar_cliente(sala_id, operacao)

        def gravar(s: dict) -> None:
            salas.exigir_estado(s, MATCH_PRONTO, acao="escolher a combinação")
            s["combinacao"] = idx
            s["combinacao_escolhida"] = combinacao
            s["modo_pagamento"] = corpo.modo_pagamento
            s["pagamentos"] = {}
            s["prazo_fim"] = None
            s["pedidos"] = []
            s["ja_enviados"] = []
            _aplicar_carrinhos(s, carrinhos)

        salas.atualizar(sala_id, gravar)
        pub = salas.publica(salas.obter(sala_id))
        return {k: pub[k] for k in ("estado", "carrinhos", "modo_pagamento", "partes", "pagamentos", "prazo_fim", "avisos")}


# ---------- pagamentos ----------
@router.post("/salas/{sala_id}/pagamentos/{pid}")
def pagar(sala_id: str, pid: str, corpo: CorpoPagamento):
    if corpo.forma not in FORMAS:
        raise ErroSala(400, "Forma de pagamento inválida: use 'pix', 'cartao_simulado' ou 'dinheiro'.")
    forma = corpo.forma

    def registrar(sala: dict) -> dict:
        salas.exigir_estado(sala, AGUARDANDO, acao="registrar o pagamento")
        pag = _pagamento_ou_404(sala, pid)
        if pag["status"] == "pago":
            raise ErroSala(409, "Essa parte já está paga.")
        parte = _parte_de(sala, pid)
        pag.pop("ajuste", None)
        pag.pop("pix_copia_e_cola", None)
        pag["forma"] = forma
        pag["valor"] = parte["total"]
        resposta: dict[str, Any]
        if forma == "pix":
            if not sala["chave_pix"]:
                raise ErroSala(409, "O organizador não cadastrou chave Pix. Escolha dinheiro ou cartão (simulado).")
            try:
                codigo = gerar_pix_copia_e_cola(sala["chave_pix"], sala["participantes"][0]["nome"],
                                                CIDADE_PIX, parte["total"])
            except ValueError as e:
                raise ErroSala(409, f"Não consegui gerar o Pix desta parte: {e}") from e
            pag["status"] = "aguardando_confirmacao"
            pag["pix_copia_e_cola"] = codigo
            resposta = {"status": pag["status"], "pix_copia_e_cola": codigo}
        elif forma == "cartao_simulado":
            if not sala["demonstracao"]:
                raise ErroSala(409, "O cartão simulado só existe no modo de demonstração.")
            _marcar_pago(pag)
            resposta = {"status": "pago", "demonstracao": True}
        else:  # dinheiro: o organizador confirma com "recebi"
            pag["status"] = "aguardando_confirmacao"
            resposta = {"status": pag["status"]}
        _reavaliar_pagamentos(sala)
        return resposta

    return salas.atualizar(sala_id, registrar)


@router.post("/salas/{sala_id}/pagamentos/{pid}/recebi")
def recebi(sala_id: str, pid: str, x_organizador: str | None = Header(default=None)):
    def confirmar(sala: dict) -> dict:
        salas.exigir_organizador(sala, x_organizador)
        salas.exigir_estado(sala, AGUARDANDO, PRONTO, acao="confirmar o recebimento")
        pag = _pagamento_ou_404(sala, pid)
        if pag["status"] == "pago":
            return {"status": "pago"}
        if pag["status"] != "aguardando_confirmacao":
            raise ErroSala(409, "Essa pessoa ainda não escolheu Pix ou dinheiro; não há o que confirmar.")
        _marcar_pago(pag)
        if sala["estado"] == AGUARDANDO:
            _reavaliar_pagamentos(sala)
        return {"status": "pago"}

    return salas.atualizar(sala_id, confirmar)


@router.post("/salas/{sala_id}/pagamentos/{pid}/resolver")
async def resolver(sala_id: str, pid: str, corpo: CorpoResolver, x_organizador: str | None = Header(default=None)):
    if corpo.acao not in ("organizador_cobre", "remover_itens"):
        raise ErroSala(400, "Ação inválida: use 'organizador_cobre' ou 'remover_itens'.")
    async with _trava(sala_id):
        sala = salas.obter(sala_id)
        salas.exigir_organizador(sala, x_organizador)
        salas.exigir_estado(sala, AGUARDANDO, acao="resolver um pagamento pendente")
        pag = _pagamento_ou_404(sala, pid)
        if pag["status"] == "pago":
            raise ErroSala(409, "Essa parte já está paga; não há o que resolver.")

        if corpo.acao == "organizador_cobre":
            def cobrir(s: dict) -> dict:
                salas.exigir_estado(s, AGUARDANDO, acao="resolver um pagamento pendente")
                p = _pagamento_ou_404(s, pid)
                p.update(forma="organizador", status="pago", valor=_parte_de(s, pid)["total"])
                p.pop("pix_copia_e_cola", None)
                p.pop("ajuste", None)
                _reavaliar_pagamentos(s)
                return {"status": "pago", "estado": s["estado"]}

            return salas.atualizar(sala_id, cobrir)

        # remover_itens: remonta os carrinhos sem os itens dessa pessoa e recalcula as partes
        if pid == sala["organizador_id"]:
            raise ErroSala(409, "Os itens do organizador não podem ser removidos.")
        escolhas = {slot: c for slot, c in sala["combinacao_escolhida"]["escolhas"].items()
                    if slot.split("#", 1)[0] != pid}
        if not escolhas:
            raise ErroSala(409, "Tirar esses itens esvaziaria o pedido; cancele o Match em vez disso.")
        filtrada = {**sala["combinacao_escolhida"], "escolhas": escolhas,
                    "lojas": list(dict.fromkeys(c["loja_id"] for c in escolhas.values()))}
        endereco_id = sala["resultado"]["endereco"]["id"]
        nome = salas.participante(sala, pid)["nome"]

        async def operacao(cfg, cliente):
            return await checkout.montar_carrinhos(cliente, filtrada, endereco_id)

        carrinhos = await _usar_cliente(sala_id, operacao)

        def remover(s: dict) -> dict:
            salas.exigir_estado(s, AGUARDANDO, acao="resolver um pagamento pendente")
            if s["pagamentos"].get(pid, {}).get("status") == "pago":
                raise ErroSala(409, "Essa parte acabou de ser paga; nada foi removido.")
            s["pagamentos"].pop(pid, None)
            s["combinacao_escolhida"] = filtrada
            s["avisos"] = [*s["avisos"], f"Os itens de {nome} saíram do pedido."]
            _aplicar_carrinhos(s, carrinhos)
            return {"estado": s["estado"], "partes": s["partes"], "carrinhos": s["carrinhos"]}

        return salas.atualizar(sala_id, remover)


# ---------- envio ----------
def _pedido_de(envio: dict, carrinho: dict, demonstracao: bool = False) -> dict:
    demonstracao = demonstracao or bool(envio.get("demonstracao"))
    status = STATUS_INICIAL_DEMO if demonstracao else STATUS_INICIAL_PEDIDO
    return {
        "order_id": envio["order_id"], "cart_id": envio["cart_id"], "loja_id": envio["loja_id"],
        "loja_nome": envio.get("loja_nome") or carrinho["loja_nome"], "total": envio["total"],
        "itens": carrinho["itens"], "status": dict(status),
        "status_code": status["code"], "encerrado": False,
        "demonstracao": demonstracao,
    }


@router.post("/salas/{sala_id}/enviar")
async def enviar(sala_id: str, corpo: dict | None = Body(default=None), x_organizador: str | None = Header(default=None)):
    async with _trava(sala_id):
        sala = salas.obter(sala_id)
        salas.exigir_organizador(sala, x_organizador)
        if not isinstance(corpo, dict) or corpo.get("confirmo") is not True:
            raise ErroSala(400, "Falta a confirmação do organizador (confirmo: true). Nada foi enviado.")
        salas.exigir_estado(sala, PRONTO, acao="enviar os pedidos")
        carrinhos = sala["carrinhos"]
        enviados = set(sala["ja_enviados"])

        async def operacao(cfg, cliente):
            return await checkout.enviar_pedidos(cliente, carrinhos, consentimento=True, ja_enviados=enviados)

        try:
            resultados = await _usar_cliente(sala_id, operacao)
        except ErroSala as e:
            # Falha inesperada no meio do envio: o que já saiu não pode ser reenviado (evita pedido em dobro).
            if enviados - set(sala["ja_enviados"]):
                def lembrar(s: dict) -> None:
                    s["ja_enviados"] = sorted(enviados | set(s["ja_enviados"]))
                    s["ultimo_erro_envio"] = {"status": "falhou", "erro": e.mensagem}

                salas.atualizar(sala_id, lembrar)
            raise

        por_cart = {c["cart_id"]: c for c in carrinhos}
        problema = next((r for r in resultados if r["status"] in ("falhou", "total_mudou")), None)
        # conta de teste com `submitOrder` desligado: não é falha para "tentar de novo"; os carrinhos ficam prontos
        desligado = bool(problema and problema["status"] == "falhou" and problema.get("erro") == MSG_ENVIO_DESLIGADO)

        def gravar(s: dict) -> None:
            for r in resultados:
                if r["status"] == "enviado":
                    s["pedidos"] = [*s["pedidos"], _pedido_de(r, por_cart[r["cart_id"]], bool(s.get("demonstracao")))]
                    s["ja_enviados"] = [*s["ja_enviados"], r["cart_id"]]
            if desligado:  # a sala continua pronta para enviar (se o envio for ligado); nada foi enviado
                s["ultimo_erro_envio"] = {
                    "status": "envio_desligado", "erro": MSG_ENVIO_DESLIGADO_SALA,
                    "nao_enviados": [c["cart_id"] for c in s["carrinhos"] if c["cart_id"] not in s["ja_enviados"]],
                }
            elif problema:
                s["ultimo_erro_envio"] = {k: v for k, v in problema.items()}
            else:
                s["ultimo_erro_envio"] = None
                if all(c["cart_id"] in s["ja_enviados"] for c in s["carrinhos"]):
                    salas.transicionar(s, ENVIADO)

        salas.atualizar(sala_id, gravar)
        feitos = len(salas.obter(sala_id)["ja_enviados"])
        total = len(carrinhos)

        if problema is None:
            return {"estado": ENVIADO, "pedidos": salas.obter(sala_id)["pedidos"]}

        if desligado:
            raise ErroSala(409, MSG_ENVIO_DESLIGADO_SALA)
        loja = problema.get("loja_nome") or problema.get("loja_id")
        ficou = f"{feitos} de {total} pedidos já foram enviados e foram mantidos."
        if problema["status"] == "falhou":
            raise ErroSala(502, f"Não consegui enviar o pedido de {loja}: {problema.get('erro')} {ficou} "
                                "Tente enviar de novo para continuar de onde parou.")
        # total_mudou: remonta o carrinho dessa loja e pede nova confirmação
        mudou = (f"O total do pedido de {loja} mudou de {_brl(problema['total_antes'])} para "
                 f"{_brl(problema['total_agora'])}.")
        await _remontar_loja(sala_id, problema["loja_id"])
        raise ErroSala(409, f"{mudou} Nada foi cobrado a mais: os valores foram recalculados. {ficou} "
                            "Revise e confirme o envio de novo.")


async def _remontar_loja(sala_id: str, loja_id: str) -> None:
    """Depois de um total que mudou: remonta o carrinho dessa loja e recalcula as partes (nova confirmação)."""
    sala = salas.obter(sala_id)
    escolhas = {slot: c for slot, c in sala["combinacao_escolhida"]["escolhas"].items() if c["loja_id"] == loja_id}
    filtrada = {**sala["combinacao_escolhida"], "escolhas": escolhas, "lojas": [loja_id]}
    endereco_id = sala["resultado"]["endereco"]["id"]

    async def operacao(cfg, cliente):
        return await checkout.montar_carrinhos(cliente, filtrada, endereco_id)

    try:
        novos = await _usar_cliente(sala_id, operacao)
    except ErroSala:
        return  # não deu para remontar; a mensagem ao organizador já explica que o total mudou

    def trocar(s: dict) -> None:
        s["carrinhos"] = [novos[0] if c["loja_id"] == loja_id else c for c in s["carrinhos"]]
        _aplicar_carrinhos(s, s["carrinhos"])

    salas.atualizar(sala_id, trocar)


@router.post("/salas/{sala_id}/pedidos/{order_id}/atualizar")
async def atualizar_pedido(sala_id: str, order_id: str):
    sala = salas.obter(sala_id)
    if not any(p["order_id"] == order_id for p in sala["pedidos"]):
        raise ErroSala(404, "Pedido não encontrado nesta sala.")

    async def operacao(cfg, cliente):
        return await checkout.acompanhar(cliente, order_id)

    rastreio = await _usar_cliente(sala_id, operacao)

    def gravar(s: dict) -> dict:
        for p in s["pedidos"]:
            if p["order_id"] == order_id:
                p["status"] = {"code": rastreio["status_code"], "description": rastreio["status_descricao"]}
                p["status_code"] = rastreio["status_code"]
                p["encerrado"] = bool(rastreio["encerrado"])
                p["historico"] = rastreio["historico"]
                p["proxima_consulta"] = rastreio["proxima_consulta"]
                return dict(p)
        raise ErroSala(404, "Pedido não encontrado nesta sala.")

    return salas.atualizar(sala_id, gravar)
