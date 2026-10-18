"""Regras do pedido (`regras_pedido.json`): o que o Match faz em cima do que cada pessoa escreve.

- Compras: mercado, farmácia e pet shop só com o botão "Compras" (chip `modo:compras`); sem ele, tudo é restaurante.
- Mesma loja: os itens de uma pessoa saem do mesmo restaurante sempre que der (peso no otimizador).
"""

import dataclasses
import json
from functools import cache
from pathlib import Path

from .modelos import Desejo, Intencao

ARQUIVO = Path(__file__).with_name("regras_pedido.json")
RESTAURANTE = "RESTAURANT"


@cache
def regras() -> dict:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def peso_mesma_loja() -> float:
    return float(regras()["mesma_loja"]["peso_por_loja_a_mais_da_pessoa"])


def lojas_mais_baratas_na_busca() -> int:
    return int(regras()["mesma_loja"]["lojas_mais_baratas_na_busca_da_loja"])


def compras_ligado(chips: list[str] | None) -> bool:
    """Botão "Compras" ligado (ou o chip antigo "Onde pedir?" num tipo de loja de compras)."""
    cfg = regras()["compras"]
    for c in chips or []:
        valor = str(c).strip()
        if valor.lower() == cfg["chip"]:
            return True
        if valor.lower().startswith("onde:") and valor[5:].strip().upper() in cfg["tipos_de_loja"]:
            return True
    return False


def aplicar_regras(desejo: Desejo, intencoes: list[Intencao]) -> tuple[list[Intencao], list[str]]:
    """Sem "Compras": cada item vai só para restaurante; item que só existe em loja de compras sai, com aviso."""
    if compras_ligado(desejo.chips):
        return intencoes, []
    cfg = regras()["compras"]
    ficam: list[Intencao] = []
    avisos: list[str] = []
    for i in intencoes:
        if RESTAURANTE in i.verticais or not i.verticais:
            ficam.append(dataclasses.replace(i, verticais=[RESTAURANTE]))
            continue
        tipo = cfg["nomes"].get(i.verticais[0], "loja de compras")
        item = (i.consultas[0] if i.consultas else "Esse item").capitalize()
        avisos.append(cfg["aviso_sem_botao"].format(item=item, pessoa=desejo.nome, tipo=tipo))
    return ficam, avisos
