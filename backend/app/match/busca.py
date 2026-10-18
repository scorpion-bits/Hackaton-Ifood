"""Busca de candidatos no MCP do iFood para um slot (contrato C5).

Toda leitura de campos das tools de descoberta (`listAddresses`, `searchOffers`, `getMerchant`, `browseOffers`)
fica neste arquivo. Lê os dois formatos: o do demo (`name`, `price`, loja na raiz) e o do MCP real conferido nas
amostras de docs/mcp-real/ (`itemName`, `promotionalUnitPrice`/`unitPrice`, loja em `merchant{}`, prazo em
`deliveryMethod.estimatedMinutes`, nota em `reviewRating`, cardápio do getMerchant em `featuredItems`).
Preço, loja, prazo, vertical, perecível e tags vêm SOMENTE da resposta da tool; item sem preço é descartado.
"""

from __future__ import annotations

import re
from typing import Any

from ..ifood_mcp.cliente import ClienteIFood, ErroMCP
from .interprete import contem, normalizar
from .modelos import Candidato, Intencao

MAX_POR_SLOT = 8
LIMITE_BUSCA = 20  # `pageSize` (o MCP real aceita no máximo 25)
TIPO_PADRAO_REAL = "RESTAURANT"  # browseOffers real exige merchantType; o Match é de comida
MIN_RESULTADOS = 3  # abaixo disso tenta lojas (MERCHANT) + getMerchant
MAX_LOJAS_EXTRA = 3
LIMITE_NA_LOJA = 10  # pageSize da busca dentro de uma loja (A′F1)
MAX_CONSULTAS_NA_LOJA = 2  # "coca" e, se a loja não tiver, "refrigerante"
MAX_POR_LOJA_NA_LOJA = 2  # itens que a busca na loja acrescenta ao slot (o juiz avalia cada um)

# tag como vem da tool (normalizada) → restrição canônica
TAGS_CANONICAS = {
    "vegetariano": "vegetariano", "vegetariana": "vegetariano", "vegetarian": "vegetariano",
    "vegano": "vegano", "vegana": "vegano", "vegan": "vegano",
    "sem lactose": "sem_lactose", "zero lactose": "sem_lactose", "lactose free": "sem_lactose",
    "sem gluten": "sem_gluten", "gluten free": "sem_gluten",
}
# tags que confirmam cada restrição (vegano também confirma vegetariano e sem lactose)
CONFIRMA = {
    "vegetariano": {"vegetariano", "vegano"},
    "vegano": {"vegano"},
    "sem_lactose": {"sem_lactose", "vegano"},
    "sem_gluten": {"sem_gluten"},
}
CARNES = ["carne", "frango", "bacon", "salmão", "atum", "peixe", "camarão", "presunto", "calabresa", "linguiça",
          "pepperoni", "costela", "picanha", "filé", "frutos do mar", "bolonhesa", "patinho", "peru", "lombo",
          "salame", "mortadela", "kani", "polvo", "lula", "smash", "sashimi", "pernil", "cordeiro", "porco"]
LATICINIOS = ["leite", "queijo", "cheddar", "muçarela", "mussarela", "parmesão", "provolone", "gorgonzola",
              "cream cheese", "requeijão", "manteiga", "creme de leite", "nata", "iogurte", "chantilly",
              "catupiry", "leite condensado", "leite em pó", "milkshake"]
OUTROS_ANIMAIS = ["ovo", "mel", "gelatina"]
GLUTEN = ["pão", "trigo", "massa", "macarrão", "empanado", "empanada", "croutons", "brioche", "pizza", "lasanha",
          "espaguete", "farinha", "cerveja"]
PERECIVEIS = ["sorvete", "gelato", "açaí", "picolé", "sundae", "milkshake", "sorbet"]

