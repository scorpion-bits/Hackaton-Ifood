"""Checkout do Match (contrato C6): monta 1 carrinho por loja, envia com consentimento e acompanha.

ATENÇÃO: `submitOrder` faz o pedido de verdade (no modo real). Por isso `enviar_pedidos` só roda com
`consentimento=True`, que a API só passa depois da confirmação humana na tela (e 100% pago no modo separado).

Modo real = conta de teste (C16): o pedido não vai ao restaurante, mas um Pix pago NÃO tem reembolso. Por isso, no
modo real, o carrinho só recebe: (1) forma que não cobra online (dinheiro / na entrega / offline); senão (2) o
"Cartão de Teste" da conta de teste do iFood (decisão do Milan, 18/10 01h45: cartão cujo nome diz "teste"/"test";
cartão comum continua proibido); senão (3) nenhuma — o carrinho é montado até o `getCart` (subtotal/taxa/total reais
na tela) sem `setCartPayment`, e só o envio fica bloqueado (`pagamento.codigo = "sem_pagamento_sem_cobranca"`).
Pix nunca, nem se o `agentHints` recomendar. `enviar_pedidos` recusa carrinho sem essa garantia, e o `submitOrder`
real continua exigindo IFOOD_MCP_PERMITIR_ENVIO=true (no cliente) + consentimento na tela.

Itens com grupo de opção obrigatório (bug 17): no modo real, 1 `getItem` por item escolhido; cada grupo com
`minSelections >= 1` recebe as opções mais baratas, no formato `options[{optionId, quantity}]` do schema real.

Este é o ÚNICO lugar que lê os campos das tools de carrinho/pedido (cartId, cartItemId, deliveryFee,
agentHints, ...). Argumentos conferidos com o schema real (docs/mcp-real/tools.json): createCart com `items`,
listPaymentMethods por `merchantId`.
Valores (subtotal, taxa, desconto, total) vêm sempre do `getCart`; nada é recalculado aqui.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ..ifood_mcp.cliente import ErroMCP
from .busca import opcoes_obrigatorias
from .modelos import Candidato, Combinacao

TIPOS_CREDITO = ("CREDIT", "CREDIT_CARD")
MSG_SEM_PAGAMENTO_SEGURO = "A conta de teste não tem forma de pagamento sem cobrança; o pedido para no carrinho."
MSG_SEM_PAGAMENTO_CURTO = "Nenhuma forma sem cobrança na conta de teste: envio bloqueado"
SUFIXO_CARTAO_TESTE = " (conta de teste do iFood, sem cobrança real)"
CODIGO_SEM_PAGAMENTO = "sem_pagamento_sem_cobranca"
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


# ---------- leitura dos campos das tools ----------
# Schemas conferidos com docs/mcp-real/tools.json (18/10). Respostas de carrinho de SUCESSO do MCP real ainda não
# têm amostra (o createCart falhou por falta de `items`): os leitores aceitam o formato do demo e variações próximas.
def _item_do_carrinho(linha: _Linha, opcoes: list[dict] | None = None) -> dict:
    """1 item no formato de `createCart.items[]` do MCP real (obrigatórios: itemId, quantity; `options` só quando o
    item tem grupo obrigatório — sem opção, vai como sempre foi, formato que o real já aceitou)."""
    item = {"itemId": linha.item_id, "quantity": 1}
    if opcoes:
        item["options"] = opcoes
    return item


def _corpo_carrinho(resp: dict) -> dict:
    """O carrinho pode vir na raiz ou dentro de `cart`/`data` (formato de sucesso do real ainda sem amostra)."""
    for chave in ("cart", "data"):
        if isinstance(resp.get(chave), dict) and (resp[chave].get("cartId") or resp[chave].get("items")):
            return resp[chave]
    return resp


def _ler_cart_id(resp: dict) -> str:
    corpo = _corpo_carrinho(resp)
    cart_id = resp.get("cartId") or corpo.get("cartId") or resp.get("id") or corpo.get("id")
    if not cart_id:
        raise ErroMCP("createCart não devolveu cartId.")
    return str(cart_id)


def _ler_cart_item_id(resp: dict, item_id: str | None = None, conhecidos: set[str] | None = None) -> str | None:
    """cartItemId da linha recém-adicionada: campo direto (`cartItemId`, `item.cartItemId`) ou, se a tool devolveu
    o carrinho inteiro, o único/último `items[]` com esse itemId que ainda não conhecíamos. Sem certeza → None
    (o checkout casa pelo itemId depois, no getCart)."""
    direto = resp.get("cartItemId") or (resp.get("item") or {}).get("cartItemId")
    if direto:
        return str(direto)
    if item_id is None:
        return None
    conhecidos = conhecidos or set()
    novos = [str(i["cartItemId"]) for i in _corpo_carrinho(resp).get("items") or []
             if isinstance(i, dict) and i.get("cartItemId") and str(i.get("itemId")) == str(item_id)
             and str(i["cartItemId"]) not in conhecidos]
    return novos[-1] if len(novos) == 1 else None


def _id_entrega(m: dict) -> str | None:
    valor = m.get("id") or m.get("deliveryMethodId")
    return str(valor) if valor not in (None, "") else None


def _ler_metodo_entrega(resp: dict) -> dict:
    """Método recomendado em agentHints (se estiver na lista) ou o primeiro. Nunca inventa id."""
    metodos = [m for m in (resp.get("methods") or resp.get("deliveryMethods") or []) if isinstance(m, dict)]
    metodos = [m for m in metodos if _id_entrega(m)]
    if not metodos:
        raise ErroMCP("A loja não ofereceu nenhum método de entrega para este endereço.")
    recomendado = (resp.get("agentHints") or {}).get("recommendedMethodId")
    for m in metodos:
        if recomendado and _id_entrega(m) == recomendado:
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


_CHAVES_NOME_CARTAO = ("name", "displayName", "title", "label", "description", "alias", "nickname", "card")
_PALAVRAS_TESTE = ("TESTE", "TEST")
_PALAVRAS_CARTAO = ("CREDIT", "CREDITO", "DEBIT", "DEBITO", "CARD", "CARTAO", "CREDIT CARD", "DEBIT CARD")


def _e_cartao(m: dict, contexto: dict | None = None) -> bool:
    textos = _textos_pag(m, _CHAVES_TEXTO_PAG) + _textos_pag(contexto or {}, _CHAVES_TEXTO_PAG)
    return _tem(_norm_pag(textos), _PALAVRAS_CARTAO)


def cartao_de_teste(m: dict, contexto: dict | None = None) -> bool:
    """True só para cartão cujo NOME/descrição diz "teste"/"test" (ex.: "Cartão de Teste 1111"), nunca Pix.

    Decisão humana (Milan, 18/10 01h45): na conta de teste do iFood esse cartão não cobra de verdade. Cartão comum
    ("Visa •••• 9999") continua proibido.
    """
    if _classificar_pagamento(m, contexto)["pix"] or not _e_cartao(m, contexto):
        return False
    return _tem(_norm_pag(_textos_pag(m, _CHAVES_NOME_CARTAO)), _PALAVRAS_TESTE)


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
    senão a recomendada em `agentHints` se for uma delas; senão a 1ª delas. Nenhuma → `SemPagamentoSemCobranca`
    (o cartão de teste é escolhido à parte, em `_escolher_pagamento`).
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


def _escolher_pagamento(resp: dict, pagamento_id: str | None, modo: str | None) -> tuple[dict | None, str | None, dict]:
    """(forma ou None, aviso, marcas {offline, teste}). Prioridade no real: offline/dinheiro → cartão de teste → nada."""
    try:
        m, aviso, offline = _ler_pagamento(resp, pagamento_id, modo)
        return m, aviso, {"offline": offline, "teste": False}
    except SemPagamentoSemCobranca:
        teste = next((m for m, ctx in _lista_pagamentos(resp) if cartao_de_teste(m, ctx)), None)
        if teste is None:
            return None, None, {"offline": False, "teste": False}
        return teste, None, {"offline": False, "teste": True}


def _pagamento_do_carrinho_cobra(resp_carrinho: dict, esperado: dict | None = None) -> bool:
    """getCart: a forma gravada no carrinho pode cobrar de verdade? (Sem forma ou sem como saber → False.)

    Pix → sempre True. Se o carrinho foi montado com o cartão de teste (`esperado.teste`), só esse cartão passa:
    outro cartão (ou forma online) → True.
    """
    corpo = _corpo_carrinho(resp_carrinho)
    pm = (resp_carrinho.get("paymentMethod") or resp_carrinho.get("payment")
          or corpo.get("paymentMethod") or corpo.get("payment"))
    if not isinstance(pm, dict):
        return False
    c = _classificar_pagamento(pm)
    if c["pix"]:
        return True
    if (esperado or {}).get("teste"):
        if _id_pagamento(pm) and _id_pagamento(pm) == esperado.get("id"):
            return False
        if cartao_de_teste(pm):
            return False
        return c["online"] or _e_cartao(pm)
    return c["online"]


def _valor(v: Any) -> float | None:
    """Número de um campo de valor: 12.5, "12,50" ou {"value"/"amount": ...}. Sem número → None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return None
    if isinstance(v, dict):
        for k in ("value", "amount", "finalValue"):
            if k in v:
                return _valor(v[k])
    return None


