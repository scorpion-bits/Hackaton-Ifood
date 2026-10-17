"""Servidor MCP de DEMONSTRAÇÃO que imita o MCP do consumidor do iFood.

- Nomes das tools e dos campos seguem a doc oficial (docs/mcp-ifood.md e llms-full.txt do Portal).
  Onde a doc não mostra o formato da resposta (ex.: itens do searchOffers), o formato aqui é nosso e está marcado
  como "não verificado" no comentário da tool; a etapa 03 ajusta o mapeamento contra o MCP real.
- Lojas, itens, preços e taxas são FICTÍCIOS (`dados_demo_match.json`); todo payload sai com "demonstracao": true.
- Taxa de entrega só aparece em getCartDeliveryMethods/getCart (como no real), nunca na busca.
- Estado (carrinhos, pedidos) fica em memória do módulo; `resetar_demo()` limpa tudo.
"""

from __future__ import annotations

import functools
import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

ARQUIVO_DADOS = Path(__file__).with_name("dados_demo_match.json")

LEITURA = ToolAnnotations(read_only_hint=True)
ESCRITA = ToolAnnotations(read_only_hint=False, destructive_hint=False)

INSTRUCOES = (
    "MCP de DEMONSTRAÇÃO que imita o MCP do consumidor do iFood (dados fictícios). Comece por listAddresses. "
    "Sequência do pedido: searchOffers → getMerchant → getItem → createCart → addItemToCart → "
    "getCartDeliveryMethods → setCartDelivery → listPaymentMethods → setCartPayment → getCart → "
    "submitOrder (só com userConsent: true após confirmação humana) → trackOrder."
)

# Sequência de status do trackOrder (cada chamada avança um passo).
SEQUENCIA_STATUS = [
    ("CONFIRMED", "Pedido confirmado pela loja (demonstração)."),
    ("PREPARING", "A loja está preparando o pedido (demonstração)."),
    ("DISPATCHED", "Pedido saiu para entrega (demonstração)."),
    ("CONCLUDED", "Pedido entregue (demonstração)."),
]

PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "com", "e", "para", "pra", "um", "uma", "algo", "quero", "pode", "ser", "o", "a", "os", "as", "sem"}

# ---------- estado em memória ----------
_estado: dict[str, dict[str, Any]] = {"carrinhos": {}, "pedidos": {}}


def resetar_demo() -> None:
    """Apaga carrinhos e pedidos do demo (os dados de lojas são só leitura)."""
    _estado["carrinhos"].clear()
    _estado["pedidos"].clear()


@functools.lru_cache(maxsize=1)
def _dados() -> dict:
    return json.loads(ARQUIVO_DADOS.read_text(encoding="utf-8"))


def _lojas() -> list[dict]:
    return _dados()["lojas"]


# ---------- utilidades ----------
class ErroDemo(Exception):
    """Erro de negócio do demo; vira ToolError com mensagem legível."""


