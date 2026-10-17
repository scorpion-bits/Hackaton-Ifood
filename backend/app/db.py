"""SQLite (biblioteca padrão). Guarda a loja de demonstração, as ações pendentes e as conversas."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import config

DADOS_DEMO = Path(__file__).with_name("dados_demo.json")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lojas (
    id TEXT PRIMARY KEY, nome TEXT, categoria TEXT, nota REAL,
    tempo_entrega_min INTEGER, taxa_entrega REAL, aberta INTEGER
);
CREATE TABLE IF NOT EXISTS itens (
    id TEXT PRIMARY KEY, loja_id TEXT, categoria TEXT, nome TEXT, descricao TEXT,
    preco REAL, disponivel INTEGER, estoque INTEGER
);
CREATE TABLE IF NOT EXISTS promocoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, loja_id TEXT, item_id TEXT,
    desconto_pct REAL, criado_em TEXT
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, loja_id TEXT, itens_json TEXT,
    total REAL, status TEXT, criado_em TEXT
);
CREATE TABLE IF NOT EXISTS acoes (
    id TEXT PRIMARY KEY, lado TEXT, tipo TEXT, resumo TEXT, motivo TEXT,
    payload_json TEXT, status TEXT, resultado_json TEXT, criado_em TEXT, decidido_em TEXT
);
CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT, conversa_id TEXT, papel TEXT, texto TEXT, criado_em TEXT
);
"""


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def conectar():
    caminho = config.carregar().db_path
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar() -> None:
    """Cria as tabelas e, se a base estiver vazia, carrega os dados de demonstração."""
    with conectar() as con:
        con.executescript(ESQUEMA)
        vazia = con.execute("SELECT COUNT(*) FROM lojas").fetchone()[0] == 0
    if vazia:
        resetar_demo()


def resetar_demo() -> None:
    """Apaga tudo e recarrega o estado inicial da demonstração (botão 'recarregar demo')."""
    dados = json.loads(DADOS_DEMO.read_text(encoding="utf-8"))
    with conectar() as con:
        con.executescript(
            "DROP TABLE IF EXISTS lojas; DROP TABLE IF EXISTS itens; DROP TABLE IF EXISTS promocoes;"
            "DROP TABLE IF EXISTS pedidos; DROP TABLE IF EXISTS acoes; DROP TABLE IF EXISTS mensagens;"
        )
        con.executescript(ESQUEMA)
        for loja in dados["lojas"]:
            con.execute(
                "INSERT INTO lojas VALUES (:id, :nome, :categoria, :nota, :tempo_entrega_min, :taxa_entrega, :aberta)",
                loja,
            )
        for item in dados["itens"]:
            con.execute(
                "INSERT INTO itens VALUES (:id, :loja_id, :categoria, :nome, :descricao, :preco, :disponivel, :estoque)",
                item,
            )
