"""Checkout do Match (contrato C6): monta 1 carrinho por loja, envia com consentimento e acompanha.

ATENÇÃO: `submitOrder` faz o pedido de verdade (no modo real). Por isso `enviar_pedidos` só roda com
`consentimento=True`, que a API só passa depois da confirmação humana na tela (e 100% pago no modo separado).

Modo real = conta de teste (C16): o pedido não vai ao restaurante, mas um Pix pago NÃO tem reembolso. Por isso, no
modo real, o carrinho só recebe forma de pagamento que não cobra online (dinheiro / pagamento na entrega / offline);
Pix e cartão online nunca são escolhidos, nem se o `agentHints` recomendar. Sem forma assim, a montagem para antes do
`setCartPayment` com `ErroCheckout` legível, e `enviar_pedidos` recusa carrinho sem essa garantia.

Este é o ÚNICO lugar que lê os campos das tools de carrinho/pedido (cartId, cartItemId, deliveryFee,
agentHints, ...). Se o MCP real usar outro formato, a etapa 03 ajusta só as funções `_ler_*` daqui.
Valores (subtotal, taxa, desconto, total) vêm sempre do `getCart`; nada é recalculado aqui.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ..ifood_mcp.cliente import ErroMCP
from .modelos import Candidato, Combinacao

TIPOS_CREDITO = ("CREDIT", "CREDIT_CARD")
MSG_SEM_PAGAMENTO_SEGURO = "A conta de teste não tem forma de pagamento sem cobrança; o pedido para no carrinho."
MSG_ENVIO_SEM_GARANTIA = ("Pedido não enviado: a forma de pagamento deste carrinho pode cobrar online "
                          "(só enviamos com pagamento na entrega na conta de teste).")


class ErroCheckout(Exception):
    """Falha ao montar o carrinho de uma loja. `mensagem` é legível para a pessoa.

    `codigo` (opcional) identifica casos que a tela pode tratar à parte, ex.: "sem_pagamento_sem_cobranca".
    """

    def __init__(self, loja_id: str, mensagem: str, codigo: str | None = None):
        super().__init__(mensagem)
        self.loja_id = loja_id
        self.mensagem = mensagem
        self.codigo = codigo


class SemPagamentoSemCobranca(ErroMCP):
    """Modo real: a lista do `listPaymentMethods` não tem nenhuma forma que não cobre online."""

    def __init__(self) -> None:
        super().__init__(MSG_SEM_PAGAMENTO_SEGURO)


@dataclass
class _Linha:
    """Um item pedido por um slot (pessoa ou "pessoa#k")."""

    slot: str
    participante_id: str
    loja_id: str
    loja_nome: str
    item_id: str
    item_nome: str
    preco: float


# ---------- utilidades ----------
def _centavos(valor: Any) -> int:
    return int((Decimal(str(valor or 0)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _pessoa_do_slot(slot: str) -> str:
    """"ana#2" → "ana" (C4b: slots extras de uma pessoa levam "#k")."""
    return slot.split("#", 1)[0]


def _campo(obj: Any, nome: str, padrao: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def _linhas_da_combinacao(combinacao: Combinacao | dict) -> list[_Linha]:
    """Achata `escolhas` (Candidato, dict, ou lista deles por slot) em linhas com o dono de cada uma."""
    escolhas = _campo(combinacao, "escolhas") or {}
    linhas: list[_Linha] = []
    for slot, valor in escolhas.items():
        candidatos = list(valor) if isinstance(valor, (list, tuple)) else [valor]
        lista = isinstance(valor, (list, tuple))
        for c in candidatos:
            dono = str((_campo(c, "participante_id") or slot) if lista else slot)
            linhas.append(_Linha(
                slot=dono,
                participante_id=_pessoa_do_slot(dono),
                loja_id=str(_campo(c, "loja_id")),
                loja_nome=str(_campo(c, "loja_nome") or _campo(c, "loja_id")),
                item_id=str(_campo(c, "item_id")),
                item_nome=str(_campo(c, "item_nome") or _campo(c, "item_id")),
                preco=float(_campo(c, "preco") or 0),
            ))
    return linhas


def _agrupar_por_loja(linhas: list[_Linha]) -> dict[str, list[_Linha]]:
    grupos: dict[str, list[_Linha]] = {}
    for linha in linhas:
        grupos.setdefault(linha.loja_id, []).append(linha)
    return grupos


# ---------- leitura dos campos das tools (ajustar aqui na etapa 03) ----------
def _ler_cart_id(resp: dict) -> str:
    cart_id = resp.get("cartId") or resp.get("id")
    if not cart_id:
        raise ErroMCP("createCart não devolveu cartId.")
    return str(cart_id)


def _ler_cart_item_id(resp: dict) -> str | None:
    return resp.get("cartItemId") or (resp.get("item") or {}).get("cartItemId")


def _ler_metodo_entrega(resp: dict) -> dict:
    """Método recomendado em agentHints (se estiver na lista) ou o primeiro. Nunca inventa id."""
    metodos = resp.get("methods") or resp.get("deliveryMethods") or []
    if not metodos:
        raise ErroMCP("A loja não ofereceu nenhum método de entrega para este endereço.")
    recomendado = (resp.get("agentHints") or {}).get("recommendedMethodId")
    for m in metodos:
        if recomendado and m.get("id") == recomendado:
            return m
    return metodos[0]


# --- formas de pagamento (C16) ---
# Campos de texto lidos de cada forma (e de dicts aninhados, ex.: `type: {"name": "OFFLINE"}`).
_CHAVES_TEXTO_PAG = ("type", "paymentType", "method", "brand", "name", "displayName", "title", "label",
                     "description", "code", "kind", "category", "group", "mode", "channel")
# Campos que dizem o TIPO (só neles "ONLINE" conta: um nome como "não cobra online" não reprova a forma).
_CHAVES_TIPO_PAG = ("type", "paymentType", "method", "kind", "mode", "channel", "category", "group")
_CHAVES_ANINHADAS = ("name", "code", "type", "value", "description")
_BOOL_OFFLINE = ("offline", "isOffline", "onDelivery", "isOnDelivery", "payOnDelivery", "paymentOnDelivery")
_BOOL_ONLINE = ("online", "isOnline")
# Palavras/expressões (texto normalizado: maiúsculas, sem acento, separadores viram espaço).
_PALAVRAS_OFFLINE = ("CASH", "DINHEIRO", "OFFLINE", "ON DELIVERY", "ONDELIVERY", "PAYONDELIVERY", "NA ENTREGA",
                     "NO RECEBIMENTO", "MAQUININHA")
_PALAVRAS_ONLINE = ("ONLINE", "PELO APP", "NO APP", "IN APP", "INAPP")
_PALAVRAS_DINHEIRO = ("CASH", "DINHEIRO")
# Onde a lista pode estar; um elemento sem id que tem lista dentro é um GRUPO (ex.: "Pague na entrega").
_CHAVES_LISTA_PAG = ("methods", "paymentMethods", "availablePaymentMethods", "payments", "options", "items",
                     "results", "groups", "sections", "categories", "paymentGroups")


def _norm_pag(textos: list[str]) -> str:
    """" PIX ON DELIVERY " — maiúsculas, sem acento, só letras/dígitos, com espaço nas pontas (busca por frase)."""
    juntos = " ".join(textos)
    sem_acento = unicodedata.normalize("NFKD", juntos).encode("ascii", "ignore").decode("ascii")
    return " " + " ".join(re.sub(r"[^A-Z0-9]+", " ", sem_acento.upper()).split()) + " "


def _textos_pag(obj: dict, chaves: tuple[str, ...]) -> list[str]:
    saida: list[str] = []
    for chave in chaves:
        valor = obj.get(chave)
        if isinstance(valor, str):
            saida.append(valor)
        elif isinstance(valor, dict):
            saida.extend(str(valor[k]) for k in _CHAVES_ANINHADAS if isinstance(valor.get(k), str))
    return saida


def _tem(norm: str, palavras: tuple[str, ...]) -> bool:
    return any(f" {p} " in norm for p in palavras)


def _id_pagamento(m: dict) -> str | None:
    valor = m.get("id") or m.get("paymentMethodId") or m.get("methodId")
    return str(valor) if valor not in (None, "") else None


def _props_grupo(grupo: dict) -> dict:
    """Campos simples do grupo (texto e booleanos), herdados pelas formas de dentro dele."""
    return {k: v for k, v in grupo.items() if isinstance(v, (str, bool)) and k not in ("id",)}


def _lista_pagamentos(resp: Any, contexto: dict | None = None, profundidade: int = 0) -> list[tuple[dict, dict]]:
    """[(forma, contexto do grupo)] em `methods`/`paymentMethods`/grupos/`data`/`{offline: [...]}`."""
    if profundidade > 3 or not isinstance(resp, dict):
        return []
    contexto = contexto or {}
    saida: list[tuple[dict, dict]] = []
    for chave in _CHAVES_LISTA_PAG:
        lista = resp.get(chave)
        if not isinstance(lista, list):
            continue
        for m in lista:
            if not isinstance(m, dict):
                continue
            if _id_pagamento(m):
                saida.append((m, contexto))
            else:  # grupo: as formas de dentro herdam o rótulo ("Pague na entrega", type OFFLINE...)
                saida.extend(_lista_pagamentos(m, {**contexto, **_props_grupo(m)}, profundidade + 1))
        if saida:
            return saida
    for chave, bandeira in (("offline", {"offline": True}), ("onDelivery", {"onDelivery": True}),
                            ("online", {"online": True})):
        lista = resp.get(chave)
        if isinstance(lista, list):
            saida.extend((m, {**contexto, **bandeira}) for m in lista if isinstance(m, dict) and _id_pagamento(m))
    if not saida and isinstance(resp.get("data"), dict):
        return _lista_pagamentos(resp["data"], contexto, profundidade + 1)
    return saida


def _classificar_pagamento(m: dict, contexto: dict | None = None) -> dict:
    """{pix, online, offline, dinheiro} de uma forma de pagamento (e do grupo onde ela veio)."""
    contexto = contexto or {}
    tudo = _norm_pag(_textos_pag(m, _CHAVES_TEXTO_PAG) + _textos_pag(contexto, _CHAVES_TEXTO_PAG))
    tipo = _norm_pag(_textos_pag(m, _CHAVES_TIPO_PAG) + _textos_pag(contexto, _CHAVES_TEXTO_PAG))
    pix = "PIX" in tudo or "PIX" in str(_id_pagamento(m) or "").upper()
    online = (_tem(tipo, _PALAVRAS_ONLINE)
              or any(d.get(k) is True for d in (m, contexto) for k in _BOOL_ONLINE)
              or any(d.get(k) is False for d in (m, contexto) for k in _BOOL_OFFLINE))
    offline = _tem(tudo, _PALAVRAS_OFFLINE) or any(d.get(k) is True for d in (m, contexto) for k in _BOOL_OFFLINE)
    return {"pix": pix, "online": online, "offline": offline, "dinheiro": _tem(tudo, _PALAVRAS_DINHEIRO)}


def sem_cobranca_online(m: dict, contexto: dict | None = None) -> bool:
    """True só se a forma, com certeza razoável, NÃO cobra online: nunca Pix, nunca online, e marcada como offline."""
    c = _classificar_pagamento(m, contexto)
    return c["offline"] and not c["pix"] and not c["online"]


def _nome_pagamento(m: dict) -> str:
    for chave in ("name", "displayName", "title", "label", "description"):
        if isinstance(m.get(chave), str) and m[chave].strip():
            return m[chave]
    return _id_pagamento(m) or "?"


def _tipo_pagamento(m: dict) -> str | None:
    for chave in ("type", "method", "paymentType", "kind"):
        textos = _textos_pag(m, (chave,))
        if textos:
            return textos[0]
    return None


def _ler_pagamento(resp: dict, pagamento_id: str | None, modo: str | None = "demo") -> tuple[dict, str | None, bool]:
    """(forma escolhida, aviso, offline).

    Demo: `pagamento_id` se existir na lista; senão o 1º crédito; senão o 1º (comportamento de sempre).
    Real (qualquer modo ≠ "demo"): só forma sem cobrança online — `pagamento_id` se for uma delas; senão dinheiro;
    senão a recomendada em `agentHints` se for uma delas; senão a 1ª delas. Nenhuma → `SemPagamentoSemCobranca`.
    """
    lista = _lista_pagamentos(resp)
    if not lista:
        raise ErroMCP("Nenhuma forma de pagamento disponível para este carrinho.")

    if modo == "demo":
        metodos = [m for m, _ in lista]
        contexto = {id(m): ctx for m, ctx in lista}
        offline = lambda m: sem_cobranca_online(m, contexto[id(m)])  # noqa: E731
        if pagamento_id:
            for m in metodos:
                if _id_pagamento(m) == pagamento_id:
                    return m, None, offline(m)
        for m in metodos:
            if str(m.get("type", "")).upper() in TIPOS_CREDITO:
                aviso = (f"Forma de pagamento '{pagamento_id}' indisponível; usando {_nome_pagamento(m)}."
                         if pagamento_id else None)
                return m, aviso, offline(m)
        m = metodos[0]
        return m, f"Sem cartão de crédito disponível; usando {_nome_pagamento(m)}.", offline(m)

    seguros = [(m, ctx) for m, ctx in lista if sem_cobranca_online(m, ctx)]
    if not seguros:
        raise SemPagamentoSemCobranca()
    recomendado = (resp.get("agentHints") or {}).get("recommendedMethodId")
    escolhido = (next((m for m, _ in seguros if pagamento_id and _id_pagamento(m) == pagamento_id), None)
                 or next((m for m, ctx in seguros if _classificar_pagamento(m, ctx)["dinheiro"]), None)
                 or next((m for m, _ in seguros if recomendado and _id_pagamento(m) == str(recomendado)), None)
                 or seguros[0][0])
    aviso = None
    if pagamento_id and _id_pagamento(escolhido) != pagamento_id:
        aviso = (f"Forma de pagamento '{pagamento_id}' indisponível ou cobra online; "
                 f"usando {_nome_pagamento(escolhido)} (sem cobrança online).")
    return escolhido, aviso, True


def _pagamento_do_carrinho_cobra(resp_carrinho: dict) -> bool:
    """getCart: a forma gravada no carrinho é Pix ou online? (Sem forma ou sem como saber → False.)"""
    pm = resp_carrinho.get("paymentMethod") or resp_carrinho.get("payment")
    if not isinstance(pm, dict):
        return False
    c = _classificar_pagamento(pm)
    return c["pix"] or c["online"]


def _ler_itens_carrinho(resp: dict) -> list[dict]:
    """[{cartItemId, itemId, nome, preco (unitário), quantidade}] do getCart."""
    itens = []
    for i in resp.get("items") or []:
        qtd = int(i.get("quantity") or 1)
        unit = i.get("unitPrice")
        if unit is None and i.get("totalPrice") is not None:
            unit = round(float(i["totalPrice"]) / qtd, 2)
        itens.append({
            "cartItemId": i.get("cartItemId"),
            "itemId": i.get("itemId"),
            "nome": i.get("name"),
            "preco": float(unit) if unit is not None else None,
            "quantidade": qtd,
        })
    return itens


def _ler_totais(resp: dict) -> dict:
    return {
        "subtotal": float(resp.get("subtotal") or 0),
        "taxa": float(resp.get("deliveryFee") or 0),
        "desconto": float(resp.get("discount") or 0),
        "total": float(resp.get("total") or 0),
    }


def _ler_eta(resp_carrinho: dict, metodo_entrega: dict) -> int | None:
    metodo = resp_carrinho.get("deliveryMethod") or metodo_entrega or {}
    eta = metodo.get("estimatedTime")
    try:
        return int(eta) if eta is not None else None
    except (TypeError, ValueError):
        return None


def _ler_order_id(resp: dict) -> str:
    order_id = resp.get("orderId") or resp.get("id")
    if not order_id:
        raise ErroMCP("submitOrder não devolveu orderId.")
    return str(order_id)


def _ler_rastreio(resp: dict) -> dict:
    status = resp.get("status") or {}
    if isinstance(status, str):
        status = {"code": status, "description": ""}
    dicas = resp.get("agentHints") or {}
    retry = dicas.get("retryMessage")
    segundos = re.search(r"(\d+)\s*(?:s\b|sec|second|segundo)", retry or "", re.IGNORECASE)
    return {
        "status_code": status.get("code"),
        "status_descricao": status.get("description"),
        "historico": [{"codigo": h.get("code"), "descricao": h.get("description")}
                      for h in resp.get("statusHistory") or []],
        "encerrado": dicas.get("pollingStop") is True,
        "proxima_consulta": retry,
        "proxima_consulta_s": int(segundos.group(1)) if segundos else None,
    }


# ---------- montar ----------
async def _montar_loja(cliente, loja_id: str, linhas: list[_Linha], endereco_id: str,
                       pagamento_id: str | None) -> dict:
    avisos: list[str] = []
    carrinho = await cliente.chamar("createCart", merchantId=loja_id, addressId=endereco_id)
    cart_id = _ler_cart_id(carrinho)

    # 1 linha por slot (mesmo item pedido por 2 pessoas = 2 linhas), para saber de quem é cada uma.
    dono_por_linha: dict[str, _Linha] = {}
    sem_id: list[_Linha] = []
    for linha in linhas:
        resp = await cliente.chamar("addItemToCart", cartId=cart_id, itemId=linha.item_id, quantity=1)
        cart_item_id = _ler_cart_item_id(resp)
        if cart_item_id:
            dono_por_linha[cart_item_id] = linha
        else:
            sem_id.append(linha)

    entregas = await cliente.chamar("getCartDeliveryMethods", cartId=cart_id)
    metodo_entrega = _ler_metodo_entrega(entregas)
    await cliente.chamar("setCartDelivery", cartId=cart_id, deliveryMethodId=metodo_entrega["id"])

    pagamentos = await cliente.chamar("listPaymentMethods", cartId=cart_id)
    # modo real: nunca Pix/online; sem forma segura levanta aqui, ANTES do setCartPayment
    metodo_pag, aviso_pag, pag_offline = _ler_pagamento(pagamentos, pagamento_id, getattr(cliente, "modo", None))
    if aviso_pag:
        avisos.append(aviso_pag)
    await cliente.chamar("setCartPayment", cartId=cart_id, paymentMethodId=_id_pagamento(metodo_pag))

    final = await cliente.chamar("getCart", cartId=cart_id)
    avisos.extend(str(w) for w in final.get("warnings") or [])

    itens = []
    for item in _ler_itens_carrinho(final):
        dono = dono_por_linha.pop(item["cartItemId"], None) if item["cartItemId"] else None
        if dono is None:  # sem cartItemId: casa pelo itemId, na ordem em que foi adicionado
            dono = next((l for l in sem_id if l.item_id == item["itemId"]), None)
            if dono is not None:
                sem_id.remove(dono)
        if dono is not None and item["preco"] is not None and _centavos(item["preco"]) != _centavos(dono.preco):
            avisos.append(f"Preço de {item['nome']} mudou: R$ {dono.preco:.2f} → R$ {item['preco']:.2f}.")
        itens.append({
            "item_id": item["itemId"],
            "nome": item["nome"],
            "preco": item["preco"],
            "quantidade": item["quantidade"],
            "participante_id": dono.participante_id if dono else None,
            "slot": dono.slot if dono else None,
            "cart_item_id": item["cartItemId"],
        })
    faltando = list(dono_por_linha.values()) + sem_id
    if faltando:
        raise ErroMCP("Itens sumiram do carrinho: " + ", ".join(l.item_nome for l in faltando) + ".")

    return {
        "loja_id": loja_id,
        "loja_nome": final.get("merchantName") or linhas[0].loja_nome,
        "cart_id": cart_id,
        "itens": itens,
        **_ler_totais(final),
        "eta_min": _ler_eta(final, metodo_entrega),
        "entrega": {"id": metodo_entrega.get("id"), "nome": metodo_entrega.get("name")},
        "pagamento": {"id": _id_pagamento(metodo_pag), "nome": _nome_pagamento(metodo_pag),
                      "tipo": _tipo_pagamento(metodo_pag), "offline": pag_offline},
        "avisos": avisos,
        "demonstracao": bool(final.get("demonstracao")),
    }


async def montar_carrinhos(cliente, combinacao: Combinacao | dict, endereco_id: str,
                           pagamento_id: str | None = None) -> list[dict]:
    """1 carrinho por loja da combinação, na sequência obrigatória do MCP. Falha → `ErroCheckout`."""
    grupos = _agrupar_por_loja(_linhas_da_combinacao(combinacao))
    if not grupos:
        raise ValueError("A combinação não tem nenhum item.")
    carrinhos = []
    for loja_id, linhas in grupos.items():
        try:
            carrinhos.append(await _montar_loja(cliente, loja_id, linhas, endereco_id, pagamento_id))
        except SemPagamentoSemCobranca as e:
            nome = linhas[0].loja_nome
            raise ErroCheckout(loja_id, f"{e} (Loja: {nome}.)", codigo="sem_pagamento_sem_cobranca") from e
        except ErroMCP as e:
            nome = linhas[0].loja_nome
            raise ErroCheckout(loja_id, f"Não deu para montar o carrinho de {nome}: {e}") from e
    return carrinhos


# ---------- enviar ----------
async def enviar_pedidos(cliente, carrinhos: list[dict], consentimento: bool,
                         ja_enviados: set[str] | None = None) -> list[dict]:
    """Envia os carrinhos em sequência. Para no 1º problema e devolve o que já foi enviado + o problema.

    `ja_enviados`: cart_ids já enviados (são pulados; os novos envios são acrescentados ao set).
    """
    if consentimento is not True:
        raise ValueError("Sem confirmação humana, nenhum pedido é enviado.")
    enviados = ja_enviados if ja_enviados is not None else set()
    real = getattr(cliente, "modo", None) != "demo"
    resultado: list[dict] = []
    for carrinho in carrinhos:
        cart_id = carrinho["cart_id"]
        loja_id = carrinho["loja_id"]
        if cart_id in enviados:
            continue
        if real and (carrinho.get("pagamento") or {}).get("offline") is not True:
            resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"),
                              "status": "falhou", "erro": MSG_ENVIO_SEM_GARANTIA})
            break
        try:
            bruto = await cliente.chamar("getCart", cartId=cart_id)
            if real and _pagamento_do_carrinho_cobra(bruto):  # alguém trocou a forma por fora: não envia
                resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"),
                                  "status": "falhou", "erro": MSG_ENVIO_SEM_GARANTIA})
                break
            atual = _ler_totais(bruto)
            if _centavos(atual["total"]) != _centavos(carrinho["total"]):
                resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"),
                                  "status": "total_mudou", "total_antes": carrinho["total"],
                                  "total_agora": atual["total"]})
                break
            pedido = await cliente.chamar("submitOrder", cartId=cart_id, userConsent=True)
            order_id = _ler_order_id(pedido)
        except ErroMCP as e:
            resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"),
                              "status": "falhou", "erro": str(e)})
            break
        enviados.add(cart_id)
        resultado.append({
            "loja_id": loja_id,
            "loja_nome": carrinho.get("loja_nome"),
            "cart_id": cart_id,
            "order_id": order_id,
            "status": "enviado",
            "total": float(pedido.get("total") or atual["total"]),
            "demonstracao": bool(pedido.get("demonstracao")),
        })
    return resultado


# ---------- acompanhar ----------
async def acompanhar(cliente, order_id: str) -> dict:
    """Status do pedido via `trackOrder`. Pare de consultar quando `encerrado` for True."""
    resp = await cliente.chamar("trackOrder", orderId=order_id)
    return {"order_id": order_id, **_ler_rastreio(resp), "demonstracao": bool(resp.get("demonstracao"))}
