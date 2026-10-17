"""Motor do Match (contrato C5): desejos do grupo → top 3 combinações, com avisos e rastro das tools MCP.

Fluxo: listAddresses → interpretar (slots) → buscar (searchOffers…) → julgar (nota/motivo) → otimizar.
Preço, prazo e loja vêm só das tools (via `busca.py`); o LLM só interpreta e dá nota. Sem LLM, tudo roda no
fallback determinístico.
"""

from __future__ import annotations

import asyncio
import re

from ..config import Config
from ..ifood_mcp.cliente import ClienteIFood, ErroMCP
from .busca import buscar_detalhado, ler_endereco
from .interprete import CONSULTA_RESTRICAO, interpretar
from .juiz import ROTULO_RESTRICAO, avaliar
from .modelos import Candidato, Combinacao, Desejo, Intencao, para_dict
from .otimizador import otimizar, pesos_por_perfil

MAX_LOJAS = 3  # cada loja a mais = +1 pedido, +1 taxa, +1 entrega (o δ do otimizador penaliza; os avisos deixam o custo explícito)
TOP = 3
NOTA_MINIMA = 0.25  # abaixo disso o item quase não tem a ver com o pedido; só fica se não houver nada melhor


def _reais(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + (texto[:-3] if texto.endswith(",00") else texto)


def _rotulo(intencao: Intencao) -> str:
    """Nome curto do item do slot ("sorvete", "japonês"); vazio se a pessoa não citou comida."""
    if not intencao.consultas:
        return ""
    texto = intencao.consultas[0]
    for termo in CONSULTA_RESTRICAO.values():
        texto = re.sub(rf"\s*\b{re.escape(termo)}\b", "", texto, flags=re.IGNORECASE)
    return texto.strip()


def _o_que(intencao: Intencao) -> str:
    """"nada vegano", "sorvete sem lactose"… para avisos."""
    base = _rotulo(intencao) or "nada"
    restricoes = " ".join(ROTULO_RESTRICAO.get(r, r) for r in intencao.restricoes)
    return f"{base} {restricoes}".strip()


def _validos(intencao: Intencao, candidatos: list[Candidato]) -> list[Candidato]:
    teto = intencao.orcamento_max
    return [c for c in candidatos if not c.viola and (teto is None or c.preco <= teto + 1e-9)]


def _sem_irrelevantes(candidatos: list[Candidato]) -> list[Candidato]:
    """Tira itens com nota < NOTA_MINIMA quando o slot tem opções que atendem ao pedido."""
    bons = [c for c in candidatos if c.nota >= NOTA_MINIMA]
    return bons if bons else candidatos


def _nomes_na_explicacao(texto: str, nomes: dict[str, str]) -> str:
    partes = []
    for parte in texto.split(" · "):
        prefixo = "sem opção válida para "
        if parte.startswith(prefixo):
            ids = parte[len(prefixo):].split(", ")
            parte = prefixo + ", ".join(nomes.get(i, i) for i in ids)
        partes.append(parte)
    return " · ".join(partes)


def _avisos_da_melhor(melhor: Combinacao, slots: list[tuple[Desejo, Intencao]], validos: dict[str, list[Candidato]],
                      pessoa_de: dict[str, str], nomes: dict[str, str]) -> tuple[list[str], list[str]]:
    """Avisos sobre o que ficou de fora na melhor combinação; devolve (avisos, slots que ficaram de fora)."""
    avisos: list[str] = []
    fora: list[str] = []
    presentes = {pessoa_de[s] for s in melhor.escolhas}
    gasto: dict[str, float] = {}
    for slot, c in melhor.escolhas.items():
        gasto[pessoa_de[slot]] = gasto.get(pessoa_de[slot], 0.0) + c.preco
    pessoas_avisadas: set[str] = set()
    for desejo, intencao in slots:
        slot, pid = intencao.participante_id, desejo.participante_id
        if slot in melhor.escolhas or not validos[slot]:
            continue
        fora.append(slot)
        if pid not in presentes:
            if pid not in pessoas_avisadas:
                pessoas_avisadas.add(pid)
                avisos.append(f"Nenhuma opção de {nomes[pid]} coube junto com as outras em até {MAX_LOJAS} lojas.")
            continue
        rotulo = _rotulo(intencao) or "um item"
        teto = intencao.orcamento_max
        mais_barato = min(c.preco for c in validos[slot])
        if teto is not None and gasto.get(pid, 0.0) + mais_barato > teto + 1e-9:
            avisos.append(f"{rotulo.capitalize()} de {nomes[pid]} ficou de fora: não cabe no orçamento de "
                          f"{_reais(teto)} junto com o resto.")
        else:
            avisos.append(f"{rotulo.capitalize()} de {nomes[pid]} ficou de fora para o pedido ficar em até "
                          f"{MAX_LOJAS} lojas.")
    return avisos, fora


async def rodar_match(cfg: Config, cliente: ClienteIFood, desejos: list[Desejo]) -> dict:
    """Roda o Match para o grupo. Nunca inventa preço; erro de tool vira aviso legível."""
    resultado: dict = {"combinacoes": [], "intencoes": [], "avisos": [], "rastro": [], "endereco": None,
                       "pessoas": []}
    avisos: list[str] = resultado["avisos"]

    try:
        endereco = ler_endereco(await cliente.chamar("listAddresses"))
    except ErroMCP as e:
        avisos.append(f"Não consegui ler os endereços no iFood: {e}")
        endereco = None
    if endereco is None:
        if not avisos:
            avisos.append("Nenhum endereço salvo na conta do iFood. Cadastre um endereço no app e rode de novo.")
        resultado["rastro"] = cliente.rastro_como_dicts()
        return resultado
    resultado["endereco"] = {"id": endereco["id"], "apelido": endereco["apelido"], "texto": endereco["texto"]}
    if not desejos:
        avisos.append("Ninguém respondeu ainda.")
        resultado["rastro"] = cliente.rastro_como_dicts()
        return resultado

    nomes = {d.participante_id: d.nome for d in desejos}
    interpretacoes = await asyncio.gather(*(interpretar(cfg, d) for d in desejos))
    slots: list[tuple[Desejo, Intencao]] = [(d, i) for d, lista in zip(desejos, interpretacoes) for i in lista]
    pessoa_de = {i.participante_id: d.participante_id for d, i in slots}

    buscas = []
    for _, intencao in slots:  # em sequência: o rastro fica na ordem em que as tools foram chamadas
        buscas.append(await buscar_detalhado(cliente, intencao, endereco))
    julgados = await asyncio.gather(*(
        avaliar(cfg, d, i, cands, det) for (d, i), (cands, det) in zip(slots, buscas)
    ))
    candidatos = {i.participante_id: _sem_irrelevantes(lista) for (_, i), lista in zip(slots, julgados)}
    validos = {slot: _validos(i, candidatos[slot]) for slot, i in ((i.participante_id, i) for _, i in slots)}

    for desejo, intencao in slots:
        if not validos[intencao.participante_id]:
            teto = f" até {_reais(intencao.orcamento_max)}" if intencao.orcamento_max else ""
            avisos.append(f"Não achei {_o_que(intencao)}{teto} para {desejo.nome}.")

    orcamentos = {d.participante_id: lista[0].orcamento_max for d, lista in zip(desejos, interpretacoes)}
    pesos = pesos_por_perfil([lista[0].perfil for lista in interpretacoes])
    combos = otimizar(candidatos, pesos, max_lojas=MAX_LOJAS, top=TOP, orcamentos=orcamentos, pessoa_de=pessoa_de)

    if not combos:
        avisos.append("Nenhuma combinação coube nas regras (orçamento e restrições). "
                      "Tente aumentar o orçamento ou tirar uma restrição.")
    else:
        melhor = combos[0]
        extras, fora = _avisos_da_melhor(melhor, slots, validos, pessoa_de, nomes)
        avisos.extend(extras)
        if fora:  # mediação: mostra o que daria para incluir com mais uma loja (sempre com confirmação humana)
            com_mais = otimizar(candidatos, pesos, max_lojas=MAX_LOJAS + 1, top=1, orcamentos=orcamentos,
                                pessoa_de=pessoa_de)
            def mantem(pid: str) -> bool:  # a pessoa ganha o item sem piorar o que já tinha
                return all(com_mais[0].escolhas.get(s) is not None
                           and com_mais[0].escolhas[s].nota >= c.nota - 0.1
                           for s, c in melhor.escolhas.items() if pessoa_de[s] == pid)

            ganhos = [s for s in fora if com_mais and s in com_mais[0].escolhas and mantem(pessoa_de[s])]
            if ganhos:
                rotulos = {i.participante_id: (_rotulo(i) or "item") for _, i in slots}
                lista = ", ".join(f"{rotulos[s]} de {nomes[pessoa_de[s]]}" for s in ganhos)
                avisos.append(f"Com {MAX_LOJAS + 1} lojas dá para incluir {lista} "
                              "(+1 pedido, +1 taxa de entrega e +1 entrega).")
        n = len(melhor.lojas)
        if n > 1:
            avisos.append(f"{n} lojas = {n} pedidos, {n} taxas de entrega e {n} entregas (podem chegar em "
                          "horários diferentes).")
        if not melhor.taxa_conhecida:
            avisos.append("A taxa de entrega de cada loja só aparece no carrinho, antes de você confirmar.")

    combinacoes = [para_dict(c) for c in combos]
    for c in combinacoes:
        c["explicacao"] = _nomes_na_explicacao(c["explicacao"], nomes)
    resultado["combinacoes"] = combinacoes
    resultado["intencoes"] = [para_dict(i) for _, i in slots]
    resultado["pessoas"] = [
        {"participante_id": d.participante_id, "nome": d.nome,
         "slots": [i.participante_id for i in lista], "orcamento_max": lista[0].orcamento_max,
         "perfil": lista[0].perfil}
        for d, lista in zip(desejos, interpretacoes)
    ]
    resultado["rastro"] = cliente.rastro_como_dicts()
    return resultado