# Bug 19: o browseOffers real trouxe "Rodeio R$ 0,90" (molho do BK) como prato. Item abaixo deste preço não é
# oferecido como prato (o mais barato do demo custa R$ 4,49; uma esfiha real, R$ 6,00).
PRECO_MIN_PRATO = 2.50
# Seção/categoria do cardápio (ou começo do nome) que indica adicional, não prato. "molho" sozinho NÃO entra: o demo
# tem "Molho de tomate 340 g" (mercado) na categoria "Molhos".
SECOES_ADICIONAL = ("adicional", "adicionais", "extra", "extras", "complemento", "complementos", "sache", "saches",
                    "turbine", "turbinar", "monte seu", "personalize")


# ---------- leitura de campos ----------
_CHAVES_LISTA_ENDERECO = ("addresses", "enderecos", "items", "results", "data", "content", "userAddresses")
_CHAVES_ENDERECO = {"addressId", "formattedAddress", "coordinates", "streetName", "street", "latitude", "location",
                    "alias", "neighborhood", "postalCode", "zipCode"}


def _lista_de_enderecos(dados: Any, profundidade: int = 0) -> list[dict]:
    """Acha a lista de endereços em qualquer formato razoável (raiz lista, `addresses`, `data.addresses`…)."""
    if profundidade > 3:
        return []
    if isinstance(dados, list):
        dicts = [e for e in dados if isinstance(e, dict)]
        if dicts and any(_CHAVES_ENDERECO & set(e) for e in dicts):
            return dicts
        for e in dicts:
            achada = _lista_de_enderecos(e, profundidade + 1)
            if achada:
                return achada
        return []
    if not isinstance(dados, dict):
        return []
    for chave in _CHAVES_LISTA_ENDERECO:
        achada = _lista_de_enderecos(dados.get(chave), profundidade + 1)
        if achada:
            return achada
    if profundidade > 0 and _CHAVES_ENDERECO & set(dados):  # um endereço só, sem lista
        return [dados]
    for valor in dados.values():
        if isinstance(valor, (dict, list)):
            achada = _lista_de_enderecos(valor, profundidade + 1)
            if achada:
                return achada
    return []


def _coordenada(endereco: dict, nomes: tuple[str, ...], profundidade: int = 0) -> float | None:
    """latitude/longitude em qualquer nível do endereço (`coordinates`, `location`, `geo`…)."""
    for nome in nomes:
        valor = endereco.get(nome)
        if valor is None or isinstance(valor, (bool, dict, list)) or not str(valor).strip():
            continue
        try:  # coordenada tem sinal e várias casas: não usar `_numero` (que lê preço)
            return float(str(valor).replace(",", "."))
        except ValueError:
            continue
    if profundidade < 3:
        for valor in endereco.values():
            if isinstance(valor, dict):
                achado = _coordenada(valor, nomes, profundidade + 1)
                if achado is not None:
                    return achado
    return None


def _texto_endereco(e: dict) -> str:
    for chave in ("formattedAddress", "fullAddress", "displayName"):
        if isinstance(e.get(chave), str) and e[chave]:
            return e[chave]
    if isinstance(e.get("location"), str):
        return e["location"]
    partes = [e.get(k) for k in ("streetName", "street", "streetNumber", "number", "neighborhood", "city")]
    return ", ".join(str(p) for p in partes if p not in (None, ""))


def ler_endereco(dados: dict) -> dict | None:
    """Endereço a usar: o marcado como último usado, senão o 1º. Saída: id, apelido, texto, latitude, longitude."""
    lista = _lista_de_enderecos(dados)
    if not lista:
        return None
    escolhido = next((e for e in lista if (e.get("usagePattern") or {}).get("isLastUsedAddress")
                      or e.get("isLastUsedAddress") or e.get("default") or e.get("isDefault")), lista[0])
    return {
        "id": escolhido.get("addressId") or escolhido.get("id"),
        "apelido": escolhido.get("alias") or escolhido.get("label") or "",
        "texto": _texto_endereco(escolhido),
        "latitude": _coordenada(escolhido, ("latitude", "lat")),
        "longitude": _coordenada(escolhido, ("longitude", "lng", "lon", "long")),
    }


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        m = re.search(r"\d+(?:[.,]\d{1,2})?", valor.replace(".", "") if "," in valor else valor)
        return float(m.group(0).replace(",", ".")) if m else None
    if isinstance(valor, dict):
        for chave in ("value", "amount", "finalPrice", "price"):
            if chave in valor:
                return _numero(valor[chave])
    return None