def _erros_legiveis(fn):
    @functools.wraps(fn)
    def envolvida(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ErroDemo as e:
            raise ToolError(str(e)) from e

    return envolvida


def _selo(payload: dict) -> dict:
    payload["demonstracao"] = True
    return payload


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower().replace("_", " ")


def _termos(query: str) -> list[str]:
    termos = [t for t in re.findall(r"[a-z0-9]+", _normalizar(query)) if t not in PALAVRAS_VAZIAS]
    return termos


def _casa(termo: str, texto: str) -> bool:
    if termo in texto:
        return True
    # plural simples: "sorvetes" → "sorvete", "pokes" → "poke"
    return len(termo) > 3 and termo.endswith("s") and termo[:-1] in texto


def _pontos(termos: list[str], texto: str) -> int:
    return sum(1 for t in termos if _casa(t, texto))


def _reais(centavos: int) -> float:
    return round(centavos / 100, 2)


def _centavos(valor: float) -> int:
    return int(round(valor * 100))


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _loja(merchant_id: str) -> dict:
    for loja in _lojas():
        if loja["id"] == merchant_id:
            return loja
    raise ErroDemo(f"Loja '{merchant_id}' não encontrada. Use um merchantId devolvido por searchOffers ou browseOffers.")


def _item(loja: dict, item_id: str) -> dict:
    for item in loja["itens"]:
        if item["id"] == item_id:
            return item
    raise ErroDemo(f"Item '{item_id}' não existe na loja '{loja['nome']}'. Use um itemId devolvido por getMerchant.")


def _carrinho(cart_id: str) -> dict:
    carrinho = _estado["carrinhos"].get(cart_id)
    if carrinho is None:
        raise ErroDemo(f"Carrinho '{cart_id}' não encontrado. Crie um com createCart.")
    return carrinho


def _pedido(order_id: str) -> dict:
    pedido = _estado["pedidos"].get(order_id)
    if pedido is None:
        raise ErroDemo(f"Pedido '{order_id}' não encontrado. Use o orderId devolvido por submitOrder.")
    return pedido


def _endereco(address_id: str) -> dict:
    for end in _dados()["enderecos"]:
        if end["id"] == address_id:
            return end
    raise ErroDemo(f"Endereço '{address_id}' não encontrado. Use um addressId devolvido por listAddresses.")


# ---------- formatos de saída ----------
def _loja_resumo(loja: dict) -> dict:
    """Loja como aparece nas listas (sem taxa de entrega, como no real)."""
    return {
        "merchantId": loja["id"],
        "name": loja["nome"],
        "merchantType": loja["merchantType"],
        "categories": loja["categorias"],
        "rating": loja["rating"],
        "distance": loja["distancia_km"],
        "deliveryTime": loja["tempo_entrega_min"],
    }


def _item_resumo(loja: dict, item: dict) -> dict:
    return {
        "itemId": item["id"],
        "name": item["nome"],
        "description": item["descricao"],
        "category": item["categoria"],
        "price": item["preco"],
        "tags": list(item.get("tags", [])),
        "perecivel": bool(item.get("perecivel", False)),
        "merchantId": loja["id"],
        "merchantName": loja["nome"],
        "merchantType": loja["merchantType"],
        "rating": loja["rating"],
        "distance": loja["distancia_km"],
        "deliveryTime": loja["tempo_entrega_min"],
    }


def _texto_loja(loja: dict) -> str:
    return _normalizar(" ".join([loja["nome"], *loja["categorias"]]))


def _texto_item(item: dict) -> str:
    return _normalizar(" ".join([item["nome"], item["descricao"], item["categoria"], *item.get("tags", [])]))


def _metodos_entrega(loja: dict) -> list[dict]:
    return [
        {
            "id": "DEFAULT",
            "name": "Entrega padrão",
            "estimatedTime": loja["tempo_entrega_min"],
            "cost": loja["taxa_entrega"],
            "availableWindows": [],
        }
    ]


METODOS_PAGAMENTO = [
    {"id": "pm-demo-credito", "name": "Cartão de crédito final 0000 (demonstração)", "type": "CREDIT_CARD"},
    {"id": "pm-demo-pix", "name": "Pix (demonstração)", "type": "PIX"},
    {"id": "pm-demo-dinheiro", "name": "Dinheiro na entrega (demonstração)", "type": "CASH"},
]


def _totais(carrinho: dict) -> dict:
    loja = _loja(carrinho["merchantId"])
    subtotal = sum(i["unitPriceCents"] * i["quantity"] for i in carrinho["itens"])
    metodo = carrinho["deliveryMethod"]
    taxa_cents = _centavos(metodo["cost"]) if metodo else _centavos(_metodos_entrega(loja)[0]["cost"])
    desconto = 0
    total = subtotal + taxa_cents - desconto
    return {"subtotal": subtotal, "deliveryFee": taxa_cents, "discount": desconto, "total": total}


def _carrinho_saida(carrinho: dict) -> dict:
    loja = _loja(carrinho["merchantId"])
    t = _totais(carrinho)
    avisos = []
    if not carrinho["itens"]:
        avisos.append("Carrinho vazio: adicione ao menos 1 item.")
    if carrinho["deliveryMethod"] is None:
        avisos.append("Método de entrega ainda não definido (taxa mostrada é a do método padrão).")
    if carrinho["paymentMethod"] is None:
        avisos.append("Forma de pagamento ainda não definida.")
    if t["subtotal"] < _centavos(loja.get("pedido_minimo", 0)):
        avisos.append(f"Pedido mínimo da loja: R$ {loja['pedido_minimo']:.2f}.")
    return _selo({
        "cartId": carrinho["cartId"],
        "merchantId": loja["id"],
        "merchantName": loja["nome"],
        "addressId": carrinho["addressId"],
        "items": [
            {
                "cartItemId": i["cartItemId"],
                "itemId": i["itemId"],
                "name": i["name"],
                "quantity": i["quantity"],
                "options": i["options"],
                "unitPrice": _reais(i["unitPriceCents"]),
                "totalPrice": _reais(i["unitPriceCents"] * i["quantity"]),
            }
            for i in carrinho["itens"]
        ],
        "subtotal": _reais(t["subtotal"]),
        "deliveryFee": _reais(t["deliveryFee"]),
        "discount": _reais(t["discount"]),
        "total": _reais(t["total"]),
        "deliveryMethod": carrinho["deliveryMethod"],
        "paymentMethod": carrinho["paymentMethod"],
        "status": carrinho["status"],
        "warnings": avisos,
    })


def _status_saida(pedido: dict) -> dict:
    passo = pedido["passo"]
    codigo, descricao = SEQUENCIA_STATUS[passo]
    historico = [
        {"code": c, "description": f"{d} ({quando})"}
        for (c, d), quando in zip(SEQUENCIA_STATUS[: passo + 1], pedido["horarios"])
    ][::-1]
    terminal = codigo == "CONCLUDED"
    return _selo({
        "orderId": pedido["orderId"],
        "status": {"code": codigo, "description": descricao},
        "statusHistory": historico,
        "agentHints": {
            "retryMessage": None if terminal else "Please call again in 2 seconds for updates (demonstração)",
            "moreStatusEvents": None,
            "pollingStop": True if terminal else None,
            "stopMessage": "Pedido concluído; pare de consultar." if terminal else None,
        },
    })


# ---------- servidor ----------
def criar_servidor_demo() -> MCPServer:
    mcp = MCPServer("ifood-consumidor-demo", instructions=INSTRUCOES)

    # ----- User MCP -----
    @mcp.tool(name="getUser", annotations=LEITURA)
    @_erros_legiveis
    def obter_usuario() -> dict:
        """Perfil do usuário autenticado (demonstração: pessoa fictícia)."""
        u = _dados()["usuario"]
        return _selo({
            "fullName": u["nome"],
            "email": u["email"],
            "phone": None,
            "agentHints": {"suggestedNextAction": "listAddresses"},
        })

    @mcp.tool(name="listAddresses", annotations=LEITURA)
    @_erros_legiveis
    def listar_enderecos() -> dict:
        """Endereços salvos do usuário. Use primeiro em qualquer fluxo de entrega."""
        enderecos = [
            {
                "addressId": e["id"],
                "alias": e["apelido"],
                "location": e["endereco"],
                "formattedAddress": e["endereco"],
                "coordinates": {"latitude": e["latitude"], "longitude": e["longitude"]},
                "usagePattern": {"isLastUsedAddress": i == 0, "isMostUsedAddress30d": i == 0},
            }
            for i, e in enumerate(_dados()["enderecos"])
        ]
        return _selo({"addresses": enderecos, "agentHints": {"decisionTree": "use_last_or_list_options"}})

    # ----- Offer Discovery MCP -----
    @mcp.tool(name="searchOffers", annotations=LEITURA)
    @_erros_legiveis
    def buscar_ofertas(
        query: str,
        latitude: float | None = None,
        longitude: float | None = None,
        limit: int = 20,
        resultKind: Literal["MERCHANT", "ITEM"] = "MERCHANT",
        refinements: dict | None = None,
        sortBy: Literal["relevance", "rating", "distance", "deliveryTime", "price"] = "relevance",
    ) -> dict:
        """Busca lojas (resultKind=MERCHANT) ou itens (resultKind=ITEM) por termo descritivo.

        Demonstração: `refinements` aceita `merchantType` e `maxPrice` (nomes não verificados no MCP real).
        """
        termos = _termos(query)
        if not termos:
            raise ErroDemo("Informe um termo descritivo em 'query' (ex.: 'sorvete', 'pizza').")
        ref = refinements or {}
        tipo = ref.get("merchantType")
        preco_max = ref.get("maxPrice")
        limite = max(1, min(int(limit), 50))

        resultados: list[tuple[int, dict]] = []
        for loja in _lojas():
            if tipo and loja["merchantType"] != tipo:
                continue
            texto_loja = _texto_loja(loja)
            if resultKind == "MERCHANT":
                pts = _pontos(termos, texto_loja)
                pts = max(pts, max((_pontos(termos, _texto_item(i)) for i in loja["itens"]), default=0))
                if pts:
                    resultados.append((pts, _loja_resumo(loja)))
            else:
                for item in loja["itens"]:
                    if preco_max is not None and item["preco"] > float(preco_max):
                        continue
                    pts = _pontos(termos, _texto_item(item) + " " + texto_loja)
                    if pts:
                        resultados.append((pts, _item_resumo(loja, item)))

        chaves = {
            "relevance": lambda r: (-r[0], -r[1]["rating"]),
            "rating": lambda r: (-r[1]["rating"], -r[0]),
            "distance": lambda r: (r[1]["distance"], -r[0]),
            "deliveryTime": lambda r: (r[1]["deliveryTime"], -r[0]),
            "price": lambda r: (r[1].get("price", 0), -r[0]),
        }
        resultados.sort(key=chaves[sortBy])
        lista = [r for _, r in resultados[:limite]]
        return _selo({"resultKind": resultKind, "query": query, "results": lista, "total": len(resultados)})

    @mcp.tool(name="browseOffers", annotations=LEITURA)
    @_erros_legiveis
    def navegar_ofertas(
        latitude: float | None = None,
        longitude: float | None = None,
        merchantType: Literal["RESTAURANT", "GROCERIES", "LIQUORSTORE", "DRUGSTORE", "PETSTORE", "SHOPPING"] | None = None,
        resultKind: Literal["MERCHANT", "ITEM"] = "MERCHANT",
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Explora lojas ou itens perto do endereço, sem termo de busca."""
        lojas = [l for l in _lojas() if merchantType is None or l["merchantType"] == merchantType]
        if resultKind == "MERCHANT":
            todos = [_loja_resumo(l) for l in sorted(lojas, key=lambda l: l["distancia_km"])]
        else:
            todos = [_item_resumo(l, i) for l in lojas for i in l["itens"]]
        pagina = todos[max(0, offset): max(0, offset) + max(1, min(int(limit), 50))]
        return _selo({"resultKind": resultKind, "results": pagina, "total": len(todos), "offset": offset})

    @mcp.tool(name="getRecommendations", annotations=LEITURA)
    @_erros_legiveis
    def obter_recomendacoes(
        latitude: float | None = None,
        longitude: float | None = None,
        contentMode: str | None = None,
        limit: int = 5,
    ) -> dict:
        """Lista curada para o usuário (demonstração: lojas mais bem avaliadas)."""
        lojas = sorted(_lojas(), key=lambda l: -l["rating"])[: max(1, min(int(limit), 20))]
        return _selo({"contentMode": contentMode, "results": [_loja_resumo(l) for l in lojas]})

    @mcp.tool(name="getMerchant", annotations=LEITURA)
    @_erros_legiveis
    def obter_loja(merchantId: str, latitude: float | None = None, longitude: float | None = None) -> dict:
        """Detalhes da loja com cardápio completo (itemId, nome, preço). Não mostra a taxa de entrega."""
        loja = _loja(merchantId)
        categorias: dict[str, list[dict]] = {}
        for item in loja["itens"]:
            categorias.setdefault(item["categoria"], []).append({
                "itemId": item["id"],
                "name": item["nome"],
                "description": item["descricao"],
                "price": item["preco"],
                "tags": list(item.get("tags", [])),
                "perecivel": bool(item.get("perecivel", False)),
            })
        return _selo({
            **_loja_resumo(loja),
            "hours": loja.get("horario"),
            "minimumOrder": loja.get("pedido_minimo"),
            "deliveryMethods": ["DELIVERY"],
            "menu": [{"category": c, "items": itens} for c, itens in categorias.items()],
        })

    @mcp.tool(name="getItem", annotations=LEITURA)
    @_erros_legiveis
    def obter_item(merchantId: str, itemId: str, latitude: float | None = None, longitude: float | None = None) -> dict:
        """Detalhes do item (preço, customizações, tags). Use antes de addItemToCart."""
        loja = _loja(merchantId)
        item = _item(loja, itemId)
        return _selo({
            **_item_resumo(loja, item),
            "promotionalPrice": None,
            "optionGroups": [],
            "agentHints": {"suggestedNextAction": "createCart"},
        })

    # ----- Cart MCP -----
    @mcp.tool(name="createCart", annotations=ESCRITA)
    @_erros_legiveis
    def criar_carrinho(merchantId: str, addressId: str, items: list[dict] | None = None) -> dict:
        """Cria um NOVO carrinho (não é idempotente): 1 carrinho = 1 loja + 1 endereço."""
        loja = _loja(merchantId)
        _endereco(addressId)
        cart_id = f"cart-demo-{uuid.uuid4().hex[:10]}"
        carrinho = {
            "cartId": cart_id,
            "merchantId": loja["id"],
            "addressId": addressId,
            "itens": [],
            "deliveryMethod": None,
            "paymentMethod": None,
            "status": "OPEN",
        }
        _estado["carrinhos"][cart_id] = carrinho
        for inicial in items or []:
            _adicionar(carrinho, inicial.get("itemId", ""), int(inicial.get("quantity", 1)), inicial.get("options"))
        return _carrinho_saida(carrinho)

    def _adicionar(carrinho: dict, item_id: str, quantidade: int, opcoes: list | None) -> dict:
        if carrinho["status"] != "OPEN":
            raise ErroDemo("Este carrinho já virou pedido; crie outro com createCart.")
        if quantidade < 1:
            raise ErroDemo("A quantidade precisa ser pelo menos 1.")
        item = _item(_loja(carrinho["merchantId"]), item_id)
        linha = {
            "cartItemId": f"ci-{uuid.uuid4().hex[:8]}",
            "itemId": item["id"],
            "name": item["nome"],
            "quantity": quantidade,
            "options": list(opcoes or []),
            "unitPriceCents": _centavos(item["preco"]),
        }
        carrinho["itens"].append(linha)
        return linha

    @mcp.tool(name="addItemToCart", annotations=ESCRITA)
    @_erros_legiveis
    def adicionar_item(cartId: str, itemId: str, quantity: int = 1, options: list[dict] | None = None) -> dict:
        """Adiciona um item ao carrinho. Guarde o cartItemId devolvido."""
        carrinho = _carrinho(cartId)
        linha = _adicionar(carrinho, itemId, quantity, options)
        saida = _carrinho_saida(carrinho)
        return _selo({
            "cartItemId": linha["cartItemId"],
            "cartId": cartId,
            "item": {
                "itemId": linha["itemId"],
                "name": linha["name"],
                "quantity": linha["quantity"],
                "unitPrice": _reais(linha["unitPriceCents"]),
                "totalPrice": _reais(linha["unitPriceCents"] * linha["quantity"]),
            },
            "subtotal": saida["subtotal"],
            "total": saida["total"],
        })

    @mcp.tool(name="getCartDeliveryMethods", annotations=LEITURA)
    @_erros_legiveis
    def metodos_entrega(cartId: str) -> dict:
        """Métodos de entrega do carrinho com prazo e custo. Chame antes de setCartDelivery."""
        carrinho = _carrinho(cartId)
        return _selo({
            "cartId": cartId,
            "methods": _metodos_entrega(_loja(carrinho["merchantId"])),
            "agentHints": {"recommendedMethodId": "DEFAULT"},
        })

    @mcp.tool(name="setCartDelivery", annotations=ESCRITA)
    @_erros_legiveis
    def definir_entrega(cartId: str, deliveryMethodId: str, scheduledTime: str | None = None) -> dict:
        """Confirma o método de entrega (id vindo de getCartDeliveryMethods)."""
        carrinho = _carrinho(cartId)
        metodos = {m["id"]: m for m in _metodos_entrega(_loja(carrinho["merchantId"]))}
        if deliveryMethodId not in metodos:
            raise ErroDemo(f"Método de entrega '{deliveryMethodId}' indisponível. Opções: {', '.join(metodos)}.")
        carrinho["deliveryMethod"] = {**metodos[deliveryMethodId], "scheduledTime": scheduledTime}
        return _carrinho_saida(carrinho)

    @mcp.tool(name="listPaymentMethods", annotations=LEITURA)
    @_erros_legiveis
    def listar_pagamentos(cartId: str | None = None, merchantId: str | None = None) -> dict:
        """Formas de pagamento disponíveis. Chame antes de setCartPayment."""
        if cartId:
            _carrinho(cartId)
        elif merchantId:
            _loja(merchantId)
        else:
            raise ErroDemo("Informe cartId ou merchantId.")
        return _selo({"methods": [dict(m) for m in METODOS_PAGAMENTO], "agentHints": {"recommendedMethodId": "pm-demo-pix"}})

    @mcp.tool(name="setCartPayment", annotations=ESCRITA)
    @_erros_legiveis
    def definir_pagamento(cartId: str, paymentMethodId: str, installments: int | None = None) -> dict:
        """Confirma a forma de pagamento (id vindo de listPaymentMethods)."""
        carrinho = _carrinho(cartId)
        metodos = {m["id"]: m for m in METODOS_PAGAMENTO}
        if paymentMethodId not in metodos:
            raise ErroDemo(f"Forma de pagamento '{paymentMethodId}' indisponível. Opções: {', '.join(metodos)}.")
        carrinho["paymentMethod"] = {**metodos[paymentMethodId], "installments": installments}
        return _carrinho_saida(carrinho)

    @mcp.tool(name="getCart", annotations=LEITURA)
    @_erros_legiveis
    def obter_carrinho(cartId: str) -> dict:
        """Conteúdo e totais do carrinho (subtotal, taxa de entrega, desconto, total)."""
        return _carrinho_saida(_carrinho(cartId))

    @mcp.tool(name="submitOrder", annotations=ESCRITA)
    @_erros_legiveis
    def enviar_pedido(cartId: str, userConsent: bool = False, device: str | None = None) -> dict:
        """Envia o pedido. Só com userConsent: true, depois de a pessoa confirmar na tela."""
        if userConsent is not True:
            raise ErroDemo("Pedido não enviado: falta o consentimento explícito da pessoa (userConsent: true).")
        carrinho = _carrinho(cartId)
        if carrinho["status"] != "OPEN":
            raise ErroDemo("Este carrinho já foi enviado como pedido.")
        if not carrinho["itens"]:
            raise ErroDemo("Carrinho vazio: adicione ao menos 1 item antes de enviar.")
        if carrinho["deliveryMethod"] is None:
            raise ErroDemo("Defina a entrega antes (getCartDeliveryMethods → setCartDelivery).")
        if carrinho["paymentMethod"] is None:
            raise ErroDemo("Defina o pagamento antes (listPaymentMethods → setCartPayment).")
        loja = _loja(carrinho["merchantId"])
        resumo = _carrinho_saida(carrinho)
        order_id = str(uuid.uuid4())
        _estado["pedidos"][order_id] = {
            "orderId": order_id,
            "cartId": cartId,
            "carrinho": resumo,
            "endereco": _endereco(carrinho["addressId"])["endereco"],
            "codigo": order_id[:4].upper(),
            "passo": -1,
            "horarios": [],
        }
        carrinho["status"] = "SUBMITTED"
        return _selo({
            "orderId": order_id,
            "merchantName": loja["nome"],
            "total": resumo["total"],
            "estimatedTime": loja["tempo_entrega_min"],
            "agentHints": {"suggestedNextAction": "trackOrder"},
        })

    # ----- Order Tracking MCP -----
    @mcp.tool(name="trackOrder", annotations=LEITURA)
    @_erros_legiveis
    def acompanhar_pedido(orderId: str) -> dict:
        """Status atual do pedido. Siga agentHints.retryMessage e pare quando pollingStop for true.

        Demonstração: cada chamada avança um passo (CONFIRMED → PREPARING → DISPATCHED → CONCLUDED).
        """
        pedido = _pedido(orderId)
        if pedido["passo"] < len(SEQUENCIA_STATUS) - 1:
            pedido["passo"] += 1
            pedido["horarios"].append(_agora())
        return _status_saida(pedido)

    @mcp.tool(name="getOrder", annotations=LEITURA)
    @_erros_legiveis
    def obter_pedido(orderId: str) -> dict:
        """Detalhes fixos do pedido (loja, itens, pagamento, endereço). Sem status: use trackOrder."""
        pedido = _pedido(orderId)
        c = pedido["carrinho"]
        return _selo({
            "id": pedido["orderId"],
            "shortCode": pedido["codigo"],
            "merchant": c["merchantName"],
            "items": [f"{i['name']} (x{i['quantity']}, R$ {i['totalPrice']:.2f})" for i in c["items"]],
            "payment": f"{c['paymentMethod']['name']} - Total R$ {c['total']:.2f}",
            "delivery": {"address": pedido["endereco"], "verificationCode": pedido["codigo"]},
        })

    return mcp
