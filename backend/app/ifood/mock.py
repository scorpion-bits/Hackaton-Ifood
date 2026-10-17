"""Modo demonstração: lê e grava na base SQLite local. Todo resultado sai com fonte="demonstração"."""

import json

from .. import db
from .base import ErroIFood


class ClienteMock:
    modo = "mock"
    fonte = "demonstração"

    def listar_lojas(self) -> list[dict]:
        with db.conectar() as con:
            linhas = con.execute("SELECT * FROM lojas ORDER BY nome").fetchall()
        return [self._loja(r) for r in linhas]

    def listar_itens(self, loja_id: str) -> list[dict]:
        with db.conectar() as con:
            if not con.execute("SELECT 1 FROM lojas WHERE id = ?", (loja_id,)).fetchone():
                raise ErroIFood(f"Loja {loja_id!r} não encontrada.")
            linhas = con.execute("SELECT * FROM itens WHERE loja_id = ? ORDER BY categoria, nome", (loja_id,)).fetchall()
        return [self._item(r) for r in linhas]

    def buscar_itens(self, termo: str, preco_max: float | None = None) -> list[dict]:
        sql = (
            "SELECT itens.*, lojas.nome AS loja_nome FROM itens JOIN lojas ON lojas.id = itens.loja_id "
            "WHERE (itens.nome LIKE ? OR itens.categoria LIKE ? OR lojas.categoria LIKE ? OR lojas.nome LIKE ?)"
        )
        padrao = f"%{termo.strip()}%"
        args: list = [padrao, padrao, padrao, padrao]
        if preco_max is not None:
            sql += " AND itens.preco <= ?"
            args.append(preco_max)
        with db.conectar() as con:
            linhas = con.execute(sql + " ORDER BY itens.preco", args).fetchall()
        return [self._item(r) | {"loja_nome": r["loja_nome"]} for r in linhas]

    def alterar_disponibilidade(self, loja_id: str, item_id: str, disponivel: bool) -> dict:
        with db.conectar() as con:
            item = self._buscar_item(con, loja_id, item_id)
            con.execute("UPDATE itens SET disponivel = ? WHERE id = ?", (int(disponivel), item_id))
        return {"item_id": item_id, "nome": item["nome"], "disponivel": disponivel, "fonte": self.fonte}

    def criar_promocao(self, loja_id: str, item_id: str, desconto_pct: float) -> dict:
        with db.conectar() as con:
            item = self._buscar_item(con, loja_id, item_id)
            cur = con.execute(
                "INSERT INTO promocoes (loja_id, item_id, desconto_pct, criado_em) VALUES (?, ?, ?, ?)",
                (loja_id, item_id, desconto_pct, db.agora()),
            )
        preco_final = round(item["preco"] * (1 - desconto_pct / 100), 2)
        return {
            "promocao_id": cur.lastrowid,
            "item": item["nome"],
            "preco_original": item["preco"],
            "preco_promocional": preco_final,
            "fonte": self.fonte,
        }

    def criar_pedido(self, loja_id: str, itens: list[dict]) -> dict:
        with db.conectar() as con:
            total = 0.0
            linhas = []
            for pedido_item in itens:
                item = self._buscar_item(con, loja_id, pedido_item["item_id"])
                qtd = int(pedido_item["quantidade"])
                if not item["disponivel"] or item["estoque"] < qtd:
                    raise ErroIFood(f"{item['nome']} sem estoque suficiente (disponível: {item['estoque']}).")
                con.execute("UPDATE itens SET estoque = estoque - ? WHERE id = ?", (qtd, item["id"]))
                total += item["preco"] * qtd
                linhas.append({"item_id": item["id"], "nome": item["nome"], "quantidade": qtd, "preco": item["preco"]})
            taxa = con.execute("SELECT taxa_entrega FROM lojas WHERE id = ?", (loja_id,)).fetchone()[0]
            total = round(total + taxa, 2)
            cur = con.execute(
                "INSERT INTO pedidos (loja_id, itens_json, total, status, criado_em) VALUES (?, ?, ?, ?, ?)",
                (loja_id, json.dumps(linhas, ensure_ascii=False), total, "CRIADO", db.agora()),
            )
        return {"pedido_id": cur.lastrowid, "itens": linhas, "taxa_entrega": taxa, "total": total, "fonte": self.fonte}

    # --- auxiliares ---
    def _buscar_item(self, con, loja_id: str, item_id: str):
        item = con.execute("SELECT * FROM itens WHERE id = ? AND loja_id = ?", (item_id, loja_id)).fetchone()
        if not item:
            raise ErroIFood(f"Item {item_id!r} não encontrado na loja {loja_id!r}.")
        return item

    def _loja(self, r) -> dict:
        return {
            "id": r["id"], "nome": r["nome"], "categoria": r["categoria"], "nota": r["nota"],
            "tempo_entrega_min": r["tempo_entrega_min"], "taxa_entrega": r["taxa_entrega"],
            "aberta": bool(r["aberta"]), "fonte": self.fonte,
        }

    def _item(self, r) -> dict:
        return {
            "id": r["id"], "loja_id": r["loja_id"], "categoria": r["categoria"], "nome": r["nome"],
            "descricao": r["descricao"], "preco": r["preco"], "disponivel": bool(r["disponivel"]),
            "estoque": r["estoque"], "fonte": self.fonte,
        }