def _primeiro_valor(fontes: list[dict], chaves: tuple[str, ...]) -> float | None:
    for fonte in fontes:
        for chave in chaves:
            achado = _valor(fonte.get(chave))
            if achado is not None:
                return achado
    return None


def _preco_de_linha(i: dict) -> float | None:
    """Preço unitário de 1 linha do getCart, já com opções se a loja somou (unitPrice / totalPrice÷qtd)."""
    qtd = int(i.get("quantity") or 1)
    unit = _primeiro_valor([i], ("unitPrice", "unitAmount", "price"))
    if unit is None:
        total = _primeiro_valor([i], ("totalPrice", "totalAmount", "total"))
        unit = round(total / qtd, 2) if total is not None else None
    return unit


def _ler_itens_carrinho(resp: dict) -> list[dict]:
    """[{cartItemId, itemId, nome, preco (unitário), quantidade}] do getCart."""
    itens = []
    for i in _corpo_carrinho(resp).get("items") or resp.get("items") or []:
        if not isinstance(i, dict):
            continue
        unit = _preco_de_linha(i)
        itens.append({
            "cartItemId": i.get("cartItemId"),
            "itemId": i.get("itemId"),
            "nome": i.get("name") or i.get("itemName"),
            "preco": float(unit) if unit is not None else None,
            "quantidade": int(i.get("quantity") or 1),
        })
    return itens


