"""Otimizador do Match (contratos C4 e C4b): enumera combinações e pontua.

Cada pessoa pode ter vários itens ("slots": `"{pid}"`, `"{pid}#2"`…). `pessoa_de` diz de quem é cada slot.

S(C) = média_p(sat_p) + α·mín_p(sat_p) − β·(custo_total / orçamento_ref) − γ·(atraso_max / 60)
       − δ·(lojas − 1) − ε·penal_perecível − penal_slots_fora

- sat_p = média das notas dos slots escolhidos da pessoa p (0 se ela ficou de fora).
- Orçamento da pessoa vale para a SOMA dos slots dela (restrição dura).
- Slot extra (2º item em diante) é opcional: pode ficar de fora para caber no orçamento ou no limite de lojas,
  pagando PENAL_SLOT_EXTRA_FORA; o slot principal (1º item da frase) paga PENAL_SLOT_PRINCIPAL_FORA.
- Ordem das combinações: primeiro a menor penalidade de slots de fora (atender o pedido vale mais que economizar
  uma loja, taxa ou prazo), depois o score. Com folga no limite de lojas, nenhum item com opção válida fica de fora.
- Enumeração por conjunto de lojas (≤ max_lojas): dentro de cada conjunto, produto das opções de cada pessoa.

O LLM só dá a nota de cada candidato e o perfil; toda a conta é deste módulo (determinística).
"""

from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass

from .modelos import PERFIS, Candidato, Combinacao, Pesos

MAX_CANDIDATOS_POR_PESSOA = 8  # por slot
MAX_COMBINACOES = 50_000  # por conjunto de lojas
MAX_AVALIACOES = 120_000  # no total (repartido entre os conjuntos de lojas)
TEMPO_ALVO_MIN = 60
DELTA_ETA_PERECIVEL_MIN = 15
VERTICAL_RESTAURANTE = "RESTAURANT"
PENAL_SLOT_PRINCIPAL_FORA = 1.0
PENAL_SLOT_EXTRA_FORA = 0.35
BEM_ATENDIDO = 0.5  # média de notas a partir da qual a pessoa conta como bem atendida (o mesmo FELIZ do leilão)

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
    vistos: set[tuple] = set()
    saida = []
    for c in lista:
        chave = (c.loja_id, c.item_id, tuple(c.cobre))  # o combo (cobre 2+ slots) não é o mesmo que o item avulso
        if chave not in vistos:
            vistos.add(chave)
            saida.append(c)
    return saida


def _podar(listas: list[list], limite: int = MAX_COMBINACOES) -> list[list]:
    """Corta a pior opção de quem tem mais opções até o produto caber em `limite` (listas já ordenadas)."""
    listas = [list(l) for l in listas]
    while math.prod(len(l) for l in listas) > limite:
        maior = max(range(len(listas)), key=lambda i: len(listas[i]))
        if len(listas[maior]) <= 1:
            break
        listas[maior].pop()  # já ordenadas da melhor para a pior
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


def _quem_ficou_bem(nota_min: float, alguem_fora: bool) -> str:
    """Linguagem simples, sem número de nota: "todos bem atendidos", "quem entrou está bem atendido" (alguém ou
    algum item ficou de fora) ou "alguém ficou longe do que pediu"."""
    if nota_min < BEM_ATENDIDO - 1e-9:
        return "alguém ficou longe do que pediu"
    return "quem entrou está bem atendido" if alguem_fora else "todos bem atendidos"


def _explicar(n_lojas: int, nota_min: float, custo: float, taxa_conhecida: bool, atraso: int | None,
              perecivel: float, sem_opcao: list[str], slots_fora: int = 0) -> str:
    partes = [f"{n_lojas} loja" + ("s" if n_lojas != 1 else "")]
    partes.append(_quem_ficou_bem(nota_min, bool(sem_opcao or slots_fora)))
    partes.append(f"{_reais(custo)} " + ("com taxa" if taxa_conhecida else "sem taxa"))
    if atraso:
        partes.append(f"chega em até {atraso} min")
    if perecivel:
        partes.append("atenção: perecível chega em horário diferente")
    if slots_fora:
        partes.append(f"{slots_fora} " + ("item ficou de fora" if slots_fora == 1 else "itens ficaram de fora"))
    if sem_opcao:
        partes.append("sem opção válida para " + ", ".join(sem_opcao))
    return " · ".join(partes)


