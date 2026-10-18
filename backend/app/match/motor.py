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
from .busca import CONFIRMA, buscar_detalhado, buscar_na_loja, ler_endereco
from .interprete import CONSULTA_RESTRICAO, MAX_SLOTS, aplicar_quantidades, interpretar, itens_alem_do_limite
from .juiz import ROTULO_RESTRICAO, acertos, avaliar, bebida_sem_pedir, nota_fallback
from .leilao import afinidade_e_felizes, carregar_politica, fechar_leilao, rodar_leilao
from .modelos import Candidato, Combinacao, Desejo, Intencao, para_dict
from .otimizador import otimizar, pesos_por_perfil

MAX_LOJAS_DO_PRINCIPAL = 3  # lojas do 1º item da pessoa onde os outros itens dela também são procurados (A′F1)
MAX_LOJAS = 3  # cada loja a mais = +1 pedido, +1 taxa, +1 entrega (o δ do otimizador penaliza; os avisos deixam o custo explícito)
TOP = 3
NOTA_MINIMA = 0.25  # abaixo disso o item quase não tem a ver com o pedido; só fica se não houver nada melhor
NOTA_RELEVANTE = 0.5  # se o melhor item do slot fica abaixo disso, o pedido não está no cardápio: vira "opção aproximada"
PREFIXO_APROXIMADA = "Opção aproximada: "
MAX_MOTIVO = 90
MSG_SEM_ENDERECO = ("Nenhum endereço salvo na conta do iFood. Cadastre um endereço de entrega no app do iFood e "
                    "rode o Match de novo.")
MSG_ENDERECO_SEM_ID = ("O endereço do iFood veio sem identificador (addressId): dá para ver as opções, mas não para "
                       "montar o carrinho. Confira o endereço no app do iFood e rode o Match de novo.")
MSG_ENDERECO_SEM_COORDENADAS = ("O endereço do iFood veio sem coordenadas (latitude/longitude), e sem elas a busca "
                                "não acha as lojas que entregam aí. Abra o endereço no app do iFood, confirme o local "
                                "no mapa e rode o Match de novo.")
MSG_ENDERECO_MOCK = ("Endereço de teste: a conta do iFood não tem endereço salvo, então a busca e o carrinho usam um "
                     "local fixo de exemplo. O pedido real só sai com um endereço salvo na conta.")
# addressId fixo do mock: o createCart real aceita (testado em 18/10) e devolve taxa e total reais.
ID_ENDERECO_MOCK = "00000000-0000-4000-8000-000000000000"


def endereco_mock(cfg: Config) -> dict | None:
    """Endereço mockado do `.env` (`IFOOD_MCP_ENDERECO_MOCK=lat,lng`), ou None se desligado/inválido.

    Por que existe: o `createAddress` do MCP real falha sempre com ADR-2001 nas contas de teste (bug 6 de
    `docs/testes/bugs.md`; erro sem documentação no portal), e sem endereço salvo o Match nem busca. Com o mock,
    a busca usa estas coordenadas e o carrinho real é montado com `ID_ENDERECO_MOCK`. Tirar quando o iFood
    liberar o endereço nas contas de teste."""
    try:
        lat, lng = (float(x) for x in cfg.ifood_mcp_endereco_mock.split(","))
    except ValueError:
        return None
    return {"id": ID_ENDERECO_MOCK, "apelido": "Teste", "texto": "Endereço de teste (mock)",
            "latitude": lat, "longitude": lng}


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


# item que se apresenta como combo/kit (nome ou seção do cardápio): "Combo smash + batata + refri", "Kit escova"
_RE_COMBO = re.compile(r"\bcombos?\b|\bkits?\b|\+|\bacompanha\b", re.IGNORECASE)