def _ler_totais(resp: dict) -> dict:
    """Totais do getCart (bug 20: nunca do `summary` do addItemToCart). Aceita o formato do demo (`subtotal`,
    `deliveryFee`, `discount`, `total` na raiz) e, como suposição a confirmar no real, um `summary`/`totals` com os
    nomes que o addItemToCart real usa (`subtotalAmount`, `totalAmount`)."""
    corpo = _corpo_carrinho(resp)
    fontes = [resp, corpo] + [d for d in (resp.get("summary"), corpo.get("summary"), resp.get("totals"),
                                           corpo.get("totals")) if isinstance(d, dict)]
    return {
        "subtotal": _primeiro_valor(fontes, ("subtotal", "subtotalAmount", "itemsAmount")) or 0.0,
        "taxa": _primeiro_valor(fontes, ("deliveryFee", "deliveryFeeAmount", "deliveryAmount")) or 0.0,
        "desconto": _primeiro_valor(fontes, ("discount", "discountAmount", "discountsAmount")) or 0.0,
        "total": _primeiro_valor(fontes, ("total", "totalAmount")) or 0.0,
    }


def _ler_eta(resp_carrinho: dict, metodo_entrega: dict) -> int | None:
    """estimatedTime (demo) ou estimatedMinutes {min, max} (formato do MCP real na busca): pega o máximo."""
    metodo = resp_carrinho.get("deliveryMethod") or metodo_entrega or {}
    eta = metodo.get("estimatedTime")
    if eta is None:
        eta = metodo.get("estimatedMinutes")
    if isinstance(eta, dict):
        eta = eta.get("max") or eta.get("min")
    try:
        return int(eta) if eta is not None and not isinstance(eta, bool) else None
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
async def _opcoes_dos_itens(cliente, loja_id: str, linhas: list[_Linha], geo: dict | None,
                            avisos: list[str]) -> dict[str, list[dict]]:
    """Modo real (bug 17): 1 `getItem` por item distinto; item com grupo obrigatório → opções mais baratas.

    Demo ou sem coordenadas: não chama nada (o roteiro não muda). getItem com erro → segue sem opções (o
    addItemToCart dirá se faltar).
    """
    coords = {k: (geo or {}).get(k) for k in ("latitude", "longitude") if (geo or {}).get(k) is not None}
    if getattr(cliente, "modo", None) == "demo" or len(coords) < 2:  # getItem real exige userLocation
        return {}
    saida: dict[str, list[dict]] = {}
    for linha in linhas:
        if linha.item_id in saida:
            continue
        saida[linha.item_id] = []
        try:
            detalhe = await cliente.chamar("getItem", merchantId=loja_id, itemId=linha.item_id, **coords)
        except ErroMCP:
            continue
        obrig = opcoes_obrigatorias(detalhe if isinstance(detalhe, dict) else {})
        if not obrig or not obrig["opcoes"]:
            continue
        saida[linha.item_id] = obrig["opcoes"]
        escolhidas = ", ".join(obrig["nomes"])
        if obrig["extra"] is None:
            avisos.append(f"{linha.item_nome} exige complemento ({escolhidas}); o valor vem do carrinho do iFood.")
        elif obrig["extra"] > 0:
            avisos.append(f"{linha.item_nome} exige complemento: escolhemos o mais barato ({escolhidas}, "
                          f"+ R$ {obrig['extra']:.2f}); o valor de cada pessoa vem do carrinho do iFood.")
        else:
            avisos.append(f"{linha.item_nome} exige complemento: escolhemos {escolhidas} (sem custo extra).")
        if not obrig["completo"]:
            avisos.append(f"{linha.item_nome}: um grupo obrigatório tem menos opções que o mínimo pedido.")
    return saida


