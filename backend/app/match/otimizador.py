"""Otimizador do Match (contratos C4 e C4b): enumera combinações e pontua.

Cada pessoa pode ter vários itens ("slots": `"{pid}"`, `"{pid}#2"`…). `pessoa_de` diz de quem é cada slot.

S(C) = média_p(sat_p) + α·mín_p(sat_p) − β·(custo_total / orçamento_ref) − γ·(atraso_max / 60)
       − δ·(lojas − 1) − ε·penal_perecível − penal_slots_fora

- sat_p = média das notas dos slots escolhidos da pessoa p (0 se ela ficou de fora).
- Orçamento da pessoa vale para a SOMA dos slots dela (restrição dura).
- Slot extra (2º item em diante) é opcional: pode ficar de fora para caber no orçamento ou no limite de lojas,
  pagando PENAL_SLOT_EXTRA_FORA; o slot principal (1º item da frase) paga PENAL_SLOT_PRINCIPAL_FORA.
- Enumeração por conjunto de lojas (≤ max_lojas): dentro de cada conjunto, produto das opções de cada pessoa.

O LLM só dá a nota de cada candidato e o perfil; toda a conta é deste módulo (determinística).
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from .modelos import PERFIS, Candidato, Combinacao, Pesos

MAX_CANDIDATOS_POR_PESSOA = 8  # por slot
MAX_COMBINACOES = 50_000  # por conjunto de lojas
MAX_AVALIACOES = 400_000  # no total
TEMPO_ALVO_MIN = 60
DELTA_ETA_PERECIVEL_MIN = 15
VERTICAL_RESTAURANTE = "RESTAURANT"
PENAL_SLOT_PRINCIPAL_FORA = 1.0
PENAL_SLOT_EXTRA_FORA = 0.35

# Pesos de cada perfil; com vários perfis no grupo, faz-se a média campo a campo.
_PESOS_PERFIL: dict[str, Pesos] = {
    "equilibrado": Pesos(),
    "barato": Pesos(alfa_justica=0.5, beta_custo=0.9, gama_atraso=0.2, delta_lojas=0.2, epsilon_perecivel=0.3),
    "rapido": Pesos(alfa_justica=0.5, beta_custo=0.2, gama_atraso=0.6, delta_lojas=0.15, epsilon_perecivel=0.3),
    "qualidade": Pesos(alfa_justica=0.8, beta_custo=0.1, gama_atraso=0.1, delta_lojas=0.1, epsilon_perecivel=0.3),
}


def pesos_por_perfil(perfis: list[str]) -> Pesos:
    """Média dos pesos dos perfis do grupo (perfil desconhecido conta como "equilibrado").

    A média já reflete a maioria: 3 "barato" e 1 "rapido" puxam o custo bem mais que o atraso.
    """
    validos = [p if p in PERFIS else "equilibrado" for p in (perfis or [])]
    if not validos:
        return Pesos()
    lista = [_PESOS_PERFIL[p] for p in validos]
    n = len(lista)
    return Pesos(
        alfa_justica=round(sum(p.alfa_justica for p in lista) / n, 4),
        beta_custo=round(sum(p.beta_custo for p in lista) / n, 4),
        gama_atraso=round(sum(p.gama_atraso for p in lista) / n, 4),
        delta_lojas=round(sum(p.delta_lojas for p in lista) / n, 4),
        epsilon_perecivel=round(sum(p.epsilon_perecivel for p in lista) / n, 4),
    )


def filtrar_validos(
    candidatos: dict[str, list[Candidato]],
    orcamentos: dict[str, float | None] | None = None,
    pessoa_de: dict[str, str] | None = None,
) -> dict[str, list[Candidato]]:
    """Restrições duras por slot: tira quem viola regra ou passa sozinho do orçamento da pessoa; 8 melhores."""
    orcamentos = orcamentos or {}
    pessoa_de = pessoa_de or {}
    validos: dict[str, list[Candidato]] = {}
    for slot, lista in candidatos.items():
        teto = orcamentos.get(pessoa_de.get(slot, slot))
        bons = [c for c in lista if not c.viola and (teto is None or c.preco <= teto + 1e-9)]
        bons.sort(key=lambda c: (-c.nota, c.preco, c.loja_id, c.item_id))
        validos[slot] = _sem_repetidos(bons)[:MAX_CANDIDATOS_POR_PESSOA]
    return validos


def _sem_repetidos(lista: list[Candidato]) -> list[Candidato]:
    vistos: set[tuple[str, str]] = set()
    saida = []
    for c in lista:
        chave = (c.loja_id, c.item_id)
        if chave not in vistos:
            vistos.add(chave)
            saida.append(c)
    return saida


def _podar(listas: list[list[Candidato]]) -> list[list[Candidato]]:
    """Corta o pior candidato de quem tem mais opções até o produto caber em MAX_COMBINACOES."""
    listas = [list(l) for l in listas]
    while math.prod(len(l) for l in listas) > MAX_COMBINACOES:
        maior = max(range(len(listas)), key=lambda i: len(listas[i]))
        if len(listas[maior]) <= 1:
            break
        listas[maior].pop()  # já ordenadas por nota desc
    return listas


def _penal_perecivel(escolhidos: list[Candidato]) -> float:
    """1 se um perecível de restaurante vem de uma loja cujo ETA difere > 15 min de outra loja do pedido."""
    eta_loja: dict[str, int] = {}
    for c in escolhidos:
        if c.eta_min is not None:
            eta_loja[c.loja_id] = max(eta_loja.get(c.loja_id, 0), c.eta_min)
    for c in escolhidos:
        if not (c.perecivel and c.vertical == VERTICAL_RESTAURANTE and c.eta_min is not None):
            continue
        for loja, eta in eta_loja.items():
            if loja != c.loja_id and abs(eta - eta_loja[c.loja_id]) > DELTA_ETA_PERECIVEL_MIN:
                return 1.0
    return 0.0


def _reais(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


__RESTO__
