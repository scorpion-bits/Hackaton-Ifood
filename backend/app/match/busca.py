"""Busca de candidatos no MCP do iFood para um slot (contrato C5).

Toda leitura de campos das tools de descoberta (`listAddresses`, `searchOffers`, `getMerchant`, `browseOffers`)
fica neste arquivo: a etapa 03 ajusta o mapeamento para o MCP real num lugar só.
Preço, loja, prazo, vertical, perecível e tags vêm SOMENTE da resposta da tool; item sem preço é descartado.
"""

from __future__ import annotations

import re
from typing import Any

from ..ifood_mcp.cliente import ClienteIFood, ErroMCP
from .interprete import contem, normalizar
from .modelos import Candidato, Intencao

MAX_POR_SLOT = 8
LIMITE_BUSCA = 20
MIN_RESULTADOS = 3  # abaixo disso tenta lojas (MERCHANT) + getMerchant
MAX_LOJAS_EXTRA = 3

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


# ---------- leitura de campos ----------
def ler_endereco(dados: dict) -> dict | None:
    """Endereço a usar: o marcado como último usado, senão o 1º. Saída: id, apelido, texto, latitude, longitude."""
    lista = dados.get("addresses") or dados.get("enderecos") or []
    lista = [e for e in lista if isinstance(e, dict)]
    if not lista:
        return None
    escolhido = next((e for e in lista if (e.get("usagePattern") or {}).get("isLastUsedAddress")), lista[0])
    coords = escolhido.get("coordinates") or {}
    return {
        "id": escolhido.get("addressId") or escolhido.get("id"),
        "apelido": escolhido.get("alias") or "",
        "texto": escolhido.get("formattedAddress") or escolhido.get("location") or "",
        "latitude": coords.get("latitude", escolhido.get("latitude")),
        "longitude": coords.get("longitude", escolhido.get("longitude")),
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
    for chave in ("promotionalPrice", "price", "unitPrice"):
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


def _ler_loja(r: dict) -> dict:
    return {
        "id": r.get("merchantId") or r.get("id"),
        "nome": r.get("merchantName") or r.get("name") or "",
        "vertical": r.get("merchantType") or "",
        "eta": _eta(r.get("deliveryTime")),
        "categorias": [str(c) for c in (r.get("categories") or []) if c],
        "avaliacao": _numero(r.get("rating")),
    }


def _ler_item(r: dict, loja: dict | None = None) -> dict | None:
    """Item normalizado a partir de um resultado ITEM do searchOffers/browseOffers ou do menu do getMerchant."""
    loja = loja or _ler_loja(r)
    item_id = r.get("itemId") or r.get("id")
    nome = r.get("name") or r.get("nome")
    preco = _preco(r)
    if not item_id or not nome or preco is None or not loja.get("id"):
        return None
    descricao = r.get("description") or ""
    categoria = r.get("category") or r.get("categoria") or ""
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
        "vertical": r.get("merchantType") or loja.get("vertical") or "",
        "perecivel": bool(perecivel),
        "tags": _tags(r.get("tags")),
        "avaliacao": _numero(r.get("rating")) if r.get("rating") is not None else loja.get("avaliacao"),
    }


def _itens_do_menu(dados: dict) -> list[dict]:
    loja = _ler_loja(dados)
    itens = []
    for secao in dados.get("menu") or []:
        for r in secao.get("items") or []:
            r = {**r, "category": r.get("category") or secao.get("category") or ""}
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


def _aceita(item: dict, intencao: Intencao) -> bool:
    if intencao.verticais and item["vertical"] and item["vertical"] not in intencao.verticais:
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
    """≤ 8 por slot, alternando lojas (para o otimizador ter como juntar pessoas em até 2 lojas).

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


async def buscar_detalhado(cliente: ClienteIFood, intencao: Intencao,
                           endereco: dict) -> tuple[list[Candidato], dict[tuple[str, str], dict]]:
    """Candidatos do slot + detalhes de cada um (descrição, categoria, tags…) para o juiz."""
    geo = {k: endereco.get(k) for k in ("latitude", "longitude") if endereco.get(k) is not None}
    coletados: dict[tuple[str, str], tuple[Candidato, dict]] = {}

    def guardar(item: dict | None) -> None:
        if item and _aceita(item, intencao):
            chave = (item["loja_id"], item["item_id"])
            if chave not in coletados:
                coletados[chave] = (_candidato(item, intencao), item)

    def bons() -> int:
        return sum(1 for c, _ in coletados.values() if not c.viola)

    for consulta in intencao.consultas:
        if bons() >= 2 * MAX_POR_SLOT:
            break
        try:
            dados = await cliente.chamar("searchOffers", query=consulta, resultKind="ITEM", limit=LIMITE_BUSCA, **geo)
        except ErroMCP:
            continue
        for r in dados.get("results") or dados.get("items") or []:
            if isinstance(r, dict):
                guardar(_ler_item(r))

    if bons() < MIN_RESULTADOS and intencao.consultas:
        lojas_vistas: set[str] = set()
        for consulta in intencao.consultas[:2]:
            try:
                dados = await cliente.chamar("searchOffers", query=consulta, resultKind="MERCHANT", limit=5, **geo)
            except ErroMCP:
                continue
            for r in (dados.get("results") or [])[:MAX_LOJAS_EXTRA]:
                loja = _ler_loja(r) if isinstance(r, dict) else {}
                if not loja.get("id") or loja["id"] in lojas_vistas:
                    continue
                if intencao.verticais and loja["vertical"] and loja["vertical"] not in intencao.verticais:
                    continue
                lojas_vistas.add(loja["id"])
                try:
                    menu = await cliente.chamar("getMerchant", merchantId=loja["id"], **geo)
                except ErroMCP:
                    continue
                for item in _itens_do_menu(menu):
                    guardar(item)

    if not coletados and not intencao.consultas:  # pedido genérico ("qualquer coisa"): explora perto do endereço
        args: dict[str, Any] = {"resultKind": "ITEM", "limit": LIMITE_BUSCA, **geo}
        if intencao.verticais:
            args["merchantType"] = intencao.verticais[0]
        try:
            dados = await cliente.chamar("browseOffers", **args)
            for r in dados.get("results") or []:
                if isinstance(r, dict):
                    guardar(_ler_item(r))
        except ErroMCP:
            pass

    selecionados = _diversificar(list(coletados.values()))
    candidatos = [c for c, _ in selecionados]
    detalhes = {(c.loja_id, c.item_id): item for c, item in selecionados}
    return candidatos, detalhes


async def buscar(cliente: ClienteIFood, intencao: Intencao, endereco: dict) -> list[Candidato]:
    """≤ 8 candidatos do slot, sem duplicatas, com `viola` marcado. Preço só da tool."""
    candidatos, _ = await buscar_detalhado(cliente, intencao, endereco)
    return candidatos
