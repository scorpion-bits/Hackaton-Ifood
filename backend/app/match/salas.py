"""Salas do Match (contrato C7): estado persistido em SQLite (tabela própria `salas_match`).

Cada sala é um JSON com o estado inteiro. Leitura e escrita passam por `atualizar(id, fn)`, que é atômica
(trava de thread + transação), então convidados entrando, pagando e o organizador agindo ao mesmo tempo
não se sobrescrevem. As chamadas lentas (MCP) ficam FORA da trava: o chamador busca, faz a rede e depois
confirma a mudança em `atualizar`, que revalida o estado.

Máquina de estados:
    coletando → match_pronto → aguardando_pagamentos (separado) ─┐
                             └→ pronto_para_enviar (junto) ──────┴→ enviado
"""

from __future__ import annotations

import json
import secrets
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from .. import db

COLETANDO = "coletando"
MATCH_PRONTO = "match_pronto"
AGUARDANDO = "aguardando_pagamentos"
PRONTO = "pronto_para_enviar"
ENVIADO = "enviado"

# Transições permitidas (inclui repetir o Match e voltar a esperar pagamento depois de um ajuste de valores).
TRANSICOES = {
    COLETANDO: {COLETANDO, MATCH_PRONTO},
    MATCH_PRONTO: {MATCH_PRONTO, AGUARDANDO, PRONTO},
    AGUARDANDO: {AGUARDANDO, PRONTO},
    PRONTO: {PRONTO, AGUARDANDO, ENVIADO},
    ENVIADO: set(),
}
ROTULO_ESTADO = {
    COLETANDO: "recebendo os desejos",
    MATCH_PRONTO: "com o Match pronto",
    AGUARDANDO: "aguardando os pagamentos",
    PRONTO: "pronta para enviar os pedidos",
    ENVIADO: "com os pedidos já enviados",
}
MAX_PARTICIPANTES = 6  # limite do otimizador (C4)
MAX_AJUSTES = 10  # histórico do "Ajustar com o Match" guardado na sala

_trava = threading.RLock()


class ErroSala(HTTPException):
    """Erro de regra da sala. `status` vira o código HTTP; `mensagem` (legível) vai em `detail`."""

    def __init__(self, status: int, mensagem: str):
        super().__init__(status_code=status, detail=mensagem)
        self.status = status
        self.mensagem = mensagem


# ---------- tempo ----------
def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso_z(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prazo_em(minutos: int) -> str:
    return iso_z(agora_utc() + timedelta(minutes=minutos))


def novo_id(tamanho: int = 8) -> str:
    return uuid.uuid4().hex[:tamanho]


# ---------- persistência ----------
def _garantir(con) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS salas_match (id TEXT PRIMARY KEY, estado_json TEXT NOT NULL, atualizado_em TEXT)"
    )


def criar(organizador_nome: str, chave_pix: str | None, demonstracao: bool) -> dict:
    """Cria a sala; o organizador entra como `participantes[0]`."""
    sala_id = novo_id()
    organizador_id = novo_id(6)
    sala = {
        "id": sala_id,
        "token": secrets.token_urlsafe(24),
        "organizador_id": organizador_id,
        "organizador_reivindicado": True,  # o id do organizador já volta no POST /api/salas; ninguém o "reivindica" pelo nome
        "chave_pix": chave_pix or None,
        "demonstracao": demonstracao,
        "estado": COLETANDO,
        "criada_em": iso_z(agora_utc()),
        "participantes": [
            {"id": organizador_id, "nome": organizador_nome, "desejo": None, "respondeu": False}
        ],
        "resultado": None,
        "combinacao": None,  # índice escolhido
        "combinacao_escolhida": None,  # a combinação em si (para remontar carrinhos)
        "carrinhos": None,
        "modo_pagamento": None,
        "partes": None,
        "pagamentos": {},
        "prazo_fim": None,
        "pedidos": [],
        "ja_enviados": [],
        "rastro": [],
        "avisos": [],
        "ultimo_erro_envio": None,
        "ajustes": [],  # "Ajustar com o Match" (C14): [{texto, entendido, em}], os últimos MAX_AJUSTES
    }
    with _trava, db.conectar() as con:
        _garantir(con)
        con.execute("INSERT INTO salas_match VALUES (?, ?, ?)",
                    (sala_id, json.dumps(sala, ensure_ascii=False), db.agora()))
    return sala


def obter(sala_id: str) -> dict:
    """Sala pelo id; 404 se não existir."""
    with db.conectar() as con:
        _garantir(con)
        linha = con.execute("SELECT estado_json FROM salas_match WHERE id = ?", (sala_id,)).fetchone()
    if linha is None:
        raise ErroSala(404, "Sala não encontrada. Confira o link ou crie uma nova sala.")
    return json.loads(linha["estado_json"])


