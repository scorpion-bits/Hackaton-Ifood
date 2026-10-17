"""Otimizador do Match (contrato C4): enumera combinações (1 item por pessoa) e pontua.

S(C) = média(nota) + α·mín(nota) − β·(custo_total / orçamento_ref) − γ·(atraso_max / 60)
       − δ·(lojas − 1) − ε·penal_perecível

O LLM só dá a nota de cada candidato e o perfil; toda a conta é deste módulo (determinística).
"""

from __future__ import annotations

import itertools
import math

from .modelos import PERFIS, Candidato, Combinacao, Pesos

MAX_CANDIDATOS_POR_PESSOA = 8
MAX_COMBINACOES = 50_000
TEMPO_ALVO_MIN = 60
DELTA_ETA_PERECIVEL_MIN = 15
VERTICAL_RESTAURANTE = "RESTAURANT"

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
    candidatos: dict[str, list[Candidato]], orcamentos: dict[str, float | None] | None = None
) -> dict[str, list[Candidato]]:
    """Restrições duras: tira quem viola regra ou passa do orçamento; mantém os 8 melhores por nota."""
    orcamentos = orcamentos or {}
    validos: dict[str, list[Candidato]] = {}
    for pid, lista in candidatos.items():
        teto = orcamentos.get(pid)
        bons = [c for c in lista if not c.viola and (teto is None or c.preco <= teto + 1e-9)]
        bons.sort(key=lambda c: (-c.nota, c.preco, c.loja_id, c.item_id))
        validos[pid] = _sem_repetidos(bons)[:MAX_CANDIDATOS_POR_PESSOA]
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


def _explicar(n_lojas: int, nota_min: float, custo: float, taxa_conhecida: bool, atraso: int | None,
              perecivel: float, sem_opcao: list[str]) -> str:
    partes = [f"{n_lojas} loja" + ("s" if n_lojas != 1 else "")]
    piso = math.floor(nota_min * 10 + 1e-9) / 10
    partes.append(f"todos com nota ≥ {_decimal(piso)}")
    partes.append(f"{_reais(custo)} " + ("com taxa" if taxa_conhecida else "sem taxa"))
    if atraso:
        partes.append(f"chega em até {atraso} min")
    if perecivel:
        partes.append("atenção: perecível chega em horário diferente")
    if sem_opcao:
        partes.append("sem opção válida para " + ", ".join(sem_opcao))
    return " · ".join(partes)


def otimizar(
    candidatos: dict[str, list[Candidato]],
    pesos: Pesos,
    max_lojas: int = 2,
    taxas: dict[str, float] | None = None,
    top: int = 3,
    orcamentos: dict[str, float | None] | None = None,
) -> list[Combinacao]:
    """Devolve as `top` melhores combinações distintas, por score decrescente.

    Pessoa sem nenhum candidato válido fica fora das combinações; isso aparece em
    `componentes["pessoas_sem_opcao"]` e na `explicacao` (não levanta erro).
    """
    orcamentos = orcamentos or {}
    validos = filtrar_validos(candidatos, orcamentos)
    sem_opcao = [pid for pid, lista in validos.items() if not lista]
    pessoas = [pid for pid, lista in validos.items() if lista]
    if not pessoas or top <= 0:
        return []

    # Referência de orçamento: orçamento da pessoa, ou o preço médio das opções dela se não informou.
    orcamento_ref = 0.0
    for pid in pessoas:
        teto = orcamentos.get(pid)
        orcamento_ref += teto if teto else sum(c.preco for c in validos[pid]) / len(validos[pid])
    if orcamento_ref <= 0:
        orcamento_ref = 1.0

    listas = _podar([validos[pid] for pid in pessoas])
    resultado: list[tuple[tuple, Combinacao]] = []
    vistas: set[tuple] = set()

    for escolhidos in itertools.product(*listas):
        lojas: list[str] = []
        for c in escolhidos:
            if c.loja_id not in lojas:
                lojas.append(c.loja_id)
        if len(lojas) > max_lojas:
            continue
        chave = tuple((c.participante_id, c.loja_id, c.item_id) for c in escolhidos)
        if chave in vistas:
            continue
        vistas.add(chave)

        notas = [c.nota for c in escolhidos]
        media = sum(notas) / len(notas)
        minimo = min(notas)
        soma_itens = sum(c.preco for c in escolhidos)
        taxa_conhecida = taxas is not None and all(l in taxas for l in lojas)
        soma_taxas = sum(taxas[l] for l in lojas) if taxa_conhecida else 0.0
        custo_total = round(soma_itens + soma_taxas, 2)
        etas = [c.eta_min for c in escolhidos if c.eta_min is not None]
        atraso_max = max(etas) if etas else 0
        penal = _penal_perecivel(list(escolhidos))

        termo_justica = pesos.alfa_justica * minimo
        termo_custo = pesos.beta_custo * (custo_total / orcamento_ref)
        termo_atraso = pesos.gama_atraso * (atraso_max / TEMPO_ALVO_MIN)
        termo_lojas = pesos.delta_lojas * (len(lojas) - 1)
        termo_perecivel = pesos.epsilon_perecivel * penal
        score = media + termo_justica - termo_custo - termo_atraso - termo_lojas - termo_perecivel

        componentes = {
            "media_nota": round(media, 4),
            "min_nota": round(minimo, 4),
            "custo_total": custo_total,
            "orcamento_ref": round(orcamento_ref, 2),
            "atraso_max_min": float(atraso_max),
            "n_lojas": float(len(lojas)),
            "penal_perecivel": penal,
            "termo_justica": round(termo_justica, 4),
            "termo_custo": round(-termo_custo, 4),
            "termo_atraso": round(-termo_atraso, 4),
            "termo_lojas": round(-termo_lojas, 4),
            "termo_perecivel": round(-termo_perecivel, 4),
            "pessoas_sem_opcao": float(len(sem_opcao)),
        }
        combinacao = Combinacao(
            escolhas={c.participante_id: c for c in escolhidos},
            lojas=lojas,
            score=round(score, 4),
            componentes=componentes,
            taxa_conhecida=taxa_conhecida,
            explicacao=_explicar(len(lojas), minimo, custo_total, taxa_conhecida, atraso_max or None,
                                 penal, sem_opcao),
        )
        # Desempate determinístico: score maior, depois mais barato, depois chave estável.
        resultado.append(((-score, custo_total, chave), combinacao))

    resultado.sort(key=lambda par: par[0])
    return [comb for _, comb in resultado[:top]]