def _info_pagamento(metodo: dict | None, marcas: dict) -> dict:
    """Campo `pagamento` do carrinho (C16; o front lê `nome` e `offline`)."""
    if metodo is None:
        return {"id": None, "nome": MSG_SEM_PAGAMENTO_CURTO, "tipo": None, "offline": False, "teste": False,
                "bloqueado": True, "codigo": CODIGO_SEM_PAGAMENTO}
    nome = _nome_pagamento(metodo)
    if marcas.get("teste"):
        nome += SUFIXO_CARTAO_TESTE
    return {"id": _id_pagamento(metodo), "nome": nome, "tipo": _tipo_pagamento(metodo),
            "offline": bool(marcas.get("offline")), "teste": bool(marcas.get("teste"))}


async def _montar_loja(cliente, loja_id: str, linhas: list[_Linha], endereco_id: str,
                       pagamento_id: str | None, geo: dict | None = None) -> dict:
    avisos: list[str] = []
    opcoes = await _opcoes_dos_itens(cliente, loja_id, linhas, geo, avisos)
    # MCP real: sem orderId, o createCart exige addressId + merchantId + items (MISSING_REQUIRED_FIELDS).
    # Vai o 1º item já na criação; os outros entram por addItemToCart.
    primeira, resto = linhas[0], linhas[1:]
    carrinho = await cliente.chamar("createCart", merchantId=loja_id, addressId=endereco_id,
                                    items=[_item_do_carrinho(primeira, opcoes.get(primeira.item_id))])
    cart_id = _ler_cart_id(carrinho)

    # 1 linha por slot (mesmo item pedido por 2 pessoas = 2 linhas), para saber de quem é cada uma.
    dono_por_linha: dict[str, _Linha] = {}
    sem_id: list[_Linha] = []

    def anotar_dono(linha: _Linha, cart_item_id: str | None) -> None:
        if cart_item_id:
            dono_por_linha[cart_item_id] = linha
        else:
            sem_id.append(linha)

    anotar_dono(primeira, _ler_cart_item_id(carrinho, primeira.item_id, set()))
    for linha in resto:
        # MCP real: sem `options` o addItemToCart quebra no servidor ("parameter options ... is null"); vazio funciona.
        resp = await cliente.chamar("addItemToCart", cartId=cart_id, itemId=linha.item_id, quantity=1,
                                    options=opcoes.get(linha.item_id) or [])
        anotar_dono(linha, _ler_cart_item_id(resp, linha.item_id, set(dono_por_linha)))

    entregas = await cliente.chamar("getCartDeliveryMethods", cartId=cart_id)
    metodo_entrega = _ler_metodo_entrega(entregas)
    await cliente.chamar("setCartDelivery", cartId=cart_id, deliveryMethodId=_id_entrega(metodo_entrega))

    # MCP real: listPaymentMethods só aceita merchantId (obrigatório); não recebe cartId.
    pagamentos = await cliente.chamar("listPaymentMethods", merchantId=loja_id)
    # modo real: nunca Pix/online; offline → cartão de teste → nenhuma (sem setCartPayment; envio bloqueado)
    metodo_pag, aviso_pag, marcas = _escolher_pagamento(pagamentos, pagamento_id, getattr(cliente, "modo", None))
    if aviso_pag:
        avisos.append(aviso_pag)
    if metodo_pag is not None:
        await cliente.chamar("setCartPayment", cartId=cart_id, paymentMethodId=_id_pagamento(metodo_pag))
        if marcas["teste"]:
            avisos.append(f"Pagamento: {_nome_pagamento(metodo_pag)}{SUFIXO_CARTAO_TESTE}.")
    else:
        avisos.append(f"{MSG_SEM_PAGAMENTO_SEGURO} O carrinho está montado; só o envio fica bloqueado.")

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
        "entrega": {"id": _id_entrega(metodo_entrega),
                    "nome": metodo_entrega.get("name") or metodo_entrega.get("deliveryMethodMode")},
        "pagamento": _info_pagamento(metodo_pag, marcas),
        "avisos": avisos,
        "demonstracao": bool(final.get("demonstracao")),
    }