def _montar_combos(slots: list[tuple[Desejo, Intencao]], candidatos: dict[str, list[Candidato]],
                   detalhes: dict[tuple[str, str], dict]) -> None:
    """Combos (A′F3, etapa 05): um combo/kit da loja que cita 2+ itens da mesma pessoa vira UM candidato que cobre
    esses itens (`cobre`), com o preço contado uma vez. O otimizador compara "combo" com "itens avulsos" e nunca
    escolhe os dois juntos. O item-combo deixa de valer como avulso nesses slots ("hambúrguer, batata e refri" não
    vira lanche + batata + combo). Altera `candidatos` no lugar."""
    por_pessoa: dict[str, list[Intencao]] = {}
    for desejo, intencao in slots:
        por_pessoa.setdefault(desejo.participante_id, []).append(intencao)
    for intencoes in por_pessoa.values():
        if len(intencoes) < 2:
            continue
        itens: dict[tuple[str, str], Candidato] = {}
        for i in intencoes:
            for c in candidatos.get(i.participante_id, []):
                if not c.cobre and not c.viola:
                    itens.setdefault((c.loja_id, c.item_id), c)
        for chave, c in itens.items():
            det = detalhes.get(chave, {})
            if not (_RE_COMBO.search(c.item_nome) or _RE_COMBO.search(str(det.get("categoria", "")))):
                continue
            atende = [i for i in intencoes if acertos(i, c, det)]
            if len(atende) < 2:
                continue
            notas = [x.nota for i in atende for x in candidatos.get(i.participante_id, [])
                     if (x.loja_id, x.item_id) == chave]
            rotulos = [r for r in (_rotulo(i) for i in atende) if r]
            combo = dataclasses.replace(
                c, participante_id=atende[0].participante_id, cobre=[i.participante_id for i in atende[1:]],
                nota=max(notas or [c.nota]),
                motivo=("Combo com " + " + ".join(rotulos) + ": 1 item só, preço do combo")[:MAX_MOTIVO])
            for i in atende:
                candidatos[i.participante_id] = [x for x in candidatos.get(i.participante_id, [])
                                                 if (x.loja_id, x.item_id) != chave]
            candidatos[atende[0].participante_id].append(combo)


MARGEM_VAREJO = 0.15  # no varejo, só concorrem itens com nota até isto abaixo do melhor (A′F5)


def _de_varejo(intencao: Intencao) -> bool:
    return bool(intencao.verticais) and "RESTAURANT" not in intencao.verticais


def _so_os_melhores(candidatos: list[Candidato]) -> list[Candidato]:
    """Varejo: produto diferente não ganha por ser mais barato (ração de gato para quem pediu ração de cachorro).
    O preço decide só entre itens que atendem igualmente bem."""
    if not candidatos:
        return candidatos
    melhor = max(c.nota for c in candidatos)
    return [c for c in candidatos if c.nota >= melhor - MARGEM_VAREJO - 1e-9]


def _nomes_na_explicacao(texto: str, nomes: dict[str, str]) -> str:
    partes = []
    for parte in texto.split(" · "):
        prefixo = "sem opção válida para "
        if parte.startswith(prefixo):
            ids = parte[len(prefixo):].split(", ")
            parte = prefixo + ", ".join(nomes.get(i, i) for i in ids)
        partes.append(parte)
    return " · ".join(partes)


