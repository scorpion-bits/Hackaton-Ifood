"""Acerto do modo "separado" (contrato C4): quanto cada pessoa paga, exato ao centavo.

- Itens: cada um paga os próprios itens.
- Taxa de entrega de uma loja: dividida IGUALMENTE entre quem tem item daquela loja.
- Desconto (cupom) de uma loja: proporcional ao valor dos itens de cada um naquela loja.
- Tudo em centavos (int); a sobra do arredondamento vai pelo método do maior resto, então
  a soma das partes é exatamente itens + taxas − descontos.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .modelos import Candidato, Parte


def centavos(valor: float) -> int:
    """Converte reais em centavos sem erro de ponto flutuante (0,1 + 0,2 vira 30, não 30,0000004)."""
    return int((Decimal(str(valor)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _reais(valor_centavos: int) -> float:
    return valor_centavos / 100


def _repartir(total: int, pesos: list[int]) -> list[int]:
    """Divide `total` centavos proporcionalmente a `pesos` (maior resto; empate → ordem da lista)."""
    soma = sum(pesos)
    if total == 0 or not pesos:
        return [0] * len(pesos)
    if soma <= 0:
        pesos = [1] * len(pesos)
        soma = len(pesos)
    base = [total * p // soma for p in pesos]
    restos = [total * p % soma for p in pesos]
    sobra = total - sum(base)
    ordem = sorted(range(len(pesos)), key=lambda i: (-restos[i], i))
    for i in ordem[:sobra]:
        base[i] += 1
    return base


def _itens_por_pessoa(escolhas: dict[str, Candidato | list[Candidato]]) -> dict[str, list[Candidato]]:
    """Aceita 1 candidato por pessoa (Combinacao.escolhas) ou uma lista (pessoa com 2+ itens)."""
    saida: dict[str, list[Candidato]] = {}
    for pid, valor in escolhas.items():
        saida[pid] = list(valor) if isinstance(valor, (list, tuple)) else [valor]
    return saida


def calcular_partes(
    escolhas: dict[str, Candidato | list[Candidato]],
    nomes: dict[str, str],
    taxas: dict[str, float],
    descontos: dict[str, float],
) -> list[Parte]:
    """Partes por pessoa, na ordem de `escolhas`. Soma das partes == itens + taxas − descontos (centavos)."""
    itens = _itens_por_pessoa(escolhas)
    pessoas = list(itens)
    for valor in list(taxas.values()) + list(descontos.values()):
        if valor < 0:
            raise ValueError("Taxa e desconto não podem ser negativos.")

    # valor de itens (centavos) de cada pessoa em cada loja, na ordem em que as lojas aparecem
    por_loja: dict[str, dict[str, int]] = {}
    for pid in pessoas:
        for c in itens[pid]:
            if c.preco < 0:
                raise ValueError(f"Preço negativo no item {c.item_nome!r}.")
            por_loja.setdefault(c.loja_id, {})
            por_loja[c.loja_id][pid] = por_loja[c.loja_id].get(pid, 0) + centavos(c.preco)

    itens_c = {pid: 0 for pid in pessoas}
    taxa_c = {pid: 0 for pid in pessoas}
    desconto_c = {pid: 0 for pid in pessoas}

    for loja, valores in por_loja.items():
        quem = [pid for pid in pessoas if pid in valores]
        subtotal = sum(valores[pid] for pid in quem)
        taxa = centavos(taxas.get(loja, 0.0))
        desconto = centavos(descontos.get(loja, 0.0))
        if desconto > subtotal + taxa:
            raise ValueError(f"Desconto da loja {loja} maior que o valor do pedido.")
        for pid in quem:
            itens_c[pid] += valores[pid]
        for pid, v in zip(quem, _repartir(taxa, [1] * len(quem))):
            taxa_c[pid] += v
        for pid, v in zip(quem, _repartir(desconto, [valores[p] for p in quem])):
            desconto_c[pid] += v

    return [
        Parte(
            participante_id=pid,
            nome=nomes.get(pid, pid),
            itens=_reais(itens_c[pid]),
            taxa=_reais(taxa_c[pid]),
            desconto=_reais(desconto_c[pid]),
            total=_reais(itens_c[pid] + taxa_c[pid] - desconto_c[pid]),
        )
        for pid in pessoas
    ]


def prazo_pagamento_min(n_pessoas: int) -> int:
    """Prazo para todos pagarem: 10 min + 2 min por pessoa acima de 2."""
    return 10 + 2 * max(0, n_pessoas - 2)