# Erros do iFood que costumam passar numa 2ª tentativa (bug 21/22: `getCart` → INTERNAL "upstream service").
CODIGOS_TRANSITORIOS = ("INTERNAL", "SERVICE_UNAVAILABLE")
ESPERA_NOVA_TENTATIVA_S = 0.5  # 1 nova tentativa, sem atrasar mais que ~1 s


def _transitorio(e: ErroMCP) -> bool:
    codigo = str(getattr(e, "codigo", None) or "").upper()
    texto = str(e).upper()
    return codigo in CODIGOS_TRANSITORIOS or any(f"(CÓDIGO {c}" in texto for c in CODIGOS_TRANSITORIOS)


class _ComNovaTentativa:
    """Embrulha o cliente: `createCart`/`getCart` com erro transitório (INTERNAL) ganham 1 nova tentativa."""

    TOOLS = ("createCart", "getCart")

    def __init__(self, cliente):
        self._cliente = cliente

    def __getattr__(self, nome: str):
        return getattr(self._cliente, nome)

    async def chamar(self, tool: str, **args):
        try:
            return await self._cliente.chamar(tool, **args)
        except ErroMCP as e:
            if tool not in self.TOOLS or not _transitorio(e):
                raise
        await asyncio.sleep(ESPERA_NOVA_TENTATIVA_S)
        return await self._cliente.chamar(tool, **args)


def _erro_da_loja(loja_id: str, nome: str, e: ErroMCP) -> ErroCheckout:
    if getattr(e, "codigo", None) == "ITEM-001":
        erro = ErroCheckout(loja_id, f"Não deu para montar o carrinho de {nome}: um item exige escolher "
                                     f"complementos que o iFood não informou ({e}). Troque o item com 'Ajustar com o IBits'.",
                            codigo="complemento_obrigatorio")
    else:
        erro = ErroCheckout(loja_id, f"Não deu para montar o carrinho de {nome}: {e}")
    erro.__cause__ = e
    return erro