def atualizar(sala_id: str, fn: Callable[[dict], Any]) -> Any:
    """Lê, aplica `fn(sala)` (que muda o dict no lugar) e grava — tudo atômico. Se `fn` levantar, nada é gravado."""
    with _trava, db.conectar() as con:
        _garantir(con)
        linha = con.execute("SELECT estado_json FROM salas_match WHERE id = ?", (sala_id,)).fetchone()
        if linha is None:
            raise ErroSala(404, "Sala não encontrada. Confira o link ou crie uma nova sala.")
        sala = json.loads(linha["estado_json"])
        retorno = fn(sala)
        con.execute("UPDATE salas_match SET estado_json = ?, atualizado_em = ? WHERE id = ?",
                    (json.dumps(sala, ensure_ascii=False), db.agora(), sala_id))
    return retorno


def limpar() -> None:
    """Apaga todas as salas (botão "Recarregar demo")."""
    with _trava, db.conectar() as con:
        _garantir(con)
        con.execute("DELETE FROM salas_match")


# ---------- regras ----------
def exigir_organizador(sala: dict, token: str | None) -> None:
    if not token or not secrets.compare_digest(token, sala["token"]):
        raise ErroSala(403, "Só o organizador da sala pode fazer isso neste aparelho.")


def exigir_estado(sala: dict, *validos: str, acao: str) -> None:
    if sala["estado"] not in validos:
        raise ErroSala(409, f"Não dá para {acao} agora: a sala está {ROTULO_ESTADO[sala['estado']]}.")


def transicionar(sala: dict, novo: str) -> None:
    atual = sala["estado"]
    if novo not in TRANSICOES[atual]:
        raise ErroSala(409, f"A sala está {ROTULO_ESTADO[atual]} e não pode passar para outra fase assim.")
    sala["estado"] = novo


def participante(sala: dict, pid: str) -> dict:
    for p in sala["participantes"]:
        if p["id"] == pid:
            return p
    raise ErroSala(404, "Participante não encontrado nesta sala.")


def acumular_rastro(sala: dict, rastro: list[dict]) -> None:
    sala["rastro"] = [*sala["rastro"], *rastro]


def registrar_ajuste(sala: dict, texto: str, entendido: list[dict]) -> dict:
    """Guarda um ajuste do organizador (C14); mantém só os últimos `MAX_AJUSTES`."""
    ajuste = {"texto": texto, "entendido": entendido, "em": iso_z(agora_utc())}
    sala["ajustes"] = [*(sala.get("ajustes") or []), ajuste][-MAX_AJUSTES:]
    return ajuste


# ---------- visão pública (sem segredos) ----------
def mascarar_chave(chave: str | None) -> str | None:
    """"12345678901" → "12•••••••01": nunca devolve a chave inteira."""
    if not chave:
        return None
    if len(chave) <= 6:
        return "•" * len(chave)
    return chave[:2] + "•" * min(len(chave) - 4, 8) + chave[-2:]


def publica(sala: dict) -> dict:
    """O que o GET devolve. Sem token, sem a chave Pix inteira, sem o texto dos desejos dos outros e sem o
    endereço completo. (O código Pix "copia e cola" do pagador contém a chave por definição do BR Code.)"""
    resultado = sala["resultado"]
    if resultado is not None:
        resultado = {k: v for k, v in resultado.items() if k != "rastro"}
        endereco = resultado.get("endereco")
        if endereco:
            resultado["endereco"] = {"apelido": endereco.get("apelido")}
    pagamentos = {}
    for pid, pag in sala["pagamentos"].items():
        item = {"forma": pag.get("forma"), "status": pag.get("status")}
        if pag.get("pix_copia_e_cola"):
            item["pix"] = pag["pix_copia_e_cola"]
            item["pix_copia_e_cola"] = pag["pix_copia_e_cola"]
        pagamentos[pid] = item
    return {
        "id": sala["id"],
        "estado": sala["estado"],
        "demonstracao": sala["demonstracao"],
        "conta_teste": not sala["demonstracao"],  # modo real só roda com as contas de teste do Portal
        "link_convite": f"#/s/{sala['id']}",
        "organizador_id": sala["organizador_id"],
        "tem_chave_pix": bool(sala["chave_pix"]),
        "chave_pix_mascarada": mascarar_chave(sala["chave_pix"]),
        "participantes": [{"id": p["id"], "nome": p["nome"], "respondeu": p["respondeu"]}
                          for p in sala["participantes"]],
        "resultado": resultado,
        "combinacao_escolhida": sala["combinacao"],
        "carrinhos": sala["carrinhos"],
        "modo_pagamento": sala["modo_pagamento"],
        "partes": sala["partes"],
        "pagamentos": pagamentos,
        "prazo_fim": sala["prazo_fim"],
        "pedidos": sala["pedidos"],
        "avisos": sala["avisos"],
        "ultimo_erro_envio": sala["ultimo_erro_envio"],
        "rastro": sala["rastro"],
        "ajustes": sala.get("ajustes") or [],
    }
