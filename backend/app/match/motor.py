"""Motor do Match (contrato C5): desejos do grupo → top 3 combinações, com avisos e rastro das tools MCP.

Fluxo: listAddresses → interpretar (slots) → buscar (searchOffers…) → julgar (nota/motivo) → leilão das lojas
(`leilao.py`, C11/C12; `MATCH_LEILAO=off` desliga) → otimizar (só o que foi ofertado).
Preço, prazo e loja vêm só das tools (via `busca.py`); o LLM só interpreta e dá nota. Sem LLM, tudo roda no
fallback determinístico.
"""

from __future__ import annotations

import asyncio
import dataclasses
import re

from ..config import Config
from ..ifood_mcp.cliente import ClienteIFood, ErroMCP
from .busca import CONFIRMA, buscar_detalhado, ler_endereco
from .interprete import CONSULTA_RESTRICAO, interpretar
from .juiz import ROTULO_RESTRICAO, avaliar, bebida_sem_pedir
from .leilao import afinidade_e_felizes, carregar_politica, fechar_leilao, rodar_leilao
from .modelos import Candidato, Combinacao, Desejo, Intencao, para_dict
from .otimizador import otimizar, pesos_por_perfil

MAX_LOJAS = 3  # cada loja a mais = +1 pedido, +1 taxa, +1 entrega (o δ do otimizador penaliza; os avisos deixam o custo explícito)
TOP = 3
NOTA_MINIMA = 0.25  # abaixo disso o item quase não tem a ver com o pedido; só fica se não houver nada melhor
NOTA_RELEVANTE = 0.5  # se o melhor item do slot fica abaixo disso, o pedido não está no cardápio: vira "opção aproximada"
PREFIXO_APROXIMADA = "Opção aproximada: "
MAX_MOTIVO = 90


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


def _pediu(desejo: Desejo, intencao: Intencao) -> str:
    """O que a pessoa pediu, para o aviso "Não achei X" (cai na frase dela se o slot só tem restrição)."""
    def sem_orcamento(texto: str) -> str:
        texto = re.sub(r"[,;]?\s*\b(até|ate|por|no máximo|max(imo)?)\b\s*(r\$)?\s*\d[\d.,]*\s*(reais)?\s*$", "", texto,
                       flags=re.IGNORECASE)
        return " ".join(texto.split()).strip(" ,;.")

    if _rotulo(intencao):
        return sem_orcamento(_o_que(intencao))
    texto = sem_orcamento(desejo.texto or "")
    return texto[:40] if texto else _o_que(intencao)