@dataclass(frozen=True)
class _OpcaoPessoa:
    """Uma escolha de itens para uma pessoa (1 candidato por slot escolhido; slots extras podem ficar de fora)."""

    escolhidos: tuple[Candidato, ...]
    n_fora: int
    penal: float
    preco: float
    sat: float
    lojas: frozenset[str]
    mascara: int = 0  # bit de cada loja (para testar o conjunto de lojas rápido)
    eta_max: int = 0
    perecivel: bool = False


def _slots_por_pessoa(slots: list[str], pessoa_de: dict[str, str]) -> dict[str, list[str]]:
    """Agrupa os slots por pessoa, na ordem em que aparecem (o 1º slot é o principal)."""
    grupos: dict[str, list[str]] = {}
    for slot in slots:
        grupos.setdefault(pessoa_de.get(slot, slot), []).append(slot)
    return grupos


def _opcoes_da_pessoa(slots: list[str], validos: dict[str, list[Candidato]], teto: float | None,
                      bits: dict[str, int]) -> list[_OpcaoPessoa]:
    com_opcao = [s for s in slots if validos.get(s)]
    if not com_opcao:
        return []
    principal = slots[0]
    varios = len(com_opcao) > 1
    listas = [([None] + validos[s]) if varios else validos[s] for s in com_opcao]
    # slots com as mesmas opções = o mesmo pedido repetido ("2 cocas"): aí o mesmo item vale para os dois
    opcoes_do_slot = {s: frozenset((c.loja_id, c.item_id, tuple(c.cobre)) for c in validos[s]) for s in com_opcao}
    opcoes: list[_OpcaoPessoa] = []
    for combo in itertools.product(*listas):
        escolhidos = tuple(c for c in combo if c is not None)
        if not escolhidos:
            continue
        if len({(c.loja_id, c.item_id) for c in escolhidos}) < len(escolhidos):
            slots_do_item: dict[tuple[str, str], set[frozenset]] = {}
            for s, c in zip(com_opcao, combo):
                if c is not None:
                    slots_do_item.setdefault((c.loja_id, c.item_id), set()).add(opcoes_do_slot[s])
            if any(len(conjuntos) > 1 for conjuntos in slots_do_item.values()):
                continue  # o mesmo item não vale por dois slots de pedidos diferentes
        # combo (A′F3): os slots que ele cobre não levam outro item (nada de "lanche + combo com lanche")
        cobertos = {s for c in escolhidos for s in c.cobre}
        if any(c is not None and s in cobertos for s, c in zip(com_opcao, combo)):
            continue
        if sum(len(c.cobre) for c in escolhidos) != len(cobertos):
            continue  # 2 combos cobrindo o mesmo slot: redundante (e inflaria a nota; achado M2 do Milan)
        preco = round(sum(c.preco for c in escolhidos), 2)
        if teto is not None and preco > teto + 1e-9:
            continue
        fora = [s for s, c in zip(com_opcao, combo) if c is None and s not in cobertos]
        penal = sum(PENAL_SLOT_PRINCIPAL_FORA if s == principal else PENAL_SLOT_EXTRA_FORA for s in fora)
        opcoes.append(_OpcaoPessoa(
            escolhidos=escolhidos, n_fora=len(fora), penal=penal, preco=preco,
            # o combo conta a nota dele para cada slot que atende
            sat=sum(c.nota * (1 + len(c.cobre)) for c in escolhidos) / (len(escolhidos) + len(cobertos)),
            lojas=frozenset(c.loja_id for c in escolhidos),
            mascara=sum({bits[c.loja_id] for c in escolhidos}),
            eta_max=max((c.eta_min for c in escolhidos if c.eta_min is not None), default=0),
            perecivel=any(c.perecivel and c.vertical == VERTICAL_RESTAURANTE for c in escolhidos),
        ))
    opcoes.sort(key=lambda o: (o.penal, -o.sat, o.preco, tuple((c.loja_id, c.item_id) for c in o.escolhidos)))
    return opcoes


def _penal_ausente(slots: list[str], validos: dict[str, list[Candidato]]) -> tuple[int, float]:
    """Slots com opção válida que ficam de fora quando a pessoa inteira fica de fora (e a penalidade deles)."""
    com_opcao = [s for s in slots if validos.get(s)]
    penal = sum(PENAL_SLOT_PRINCIPAL_FORA if s == slots[0] else PENAL_SLOT_EXTRA_FORA for s in com_opcao)
    return len(com_opcao), penal


