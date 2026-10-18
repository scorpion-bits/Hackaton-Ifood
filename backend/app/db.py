"""SQLite (biblioteca padrão). Hoje guarda só as salas do Match (tabela criada em match/salas.py)."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config


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
    """Garante que a pasta e o arquivo do banco existam (as tabelas são criadas por quem as usa, ex.: salas)."""
    with conectar():
        pass