def _preco(r: dict) -> float | None:
    """Preço do item como a tool devolveu (promocional, se houver). Sem preço → None (item descartado)."""
    for chave in ("promotionalPrice", "promotionalUnitPrice", "price", "unitPrice"):
        valor = _numero(r.get(chave))
        if valor is not None and valor > 0:
            return round(valor, 2)
    return None


def _eta(valor: Any) -> int | None:
    """deliveryTime em minutos: número, "30-40 min" (pega o maior) ou {min, max}."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return int(valor)
    if isinstance(valor, dict):
        return _eta(valor.get("max") or valor.get("value") or valor.get("min"))
    if isinstance(valor, str):
        numeros = [int(n) for n in re.findall(r"\d+", valor)]
        return max(numeros) if numeros else None
    return None


def _tags(valor: Any) -> list[str]:
    """Tags canônicas (vegetariano, vegano, sem_lactose, sem_gluten) a partir das tags da tool."""
    saida: list[str] = []
    for t in valor or []:
        texto = (t.get("name") or t.get("code") or "") if isinstance(t, dict) else str(t)
        canonica = TAGS_CANONICAS.get(normalizar(texto).strip())
        if canonica and canonica not in saida:
            saida.append(canonica)
    return saida


def _eta_loja(r: dict) -> int | None:
    """Prazo da loja: `deliveryTime` (demo) ou `deliveryMethod(s).estimatedMinutes` (MCP real)."""
    if r.get("deliveryTime") is not None:
        return _eta(r.get("deliveryTime"))
    metodo = r.get("deliveryMethod")
    if not isinstance(metodo, dict):
        metodos = [m for m in (r.get("deliveryMethods") or []) if isinstance(m, dict)]
        metodo = metodos[0] if metodos else {}
    return _eta(metodo.get("estimatedMinutes"))


def _taxa_loja(r: dict) -> float | None:
    """Taxa de entrega da loja na busca (A′F4): `deliveryMethod.promotionalFee`/`fee` (MCP real, conferido em
    docs/mcp-real/searchOffers.json) ou `deliveryFee` (demo). Estimativa: o valor final é o do `getCart`."""
    metodo = r.get("deliveryMethod")
    if not isinstance(metodo, dict):
        metodos = [m for m in (r.get("deliveryMethods") or []) if isinstance(m, dict)]
        metodo = metodos[0] if metodos else {}
    for valor in (metodo.get("promotionalFee"), metodo.get("fee"), r.get("deliveryFee")):
        numero = _numero(valor)
        if numero is not None and numero >= 0:
            return numero
    return None


def _ler_loja(r: dict) -> dict:
    """Loja de um resultado MERCHANT, do getMerchant ou (MCP real) do `merchant{}` aninhado num resultado ITEM."""
    if isinstance(r.get("merchant"), dict):
        r = {**r["merchant"], **{k: r[k] for k in ("merchantType",) if r.get(k)}}
    return {
        "id": r.get("merchantId") or r.get("id"),
        "nome": r.get("merchantName") or r.get("name") or "",
        "vertical": r.get("merchantType") or "",
        "eta": _eta_loja(r),
        "categorias": [str(c) for c in (r.get("categories") or []) if c],
        "avaliacao": _numero(r.get("rating") if r.get("rating") is not None else r.get("reviewRating")),
        "aberta": r.get("isOpen"),
        "taxa": _taxa_loja(r),
        "pedido_minimo": _numero(r.get("minimumOrderAmount") if r.get("minimumOrderAmount") is not None
                                 else r.get("minimumOrder")),
    }


def _parece_adicional(nome: str, categoria: str, preco: float) -> bool:
    """Bug 19: molho/adicional barato não é prato. Preço muito baixo, seção de adicionais ou nome "Adicional …"."""
    if preco < PRECO_MIN_PRATO:
        return True
    secao = normalizar(categoria).strip()
    if secao and any(secao == p or secao.startswith(p + " ") for p in SECOES_ADICIONAL):
        return True
    return normalizar(nome).strip().startswith(("adicional ", "extra "))


def opcoes_obrigatorias(r: dict) -> dict | None:
    """Grupos de opção obrigatórios de um item (`optionGroups` do getItem real, conferido em docs/mcp-real/getItem.json).

    Preenche cada grupo com `minSelections >= 1` com as opções MAIS BARATAS (`additionalPrice`) até o mínimo, no
    formato de `addItemToCart.options[]` do schema real (`{optionId, quantity}`, docs/mcp-real/tools.json).
    Devolve None se a resposta não traz `optionGroups` (não dá para saber). Saída:
    {"opcoes": [...], "extra": soma dos additionalPrice ou None se algum faltar, "nomes": [...], "completo": bool}.
    """
    grupos = r.get("optionGroups")
    if not isinstance(grupos, list):
        return None
    opcoes: list[dict] = []
    nomes: list[str] = []
    extra: float | None = 0.0
    completo = True
    for g in grupos:
        if not isinstance(g, dict):
            continue
        minimo = g.get("minSelections")
        if isinstance(minimo, bool) or not isinstance(minimo, (int, float)) or minimo < 1:
            continue
        validas = [o for o in g.get("options") or [] if isinstance(o, dict) and o.get("optionId")]
        validas.sort(key=lambda o: _numero(o.get("additionalPrice")) if _numero(o.get("additionalPrice")) is not None
                     else float("inf"))
        escolhidas = validas[:int(minimo)]
        if len(escolhidas) < int(minimo):
            completo = False
        for o in escolhidas:
            opcoes.append({"optionId": str(o["optionId"]), "quantity": 1})
            nomes.append(str(o.get("name") or o["optionId"]))
            preco = _numero(o.get("additionalPrice"))
            extra = None if preco is None or extra is None else round(extra + preco, 2)
    return {"opcoes": opcoes, "extra": extra, "nomes": nomes, "completo": completo}


def _ler_item(r: dict, loja: dict | None = None) -> dict | None:
    """Item normalizado a partir de um resultado ITEM do searchOffers/browseOffers ou do menu do getMerchant."""
    loja = loja or _ler_loja(r)
    item_id = r.get("itemId") or r.get("id")
    nome = r.get("name") or r.get("itemName") or r.get("nome")
    preco = _preco(r)
    if not item_id or not nome or preco is None or not loja.get("id"):
        return None
    if loja.get("aberta") is False:  # MCP real: `isOpen: false` → a loja não aceita pedido agora
        return None
    descricao = r.get("description") or r.get("itemDescription") or ""
    categoria = r.get("category") or r.get("menuSection") or r.get("categoria") or ""
    vertical = r.get("merchantType") or loja.get("vertical") or ""
    # adicional barato só existe em restaurante; no mercado/farmácia, item de R$ 2 é produto (detergente)
    if vertical in ("", TIPO_PADRAO_REAL) and _parece_adicional(str(nome), str(categoria), preco):
        return None
    obrigatorias = opcoes_obrigatorias(r)
    # Bug 17: com os grupos à vista (a busca real não traz; getItem traz), item cuja opção obrigatória custa a mais
    # (ou de preço desconhecido) sai: o preço mostrado não seria o do carrinho. Opção obrigatória grátis fica (o
    # checkout preenche).
    if obrigatorias and obrigatorias["opcoes"] and (not obrigatorias["completo"] or obrigatorias["extra"] != 0):
        return None
    texto = normalizar(" ".join([nome, descricao, categoria]))
    perecivel = r.get("perecivel")
    if not isinstance(perecivel, bool):  # campo do demo; no real, inferido do texto da própria tool
        perecivel = any(contem(texto, p) for p in PERECIVEIS)
    return {
        "loja_id": str(loja["id"]),
        "loja_nome": loja.get("nome") or str(loja["id"]),
        "loja_categorias": loja.get("categorias", []),
        "item_id": str(item_id),
        "item_nome": str(nome),
        "descricao": str(descricao),
        "categoria": str(categoria),
        "preco": preco,
        "eta_min": _eta(r.get("deliveryTime")) if r.get("deliveryTime") is not None else loja.get("eta"),
        "vertical": vertical,
        "perecivel": bool(perecivel),
        "tags": _tags(r.get("tags")),
        "avaliacao": _numero(r.get("rating")) if r.get("rating") is not None else loja.get("avaliacao"),
        "taxa_entrega": loja.get("taxa"),
        "pedido_minimo": loja.get("pedido_minimo"),
    }


def _itens_do_menu(dados: dict) -> list[dict]:
    """Itens do getMerchant: `menu[].items` (demo) ou `featuredItems` (MCP real: só os destaques da loja)."""
    loja = _ler_loja(dados)
    itens = []
    brutos = [{**r, "category": r.get("category") or secao.get("category") or ""}
              for secao in dados.get("menu") or [] if isinstance(secao, dict)
              for r in secao.get("items") or [] if isinstance(r, dict)]
    brutos += [r for r in dados.get("featuredItems") or [] if isinstance(r, dict)]
    for r in brutos:
        item = _ler_item(r, loja)
        if item:
            itens.append(item)
    return itens


# ---------- regras ----------
def violacoes(restricoes: list[str], tags: list[str], texto_norm: str) -> list[str]:
    """Restrições claramente contrariadas: sem tag que confirme E com ingrediente proibido no nome/descrição.

    Na dúvida (sem tag, sem ingrediente proibido) não elimina: o juiz avisa "confirme com a loja".
    """
    def tem(palavras: list[str]) -> bool:
        return any(contem(texto_norm, p) for p in palavras)

    viola = []
    for r in restricoes:
        if set(tags) & CONFIRMA.get(r, set()):
            continue
        if (r == "vegetariano" and tem(CARNES)) or \
           (r == "vegano" and tem(CARNES + LATICINIOS + OUTROS_ANIMAIS)) or \
           (r == "sem_lactose" and tem(LATICINIOS)) or \
           (r == "sem_gluten" and tem(GLUTEN)):
            viola.append(r)
    return viola


def _aceita(item: dict, intencao: Intencao, qualquer_vertical: bool = False) -> bool:
    """`qualquer_vertical`: busca dentro de uma loja já escolhida (A′F1) — a loja vale mesmo sendo de outra
    categoria ("areia" depois de "ração" sai do pet shop)."""
    if not qualquer_vertical and intencao.verticais and item["vertical"] and item["vertical"] not in intencao.verticais:
        return False
    if intencao.orcamento_max is not None and item["preco"] > intencao.orcamento_max + 1e-9:
        return False
    return True


def _candidato(item: dict, intencao: Intencao) -> Candidato:
    texto = normalizar(" ".join([item["item_nome"], item["descricao"], item["categoria"]]))
    return Candidato(
        participante_id=intencao.participante_id, loja_id=item["loja_id"], loja_nome=item["loja_nome"],
        item_id=item["item_id"], item_nome=item["item_nome"], preco=item["preco"], eta_min=item["eta_min"],
        vertical=item["vertical"], perecivel=item["perecivel"],
        viola=violacoes(intencao.restricoes, item["tags"], texto),
    )


def _diversificar(itens: list[tuple[Candidato, dict]]) -> list[tuple[Candidato, dict]]:
    """≤ 8 por slot, alternando lojas (para o otimizador ter como juntar pessoas em até 3 lojas).

    Quem não viola restrição vem antes; dentro de cada loja mantém a ordem da tool.
    """
    escolhidos: list[tuple[Candidato, dict]] = []
    for grupo in ([p for p in itens if not p[0].viola], [p for p in itens if p[0].viola]):
        por_loja: dict[str, list] = {}
        for par in grupo:
            por_loja.setdefault(par[0].loja_id, []).append(par)
        while len(escolhidos) < MAX_POR_SLOT and any(por_loja.values()):
            for fila in por_loja.values():
                if fila and len(escolhidos) < MAX_POR_SLOT:
                    escolhidos.append(fila.pop(0))
    return escolhidos


async def buscar_detalhado(cliente: ClienteIFood, intencao: Intencao, endereco: dict,
                           fechadas: dict[str, list[str]] | None = None,
                           acima: dict[str, float] | None = None,
                           ) -> tuple[list[Candidato], dict[tuple[str, str], dict]]:
    """Candidatos do slot + detalhes de cada um (descrição, categoria, tags…) para o juiz.
    `fechadas` (bug 32): recebe, por slot, as lojas que tinham o item mas vieram `isOpen: false`.
    `acima`: recebe, por slot, o menor preço do que a busca achou mas passou do orçamento da pessoa."""
    geo = {k: endereco.get(k) for k in ("latitude", "longitude") if endereco.get(k) is not None}
    coletados: dict[tuple[str, str], tuple[Candidato, dict]] = {}
    lojas_fechadas: list[str] = []
    mais_barato_acima: list[float] = []

    def anotar_fechada(r: dict) -> None:
        loja = _ler_loja(r)
        if loja.get("aberta") is False and loja.get("nome") and loja["nome"] not in lojas_fechadas:
            lojas_fechadas.append(loja["nome"])

    def guardar(item: dict | None) -> None:
        if item and intencao.orcamento_max is not None and item["preco"] > intencao.orcamento_max + 1e-9 \
                and _aceita(item, Intencao(intencao.participante_id, verticais=intencao.verticais)) \
                and _bate_consulta(item, intencao):  # só o que é o pedido (não a água do cardápio da pizzaria)
            mais_barato_acima.append(item["preco"])
        if item and _aceita(item, intencao):
            chave = (item["loja_id"], item["item_id"])
            if chave not in coletados:
                coletados[chave] = (_candidato(item, intencao), item)

    def bons() -> int:
        return sum(1 for c, _ in coletados.values() if not c.viola)

    for consulta in intencao.consultas:
        if bons() >= 2 * MAX_POR_SLOT:
            break
        extra: dict[str, Any] = {}
        if len(intencao.verticais) == 1 and intencao.verticais[0] != TIPO_PADRAO_REAL:
            extra["merchantType"] = intencao.verticais[0]  # varejo (A′F5): "ração" só no pet shop
        try:
            dados = await cliente.chamar("searchOffers", query=consulta, **extra, resultKind="ITEM",
                                         pageSize=LIMITE_BUSCA, **geo)  # merchantType logo após a query: o rastro mostra
        except ErroMCP:
            continue
        for r in dados.get("results") or dados.get("items") or []:
            if isinstance(r, dict):
                item = _ler_item(r)
                if item is None:
                    anotar_fechada(r)
                guardar(item)

    if bons() < MIN_RESULTADOS and intencao.consultas:
        lojas_vistas: set[str] = set()
        for consulta in intencao.consultas[:2]:
            try:
                dados = await cliente.chamar("searchOffers", query=consulta, resultKind="MERCHANT", pageSize=5, **geo)
            except ErroMCP:
                continue
            for r in (dados.get("results") or [])[:MAX_LOJAS_EXTRA]:
                loja = _ler_loja(r) if isinstance(r, dict) else {}
                if not loja.get("id") or loja["id"] in lojas_vistas:
                    continue
                if intencao.verticais and loja["vertical"] and loja["vertical"] not in intencao.verticais:
                    continue
                if loja.get("aberta") is False:
                    continue
                lojas_vistas.add(loja["id"])
                try:
                    menu = await cliente.chamar("getMerchant", merchantId=loja["id"], **geo)
                except ErroMCP:
                    continue
                for item in _itens_do_menu(menu):
                    guardar(item)

    # Pedido genérico ("qualquer coisa") OU as consultas do slot não trouxeram nenhum candidato válido (C16):
    # explora perto do endereço, na vertical pedida. O juiz dá nota baixa e o motor avisa "a opção mais próxima é X".
    # No varejo (A′F5) não explora: um produto qualquer do mercado não é "opção aproximada" de "areia".
    varejo = bool(intencao.verticais) and TIPO_PADRAO_REAL not in intencao.verticais and not any(
        normalizar(c).strip() == "mercado" for c in intencao.consultas)
    # achou o pedido, só que acima do orçamento: explorar daria um item qualquer barato (ex.: água por "pizza até 5")
    if bons() == 0 and not varejo and not mais_barato_acima:
        args: dict[str, Any] = {"resultKind": "ITEM", "pageSize": LIMITE_BUSCA, **geo}
        if intencao.verticais:
            args["merchantType"] = intencao.verticais[0]
        elif getattr(cliente, "modo", "demo") != "demo":  # no real, merchantType é obrigatório no browseOffers
            args["merchantType"] = TIPO_PADRAO_REAL
        try:
            dados = await cliente.chamar("browseOffers", **args)
            for r in dados.get("results") or []:
                if isinstance(r, dict):
                    guardar(_ler_item(r))
        except ErroMCP:
            pass

    if fechadas is not None and lojas_fechadas:
        fechadas[intencao.participante_id] = lojas_fechadas
    if acima is not None and mais_barato_acima:
        acima[intencao.participante_id] = min(mais_barato_acima)
    selecionados = _diversificar(list(coletados.values()))
    candidatos = [c for c, _ in selecionados]
    detalhes = {(c.loja_id, c.item_id): item for c, item in selecionados}
    return candidatos, detalhes


async def buscar_na_loja(cliente: ClienteIFood, intencao: Intencao, endereco: dict, loja_id: str,
                         vertical: str = "") -> tuple[list[Candidato], dict[tuple[str, str], dict]]:
    """Candidatos do slot DENTRO de uma loja: `searchOffers` com `refinements.merchantId` (o caminho que o
    `getMerchant` real indica em `catalogSummary.navigationHint`). Pedido completo (A′F1, etapa 05): o refri vem da
    mesma pizzaria da pizza, não de outra loja. Tenta as consultas em ordem e para na primeira que acha item."""
    geo = {k: endereco.get(k) for k in ("latitude", "longitude") if endereco.get(k) is not None}
    for consulta in intencao.consultas[:MAX_CONSULTAS_NA_LOJA]:
        # refinements logo depois da query: o rastro (≤ 80 caracteres) mostra que a busca foi dentro da loja
        args: dict[str, Any] = {"query": consulta, "refinements": {"merchantId": loja_id}, "resultKind": "ITEM",
                                "pageSize": LIMITE_NA_LOJA, **geo}
        if vertical:
            args["merchantType"] = vertical
        try:
            dados = await cliente.chamar("searchOffers", **args)
        except ErroMCP:
            return [], {}
        achados: list[tuple[Candidato, dict]] = []
        for r in dados.get("results") or dados.get("items") or []:
            item = _ler_item(r) if isinstance(r, dict) else None
            # a busca semântica real pode trazer qualquer item da loja: só fica o que bate com o pedido
            if (item and item["loja_id"] == str(loja_id) and _aceita(item, intencao, qualquer_vertical=True)
                    and _bate_consulta(item, intencao)):
                achados.append((_candidato(item, intencao), item))
        achados.sort(key=lambda par: bool(par[0].viola))  # quem não viola restrição primeiro
        if achados:
            achados = achados[:MAX_POR_LOJA_NA_LOJA]
            return [c for c, _ in achados], {(c.loja_id, c.item_id): item for c, item in achados}
    return [], {}


def _bate_consulta(item: dict, intencao: Intencao) -> bool:
    """Alguma palavra (≥ 3 letras) das consultas/vontades aparece no nome, descrição ou seção do item."""
    texto = normalizar(" ".join([item["item_nome"], item["descricao"], item["categoria"]]))
    palavras = {p for t in [*intencao.consultas, *intencao.vontades] for p in re.findall(r"[a-z0-9]+", normalizar(t))
                if len(p) >= 3}
    return any(re.search(rf"\b{re.escape(p)}", texto) for p in palavras)


async def buscar(cliente: ClienteIFood, intencao: Intencao, endereco: dict) -> list[Candidato]:
    """≤ 8 candidatos do slot, sem duplicatas, com `viola` marcado. Preço só da tool."""
    candidatos, _ = await buscar_detalhado(cliente, intencao, endereco)
    return candidatos