def otimizar(
    candidatos: dict[str, list[Candidato]],
    pesos: Pesos,
    max_lojas: int = 2,
    taxas: dict[str, float] | None = None,
    top: int = 3,
    orcamentos: dict[str, float | None] | None = None,
    pessoa_de: dict[str, str] | None = None,
) -> list[Combinacao]:
    """Devolve as `top` melhores combinações distintas, por score decrescente.

    `candidatos` é por slot; `pessoa_de` (slot → pessoa) e `orcamentos` (por pessoa) são opcionais:
    sem `pessoa_de`, cada chave é uma pessoa com 1 item. Pessoa sem nenhum candidato válido fica fora
    (aparece em `componentes["pessoas_sem_opcao"]` e na `explicacao`); nada cabe → `[]`.
    """
    orcamentos = orcamentos or {}
    pessoa_de = pessoa_de or {}
    validos = filtrar_validos(candidatos, orcamentos, pessoa_de)
    grupos = _slots_por_pessoa(list(candidatos), pessoa_de)
    lojas_todas: list[str] = []
    for slots in grupos.values():
        for slot in slots:
            for c in validos[slot]:
                if c.loja_id not in lojas_todas:
                    lojas_todas.append(c.loja_id)
    bits = {loja: 1 << i for i, loja in enumerate(lojas_todas)}
    opcoes = {p: _opcoes_da_pessoa(slots, validos, orcamentos.get(p), bits) for p, slots in grupos.items()}
    sem_opcao = [p for p in grupos if not opcoes[p]]
    ativas = [p for p in grupos if opcoes[p]]
    if not ativas or top <= 0 or max_lojas <= 0:
        return []
    ausente = {p: _penal_ausente(grupos[p], validos) for p in ativas}

    # Referência de orçamento: orçamento da pessoa, ou a soma do preço médio de cada slot dela.
    orcamento_ref = 0.0
    for p in ativas:
        teto = orcamentos.get(p)
        if teto:
            orcamento_ref += teto
        else:
            orcamento_ref += sum(sum(c.preco for c in validos[s]) / len(validos[s]) for s in grupos[p] if validos[s])
    if orcamento_ref <= 0:
        orcamento_ref = 1.0

    # Cada conjunto de lojas (≤ max_lojas) recebe uma fatia igual do orçamento de avaliações,
    # para nenhum conjunto ficar sem ser visto. Uma combinação só conta no conjunto exato das lojas que usa.
    tamanhos = range(1, min(max_lojas, len(lojas_todas)) + 1)
    n_conjuntos = sum(math.comb(len(lojas_todas), k) for k in tamanhos)
    por_conjunto = max(200, min(MAX_COMBINACOES, MAX_AVALIACOES // max(1, n_conjuntos)))
    finalistas: list[tuple] = []  # heap com as melhores (score mais alto, depois custo menor)
    limite_heap = max(top * 4, 12)
    contador = itertools.count()

    for k in tamanhos:
        termo_lojas = pesos.delta_lojas * (k - 1)
        for conjunto in itertools.combinations(lojas_todas, k):
            alvo = sum(bits[l] for l in conjunto)
            listas: list[list] = []
            for p in ativas:
                dentro = [o for o in opcoes[p] if o.mascara & ~alvo == 0]
                listas.append(dentro or [None])  # None = a pessoa fica de fora neste conjunto de lojas
            if all(l == [None] for l in listas):
                continue
            taxa_conhecida = taxas is not None and all(l in taxas for l in conjunto)
            soma_taxas = sum(taxas[l] for l in conjunto) if taxa_conhecida else 0.0
            for escolha in itertools.product(*_podar(listas, por_conjunto)):
                mascara = 0
                for o in escolha:
                    if o is not None:
                        mascara |= o.mascara
                if mascara != alvo:
                    continue  # esta combinação é contada no conjunto de lojas menor
                soma_sat = 0.0
                minimo = 1e9
                preco = 0.0
                penal_slots = 0.0
                atraso = 0
                tem_perecivel = False
                for p, o in zip(ativas, escolha):
                    if o is None:
                        minimo = 0.0
                        penal_slots += ausente[p][1]
                        continue
                    soma_sat += o.sat
                    minimo = min(minimo, o.sat)
                    preco += o.preco
                    penal_slots += o.penal
                    atraso = max(atraso, o.eta_max)
                    tem_perecivel = tem_perecivel or o.perecivel
                custo_total = round(preco + soma_taxas, 2)
                penal = 0.0
                if tem_perecivel:
                    penal = _penal_perecivel([c for o in escolha if o is not None for c in o.escolhidos])
                score = (soma_sat / len(ativas) + pesos.alfa_justica * minimo
                         - pesos.beta_custo * (custo_total / orcamento_ref)
                         - pesos.gama_atraso * (atraso / TEMPO_ALVO_MIN)
                         - termo_lojas - pesos.epsilon_perecivel * penal - penal_slots)
                # 1º critério: atender o máximo de slots (deixar item de fora só se não couber no orçamento ou
                # no limite de lojas); só depois o score. Assim δ/custo/perecível nunca "compram" um item cortado.
                item = (-round(penal_slots, 4), round(score, 4), -custo_total, -next(contador), escolha)
                if len(finalistas) < limite_heap:
                    heapq.heappush(finalistas, item)
                elif item[:3] > finalistas[0][:3]:
                    heapq.heapreplace(finalistas, item)

    resultado = []
    for _, _, _, _, escolha in finalistas:
        escolhidos = [c for o in escolha if o is not None for c in o.escolhidos]
        lojas: list[str] = []
        for c in escolhidos:
            if c.loja_id not in lojas:
                lojas.append(c.loja_id)
        chave = tuple((c.participante_id, c.loja_id, c.item_id) for c in escolhidos)
        resultado.append(_pontuar(escolha, ativas, escolhidos, lojas, chave, pesos, taxas, orcamento_ref,
                                  ausente, sem_opcao))
    resultado.sort(key=lambda par: par[0])
    return [comb for _, comb in resultado[:top]]


def _pontuar(escolha, ativas, escolhidos, lojas, chave, pesos, taxas, orcamento_ref, ausente, sem_opcao):
    sats = [o.sat if o is not None else 0.0 for o in escolha]
    presentes = [o.sat for o in escolha if o is not None]
    fora_pessoas = [p for p, o in zip(ativas, escolha) if o is None]
    media = sum(sats) / len(sats)
    minimo = min(sats)
    slots_fora = sum(o.n_fora for o in escolha if o is not None) + sum(ausente[p][0] for p in fora_pessoas)
    penal_slots = sum(o.penal for o in escolha if o is not None) + sum(ausente[p][1] for p in fora_pessoas)

    soma_itens = sum(c.preco for c in escolhidos)
    taxa_conhecida = taxas is not None and all(l in taxas for l in lojas)
    soma_taxas = sum(taxas[l] for l in lojas) if taxa_conhecida else 0.0
    custo_total = round(soma_itens + soma_taxas, 2)
    etas = [c.eta_min for c in escolhidos if c.eta_min is not None]
    atraso_max = max(etas) if etas else 0
    penal = _penal_perecivel(escolhidos)

    termo_justica = pesos.alfa_justica * minimo
    termo_custo = pesos.beta_custo * (custo_total / orcamento_ref)
    termo_atraso = pesos.gama_atraso * (atraso_max / TEMPO_ALVO_MIN)
    termo_lojas = pesos.delta_lojas * (len(lojas) - 1)
    termo_perecivel = pesos.epsilon_perecivel * penal
    score = (media + termo_justica - termo_custo - termo_atraso - termo_lojas - termo_perecivel - penal_slots)

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
        "slots_fora": float(slots_fora),
        "termo_slots_fora": round(-penal_slots, 4),
        "pessoas_sem_opcao": float(len(sem_opcao) + len(fora_pessoas)),
    }
    combinacao = Combinacao(
        escolhas={c.participante_id: c for c in escolhidos},
        cobertos={s: c.participante_id for c in escolhidos for s in c.cobre},
        lojas=lojas,
        score=round(score, 4),
        componentes=componentes,
        taxa_conhecida=taxa_conhecida,
        explicacao=_explicar(len(lojas), min(presentes) if presentes else 0.0, custo_total, taxa_conhecida,
                             atraso_max or None, penal, [*sem_opcao, *fora_pessoas],
                             slots_fora=int(slots_fora - sum(ausente[p][0] for p in fora_pessoas))),
    )
    # Ordem: menos itens de fora (penalidade dos slots), depois score maior, mais barato, chave estável.
    return ((round(penal_slots, 4), -score, custo_total, chave), combinacao)