def _marcar_aproximada(candidatos: list[Candidato]) -> list[Candidato]:
    """Cópias dos candidatos com o motivo começando por "Opção aproximada:" (o front destaca)."""
    marcados = []
    for c in candidatos:
        if c.motivo.startswith(PREFIXO_APROXIMADA):
            marcados.append(c)
            continue
        motivo = (PREFIXO_APROXIMADA + c.motivo).strip()[:MAX_MOTIVO]
        marcados.append(dataclasses.replace(c, motivo=motivo))
    return marcados


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

    # relevância: o melhor item do slot precisa passar de NOTA_RELEVANTE; senão é "opção aproximada" (e avisa)
    fracos = [(d, i) for d, i in slots
              if validos[i.participante_id] and max(c.nota for c in validos[i.participante_id]) < NOTA_RELEVANTE]
    for desejo, intencao in slots:
        slot = intencao.participante_id
        if not validos[slot]:
            teto = f" até {_reais(intencao.orcamento_max)}" if intencao.orcamento_max else ""
            avisos.append(f"Não achei {_o_que(intencao)}{teto} para {desejo.nome}.")
    descartados: list[tuple[Desejo, Intencao]] = []
    for (desejo, intencao), (_, detalhes) in zip(slots, buscas):
        if (desejo, intencao) not in fracos:
            continue
        slot = intencao.participante_id
        candidatos[slot] = [c for c in candidatos[slot]
                            if not bebida_sem_pedir(intencao, detalhes.get((c.loja_id, c.item_id), {}))]
        validos[slot] = _validos(intencao, candidatos[slot])
        if not validos[slot]:  # só sobrou bebida para quem pediu comida: não sugere nada
            descartados.append((desejo, intencao))
            avisos.append(f"Não achei {_pediu(desejo, intencao)} para {desejo.nome}. Quer mudar o pedido?")
    fracos = [f for f in fracos if f not in descartados]
    for desejo, intencao in fracos:
        slot = intencao.participante_id
        proximo = max(validos[slot], key=lambda c: (c.nota, -c.preco))
        avisos.append(f"Não achei {_pediu(desejo, intencao)} para {desejo.nome}; a opção mais próxima é "
                      f"{proximo.item_nome} ({proximo.loja_nome}). Quer mudar o pedido?")
        candidatos[slot] = _marcar_aproximada(candidatos[slot])
        validos[slot] = _validos(intencao, candidatos[slot])

    # restrição explícita que nenhum item do slot confirma por tag: não elimina, só avisa
    avisados: set[tuple[str, str]] = set()
    for (desejo, intencao), (_, detalhes) in zip(slots, buscas):
        slot, pid = intencao.participante_id, desejo.participante_id
        for r in intencao.restricoes:
            if not validos[slot] or (pid, r) in avisados:
                continue
            confirma = CONFIRMA.get(r, {r})
            if any(set(detalhes.get((c.loja_id, c.item_id), {}).get("tags", [])) & confirma for c in validos[slot]):
                continue
            avisados.add((pid, r))
            quem = f" para {desejo.nome}" if len(nomes) > 1 else ""
            avisos.append(f"Nenhum item confirma '{ROTULO_RESTRICAO.get(r, r)}'{quem} — confirme com a loja.")

    ids_fracos = {i.participante_id for _, i in fracos}
    nada_relevante = bool(fracos or descartados) and not any(
        validos[i.participante_id] and i.participante_id not in ids_fracos for _, i in slots)

    orcamentos = {d.participante_id: lista[0].orcamento_max for d, lista in zip(desejos, interpretacoes)}
    pesos = pesos_por_perfil([lista[0].perfil for lista in interpretacoes])

    # leilão: cada loja oferta só o que quer vender; o otimizador (e a mediação) só enxerga o ofertado
    leilao = None
    if getattr(cfg, "match_leilao", True):
        detalhes_todos = {chave: det for _, detalhes in buscas for chave, det in detalhes.items()}
        demonstracao = getattr(cliente, "modo", "demo") == "demo"
        politica = carregar_politica() if demonstracao else {}  # no modo real nenhuma loja é patrocinada
        candidatos, leilao = await rodar_leilao(cfg, slots, candidatos, detalhes_todos, nomes, politica)
        leilao["demonstracao"] = demonstracao
        validos = {slot: _validos(i, candidatos[slot]) for slot, i in ((i.participante_id, i) for _, i in slots)}
    if nada_relevante:  # ninguém tem um item que passe do limiar: sem combinação (a API devolve 409 legível)
        combos = []
        avisos[:] = [a.removesuffix(" Quer mudar o pedido?") for a in avisos]  # a pergunta vai uma vez só, no fim
        avisos.append("Nada do que foi pedido está nos cardápios das lojas. Quer mudar o pedido?")
    else:
        combos = otimizar(candidatos, pesos, max_lojas=MAX_LOJAS, top=TOP, orcamentos=orcamentos,
                          pessoa_de=pessoa_de)

    if nada_relevante:
        pass  # já avisado acima
    elif not combos:
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
        c["afinidade"], c["felizes"] = afinidade_e_felizes(c, list(nomes), pessoa_de)
    resultado["combinacoes"] = combinacoes
    if leilao is not None:
        resultado["leilao"] = fechar_leilao(leilao, combinacoes, slots, pessoa_de, nomes)
    resultado["intencoes"] = [para_dict(i) for _, i in slots]
    resultado["pessoas"] = [
        {"participante_id": d.participante_id, "nome": d.nome,
         "slots": [i.participante_id for i in lista], "orcamento_max": lista[0].orcamento_max,
         "perfil": lista[0].perfil}
        for d, lista in zip(desejos, interpretacoes)
    ]
    resultado["rastro"] = cliente.rastro_como_dicts()
    return resultado