async def _completar_na_mesma_loja(cliente: ClienteIFood, slots: list[tuple[Desejo, Intencao]],
                                   buscas: list[tuple[list[Candidato], dict]], julgados: list[list[Candidato]],
                                   endereco: dict) -> list[list[Candidato]]:
    """Pedido completo (A′F1, etapa 05): o 2º item em diante de cada pessoa também é procurado DENTRO das lojas
    mais prováveis do 1º item dela (`searchOffers` + `refinements.merchantId`). Sem isso, "pizza e um refri" buscava
    refri na cidade toda e o refri vinha de outra loja (+1 taxa, +1 entrega) ou ficava de fora.

    Roda depois do juiz (bug 30): as lojas do 1º item são ordenadas pela nota e pelo preço do melhor item delas —
    a ordem em que o otimizador tende a escolher —, não pela ordem da busca. Os itens achados na loja ganham a nota
    do juiz determinístico (sem chamada extra ao LLM: o Groq grátis tem limite de tokens por minuto)."""
    por_pessoa: dict[str, list[int]] = {}
    for k, (desejo, _) in enumerate(slots):
        por_pessoa.setdefault(desejo.participante_id, []).append(k)
    for indices in por_pessoa.values():
        if len(indices) < 2:
            continue
        melhor_da_loja: dict[str, tuple[float, float, str]] = {}  # loja → (nota, -preço, vertical)
        for c in julgados[indices[0]]:
            if c.viola:
                continue
            chave = (c.nota, -c.preco, c.vertical)
            if c.loja_id not in melhor_da_loja or chave[:2] > melhor_da_loja[c.loja_id][:2]:
                melhor_da_loja[c.loja_id] = chave
        lojas = sorted(melhor_da_loja, key=lambda l: melhor_da_loja[l][:2], reverse=True)[:MAX_LOJAS_DO_PRINCIPAL]
        for k in indices[1:]:
            desejo, intencao = slots[k]
            detalhes = buscas[k][1]
            for loja_id in lojas:
                if any(c.loja_id == loja_id and not c.viola for c in julgados[k]):
                    continue  # a busca normal já achou o item nessa loja
                novos, det_novos = await buscar_na_loja(cliente, intencao, endereco, loja_id,
                                                        melhor_da_loja[loja_id][2])
                vistos = {(c.loja_id, c.item_id) for c in julgados[k]}
                novos = [c for c in novos if (c.loja_id, c.item_id) not in vistos]
                if not novos:
                    continue
                detalhes.update(det_novos)
                todos = julgados[k] + novos
                for c in novos:
                    c.nota, c.motivo = nota_fallback(intencao, c, det_novos.get((c.loja_id, c.item_id), {}), todos,
                                                     ha_acertos=True)
                julgados[k] = todos
    return julgados


def _economia_de_taxa(melhor: Combinacao, validos: dict[str, list[Candidato]], taxas: dict[str, float]) -> str:
    """"Juntando em 2 lojas (em vez de 3), o grupo economiza R$ 7,50 de taxa": compara com cada item vindo da loja
    do item de maior nota (o que cada um escolheria sozinho). Vazio se não economiza ou se falta alguma taxa."""
    sozinho: list[str] = []
    for slot in melhor.escolhas:
        if not validos.get(slot):
            continue
        preferido = max(validos[slot], key=lambda c: (c.nota, -c.preco))
        if preferido.loja_id not in sozinho:
            sozinho.append(preferido.loja_id)
    if len(sozinho) <= len(melhor.lojas) or any(l not in taxas for l in [*sozinho, *melhor.lojas]):
        return ""
    diferenca = round(sum(taxas[l] for l in sozinho) - sum(taxas[l] for l in melhor.lojas), 2)
    if diferenca < 0.01:
        return ""
    n = len(melhor.lojas)
    return (f"Juntando os itens em {n} loja{'s' if n != 1 else ''}, o pedido paga {_reais(diferenca)} a menos de taxa "
            f"de entrega do que se cada item viesse da loja com a melhor nota ({len(sozinho)} lojas).")