def _falha(loja_id: str, linhas: list[_Linha], erro: ErroCheckout) -> dict:
    """Uma loja que saiu do pedido (bug 21): quem ficou sem quais itens e o que o iFood respondeu."""
    causa = erro.__cause__
    return {
        "loja_id": loja_id,
        "loja_nome": linhas[0].loja_nome,
        "codigo_ifood": getattr(causa, "codigo", None),
        "erro": erro.mensagem,
        "participantes": list(dict.fromkeys(l.participante_id for l in linhas)),
        "itens": [{"participante_id": l.participante_id, "slot": l.slot, "item_id": l.item_id,
                   "nome": l.item_nome} for l in linhas],
        "excecao": erro,
    }


async def montar_carrinhos(cliente, combinacao: Combinacao | dict, endereco_id: str,
                           pagamento_id: str | None = None, geo: dict | None = None,
                           falhas: list[dict] | None = None) -> list[dict]:
    """1 carrinho por loja da combinação, na sequência obrigatória do MCP. Falha → `ErroCheckout`.

    `geo` ({latitude, longitude} do endereço; ou `combinacao["geo"]`): o getItem real exige `userLocation` (bug 17).
    Sem forma de pagamento aceitável o carrinho volta montado, com `pagamento.codigo = "sem_pagamento_sem_cobranca"`.

    `falhas` (lista; ou `combinacao["falhas"]`, como o `geo`) liga o modo "pula a loja que falhou" (bug 21): a loja
    com erro sai, as outras seguem, e cada loja que saiu é anotada nessa lista (ver `_falha`). Se TODAS falharem,
    levanta `ErroCheckout` do mesmo jeito. Sem a lista (padrão), a 1ª loja com erro derruba tudo, como sempre.
    `createCart`/`getCart` com erro transitório (INTERNAL) ganham 1 nova tentativa antes de desistir da loja.
    """
    if isinstance(combinacao, dict):  # a rota manda coordenadas e a lista de falhas dentro da combinação
        if geo is None:
            geo = _campo(combinacao, "geo")
        if falhas is None and isinstance(combinacao.get("falhas"), list):
            falhas = combinacao["falhas"]
    grupos = _agrupar_por_loja(_linhas_da_combinacao(combinacao))
    if not grupos:
        raise ValueError("A combinação não tem nenhum item.")
    cli = _ComNovaTentativa(cliente)
    carrinhos = []
    erros: list[ErroCheckout] = []
    for loja_id, linhas in grupos.items():
        try:
            carrinhos.append(await _montar_loja(cli, loja_id, linhas, endereco_id, pagamento_id, geo))
        except ErroMCP as e:
            erro = _erro_da_loja(loja_id, linhas[0].loja_nome, e)
            if falhas is None:
                raise erro from e
            erros.append(erro)
            falhas.append(_falha(loja_id, linhas, erro))
    if not carrinhos:  # todas as lojas falharam: o erro de sempre (com todas as lojas, se forem várias)
        primeiro = erros[0]
        if len(erros) == 1:
            raise primeiro
        juntos = ErroCheckout(primeiro.loja_id, " ".join(e.mensagem for e in erros), codigo=primeiro.codigo)
        raise juntos from primeiro.__cause__
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
        pagamento = carrinho.get("pagamento") or {}
        if real and pagamento.get("codigo") == CODIGO_SEM_PAGAMENTO:
            resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"), "status": "falhou",
                              "erro": MSG_SEM_PAGAMENTO_SEGURO, "codigo": CODIGO_SEM_PAGAMENTO})
            break
        # real: só forma offline OU o cartão de teste da conta de teste (marcado na montagem); cartão comum nunca
        if real and pagamento.get("offline") is not True and pagamento.get("teste") is not True:
            resultado.append({"loja_id": loja_id, "loja_nome": carrinho.get("loja_nome"),
                              "status": "falhou", "erro": MSG_ENVIO_SEM_GARANTIA})
            break
        try:
            bruto = await cliente.chamar("getCart", cartId=cart_id)
            if real and _pagamento_do_carrinho_cobra(bruto, pagamento):  # trocaram a forma por fora: não envia
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
