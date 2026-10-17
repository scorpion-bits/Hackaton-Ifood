"""Ações sensíveis (dinheiro, pedido, preço, mensagem a cliente) com confirmação humana.

O agente só PROPÕE. Quem executa é a pessoa, pelo botão "Confirmar" (POST /api/acoes/{id}/confirmar).
Nenhuma ferramenta MCP consegue confirmar uma ação.
"""

import json
import uuid

from . import db
from .ifood import ErroIFood, obter_cliente

# tipo -> (lado, função que executa no cliente iFood)
EXECUTORES = {
    "alterar_disponibilidade": ("vendedor", lambda c, p: c.alterar_disponibilidade(p["loja_id"], p["item_id"], p["disponivel"])),
    "criar_promocao": ("vendedor", lambda c, p: c.criar_promocao(p["loja_id"], p["item_id"], p["desconto_pct"])),
    "criar_pedido": ("comprador", lambda c, p: c.criar_pedido(p["loja_id"], p["itens"])),
}


def propor(tipo: str, resumo: str, motivo: str, payload: dict) -> dict:
    lado, _ = EXECUTORES[tipo]
    acao_id = uuid.uuid4().hex[:8]
    with db.conectar() as con:
        con.execute(
            "INSERT INTO acoes (id, lado, tipo, resumo, motivo, payload_json, status, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)",
            (acao_id, lado, tipo, resumo, motivo, json.dumps(payload, ensure_ascii=False), db.agora()),
        )
    return obter(acao_id) | {
        "instrucao": "Ação NÃO executada. Mostre o resumo e peça para a pessoa confirmar no botão da tela."
    }


def obter(acao_id: str) -> dict:
    with db.conectar() as con:
        r = con.execute("SELECT * FROM acoes WHERE id = ?", (acao_id,)).fetchone()
    if not r:
        raise ErroIFood(f"Ação {acao_id!r} não encontrada.")
    return _dict(r)


def listar(status: str | None = None) -> list[dict]:
    with db.conectar() as con:
        if status:
            linhas = con.execute("SELECT * FROM acoes WHERE status = ? ORDER BY criado_em DESC", (status,)).fetchall()
        else:
            linhas = con.execute("SELECT * FROM acoes ORDER BY criado_em DESC").fetchall()
    return [_dict(r) for r in linhas]


def confirmar(acao_id: str) -> dict:
    acao = obter(acao_id)
    if acao["status"] != "pendente":
        raise ErroIFood(f"Ação já está '{acao['status']}'.")
    _, executar = EXECUTORES[acao["tipo"]]
    try:
        resultado, status = executar(obter_cliente(), acao["payload"]), "executada"
    except ErroIFood as e:
        resultado, status = {"erro": str(e)}, "erro"
    _decidir(acao_id, status, resultado)
    return obter(acao_id)


def recusar(acao_id: str) -> dict:
    acao = obter(acao_id)
    if acao["status"] != "pendente":
        raise ErroIFood(f"Ação já está '{acao['status']}'.")
    _decidir(acao_id, "recusada", None)
    return obter(acao_id)


def _decidir(acao_id: str, status: str, resultado: dict | None) -> None:
    with db.conectar() as con:
        con.execute(
            "UPDATE acoes SET status = ?, resultado_json = ?, decidido_em = ? WHERE id = ?",
            (status, json.dumps(resultado, ensure_ascii=False) if resultado else None, db.agora(), acao_id),
        )


def _dict(r) -> dict:
    return {
        "id": r["id"], "lado": r["lado"], "tipo": r["tipo"], "resumo": r["resumo"], "motivo": r["motivo"],
        "payload": json.loads(r["payload_json"]), "status": r["status"],
        "resultado": json.loads(r["resultado_json"]) if r["resultado_json"] else None,
        "criado_em": r["criado_em"], "decidido_em": r["decidido_em"],
    }