def _avisos_da_melhor(melhor: Combinacao, slots: list[tuple[Desejo, Intencao]], validos: dict[str, list[Candidato]],
                      pessoa_de: dict[str, str], nomes: dict[str, str],
                      ja_avisados: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Avisos sobre o que ficou de fora na melhor combinação; devolve (avisos, slots que ficaram de fora).
    `ja_avisados`: slots que já têm "Não achei X" (não ganham um 2º motivo que contradiz o 1º)."""
    avisos: list[str] = []
    fora: list[str] = []
    presentes = {pessoa_de[s] for s in [*melhor.escolhas, *melhor.cobertos]}
    gasto: dict[str, float] = {}
    for slot, c in melhor.escolhas.items():
        gasto[pessoa_de[slot]] = gasto.get(pessoa_de[slot], 0.0) + c.preco
    pessoas_avisadas: set[str] = set()
    limite_atingido = len(melhor.lojas) >= MAX_LOJAS
    for desejo, intencao in slots:
        slot, pid = intencao.participante_id, desejo.participante_id
        if slot in melhor.escolhas or slot in melhor.cobertos or not validos[slot] or slot in (ja_avisados or set()):
            continue
        fora.append(slot)
        if pid not in presentes:
            if pid not in pessoas_avisadas:
                pessoas_avisadas.add(pid)
                if limite_atingido:
                    avisos.append(f"Nenhuma opção de {nomes[pid]} coube junto com as outras em até {MAX_LOJAS} lojas.")
                else:
                    avisos.append(f"Nenhuma opção de {nomes[pid]} coube junto com o resto do pedido.")
            continue
        rotulo = _rotulo(intencao) or "um item"
        teto = intencao.orcamento_max
        mais_barato = min(c.preco for c in validos[slot])
        if teto is not None and gasto.get(pid, 0.0) + mais_barato > teto + 1e-9:
            avisos.append(f"{rotulo.capitalize()} de {nomes[pid]} ficou de fora: não cabe no orçamento de "
                          f"{_reais(teto)} junto com o resto.")
        elif limite_atingido:
            avisos.append(f"{rotulo.capitalize()} de {nomes[pid]} ficou de fora para o pedido ficar em até "
                          f"{MAX_LOJAS} lojas.")
        else:  # só fala do limite de lojas quando ele foi de fato atingido
            avisos.append(f"{rotulo.capitalize()} de {nomes[pid]} ficou de fora: não coube junto com o resto "
                          "do pedido.")
    return avisos, fora


async def rodar_match(cfg: Config, cliente: ClienteIFood, desejos: list[Desejo]) -> dict:
    """Roda o Match para o grupo. Nunca inventa preço; erro de tool vira aviso legível."""
    resultado: dict = {"combinacoes": [], "intencoes": [], "avisos": [], "rastro": [], "endereco": None,
                       "pessoas": []}
    avisos: list[str] = resultado["avisos"]

    falha_enderecos: str | None = None  # detalhe do erro do listAddresses
    try:
        endereco = ler_endereco(await cliente.chamar("listAddresses"))
    except ErroMCP as e:
        if "(401)" in str(e):  # login recusado no meio da sessão: a rota devolve 401 com a mensagem certa
            raise
        falha_enderecos = str(e)
        endereco = None
    if endereco is None and (mock := endereco_mock(cfg)):
        # lista vazia (ADR-2001 no createAddress) ou listAddresses fora do ar (bug 23): usa o mock do .env
        endereco = mock
        avisos.append(f"Não consegui ler os endereços no iFood ({falha_enderecos}); usando o endereço de teste."
                      if falha_enderecos else MSG_ENDERECO_MOCK)
    elif falha_enderecos:
        avisos.append(f"Não consegui ler os endereços no iFood: {falha_enderecos}")
    if endereco is None:
        if not avisos:
            avisos.append(MSG_SEM_ENDERECO)
        resultado["problema"] = "endereco"  # a rota não diz "nenhum pedido serve para todos": o problema é outro
        resultado["rastro"] = cliente.rastro_como_dicts()
        return resultado
    resultado["endereco"] = {"id": endereco["id"], "apelido": endereco["apelido"], "texto": endereco["texto"]}
    if not endereco.get("id"):
        avisos.append(MSG_ENDERECO_SEM_ID)  # avisa já ao rodar (escolher sem id devolve 409)
    sem_coordenadas = endereco.get("latitude") is None or endereco.get("longitude") is None
    if not desejos:
        avisos.append("Ninguém respondeu ainda.")
        resultado["rastro"] = cliente.rastro_como_dicts()
        return resultado

    nomes = {d.participante_id: d.nome for d in desejos}
    interpretacoes = await asyncio.gather(*(interpretar(cfg, d) for d in desejos))
    ajustadas = [aplicar_quantidades(d, lista) for d, lista in zip(desejos, interpretacoes)]
    interpretacoes = [lista for lista, _ in ajustadas]
    avisos.extend(a for _, avs in ajustadas for a in avs)  # quantidade ignorada nunca some calada
    for d in desejos:  # lista de compras longa: o que passou do limite vira aviso
        if fora_do_limite := itens_alem_do_limite(d):
            avisos.append(f"{d.nome} pediu mais de {MAX_SLOTS} itens: o Match monta até {MAX_SLOTS} por pessoa; "
                          f"ficou de fora: {', '.join(fora_do_limite)}.")
    slots: list[tuple[Desejo, Intencao]] = [(d, i) for d, lista in zip(desejos, interpretacoes) for i in lista]
    pessoa_de = {i.participante_id: d.participante_id for d, i in slots}

    buscas = []
    for _, intencao in slots:  # em sequência: o rastro fica na ordem em que as tools foram chamadas
        buscas.append(await buscar_detalhado(cliente, intencao, endereco))
    if sem_coordenadas and not any(cands for cands, _ in buscas):
        # sem coordenadas e nada achado: o problema é o endereço, não o pedido ("Não achei X" enganaria)
        avisos[:] = [a for a in avisos if a == MSG_ENDERECO_SEM_ID] + [MSG_ENDERECO_SEM_COORDENADAS]
        resultado["problema"] = "endereco"
        resultado["rastro"] = cliente.rastro_como_dicts()
        return resultado
    julgados = await asyncio.gather(*(
        avaliar(cfg, d, i, cands, det) for (d, i), (cands, det) in zip(slots, buscas)
    ))
    julgados = await _completar_na_mesma_loja(cliente, slots, buscas, list(julgados), endereco)
    candidatos = {i.participante_id: (_so_os_melhores(_sem_irrelevantes(lista)) if _de_varejo(i)
                                      else _sem_irrelevantes(lista))
                  for (_, i), lista in zip(slots, julgados)}
    validos = {slot: _validos(i, candidatos[slot]) for slot, i in ((i.participante_id, i) for _, i in slots)}

    # relevância: o melhor item do slot precisa passar de NOTA_RELEVANTE; senão é "opção aproximada" (e avisa)
    fracos = [(d, i) for d, i in slots
              if validos[i.participante_id] and max(c.nota for c in validos[i.participante_id]) < NOTA_RELEVANTE]
    for desejo, intencao in slots:
        slot = intencao.participante_id
        if not validos[slot]:
            teto = f" até {_reais(intencao.orcamento_max)}" if intencao.orcamento_max else ""
            avisos.append(f"Não achei {_o_que(intencao)}{teto} para {desejo.nome}.")
    if sem_coordenadas and any(not cands for cands, _ in buscas):
        avisos.append("O endereço do iFood veio sem coordenadas (latitude/longitude): a busca pode ter deixado "
                      "lojas de fora. Confirme o local no app do iFood.")
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
    aviso_aproximada: dict[str, tuple[str, str]] = {}  # slot -> (texto provisório, "Não achei X para Y"), bug 24
    for desejo, intencao in fracos:
        slot = intencao.participante_id
        proximo = max(validos[slot], key=lambda c: (c.nota, -c.preco))
        base = f"Não achei {_pediu(desejo, intencao)} para {desejo.nome}"
        texto = f"{base}; a opção mais próxima é {proximo.item_nome} ({proximo.loja_nome}). Quer mudar o pedido?"
        avisos.append(texto)
        aviso_aproximada[slot] = (texto, base)
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

    # A′F4: taxa de entrega de cada loja como veio na busca (estimativa; o valor final é o do getCart)
    taxas = {loja: det["taxa_entrega"] for _, detalhes in buscas for (loja, _), det in detalhes.items()
             if det.get("taxa_entrega") is not None}
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
    detalhes_combo = {chave: det for _, detalhes in buscas for chave, det in detalhes.items()}
    _montar_combos(slots, candidatos, detalhes_combo)
    validos = {slot: _validos(i, candidatos[slot]) for slot, i in ((i.participante_id, i) for _, i in slots)}
    if nada_relevante:  # ninguém tem um item que passe do limiar: sem combinação (a API devolve 409 legível)
        combos = []
        # a pergunta vai uma vez só, no fim; sem combinação, "a opção mais próxima" contradiz o aviso final (bug 14)
        avisos[:] = [a.removesuffix(" Quer mudar o pedido?").split("; a opção mais próxima é")[0].rstrip(".") + "."
                     for a in avisos]
        avisos.append("Nada do que foi pedido está nos cardápios das lojas. Quer mudar o pedido?")
    else:
        combos = otimizar(candidatos, pesos, max_lojas=MAX_LOJAS, top=TOP, orcamentos=orcamentos,
                          pessoa_de=pessoa_de, taxas=taxas)

    if nada_relevante:
        pass  # já avisado acima
    elif not combos:
        avisos.append("Nenhuma combinação coube nas regras (orçamento e restrições). "
                      "Tente aumentar o orçamento ou tirar uma restrição.")
    else:
        melhor = combos[0]
        for slot, (texto, base) in aviso_aproximada.items():  # o aviso cita o item que a combinação de fato usa
            esc = melhor.escolhas.get(slot)
            novo = (f"{base}; a opção mais próxima é {esc.item_nome} ({esc.loja_nome}). Quer mudar o pedido?"
                    if esc else f"{base}. Quer mudar o pedido?")
            avisos[:] = [novo if a == texto else a for a in avisos]
        extras, fora = _avisos_da_melhor(melhor, slots, validos, pessoa_de, nomes,
                                         {i.participante_id for _, i in descartados})
        avisos.extend(extras)
        if fora:  # mediação: mostra o que daria para incluir com mais uma loja (sempre com confirmação humana)
            com_mais = otimizar(candidatos, pesos, max_lojas=MAX_LOJAS + 1, top=1, orcamentos=orcamentos,
                                pessoa_de=pessoa_de, taxas=taxas)
            def mantem(pid: str) -> bool:  # a pessoa ganha o item sem piorar o que já tinha
                return all(com_mais[0].escolhas.get(s) is not None
                           and com_mais[0].escolhas[s].nota >= c.nota - 0.1
                           for s, c in melhor.escolhas.items() if pessoa_de[s] == pid)

            ganhos = [s for s in fora if com_mais and (s in com_mais[0].escolhas or s in com_mais[0].cobertos)
                      and mantem(pessoa_de[s])]
            if ganhos:
                rotulos = {i.participante_id: (_rotulo(i) or "item") for _, i in slots}
                lista = ", ".join(f"{rotulos[s]} de {nomes[pessoa_de[s]]}" for s in ganhos)
                avisos.append(f"Com {MAX_LOJAS + 1} lojas dá para incluir {lista} "
                              "(+1 pedido, +1 taxa de entrega e +1 entrega).")
        n = len(melhor.lojas)
        if n > 1:
            avisos.append(f"{n} lojas = {n} pedidos, {n} taxas de entrega e {n} entregas (podem chegar em "
                          "horários diferentes).")
        if melhor.taxa_conhecida:
            economia = _economia_de_taxa(melhor, validos, taxas)
            if economia:
                avisos.append(economia)
            avisos.append("A taxa de entrega veio da busca do iFood (estimada); o valor final aparece no carrinho, "
                          "antes de você confirmar.")
        else:
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
    avisos[:] = list(dict.fromkeys(avisos))  # slots repetidos ("2 sorvetes") não repetem o mesmo aviso
    resultado["rastro"] = cliente.rastro_como_dicts()
    return resultado
