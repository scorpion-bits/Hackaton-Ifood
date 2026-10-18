"""Diagnóstico do MCP real do iFood (contrato C10). Roda no PC da equipe, com o login já feito no app.

    Linux:   cd backend && .venv/bin/python -m app.ifood_mcp.diagnostico [--carrinho]
    Windows: cd backend; .venv\\Scripts\\python -m app.ifood_mcp.diagnostico [--carrinho]

1. `list_tools` → `docs/mcp-real/tools.json` (nome, descrição, input/output schema).
2. Só leitura: `getUser`, `listAddresses`, `searchOffers` ("pizza", "sorvete", "hambúrguer" × ITEM/MERCHANT),
   `getMerchant` e `getItem` do 1º resultado, `getRecommendations` → `docs/mcp-real/<tool>.json`.
3. Com `--carrinho`: `createCart` em 2 lojas diferentes, `addItemToCart`, `getCartDeliveryMethods`,
   `listPaymentMethods`, `getCart`. **Nunca chama `submitOrder`** (nem `setCartPayment`/`setCartDelivery`).

Tudo é SANITIZADO antes de gravar (nome de pessoa, e-mail, telefone, CPF, endereço textual, últimos dígitos,
qualquer campo com "token"; coordenadas com 2 casas). Confira os arquivos antes do commit mesmo assim.
`--demo` roda contra o servidor de demonstração (útil para testar o próprio diagnóstico, sem rede).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..config import RAIZ, carregar
from .cliente import ClienteIFood, ErroMCP, abrir_cliente

SAIDA_PADRAO = RAIZ / "docs" / "mcp-real"

TOOLS_DA_DOC = [
    "getUser", "listAddresses", "createAddress",
    "searchOffers", "browseOffers", "getRecommendations", "listItemTaxonomy", "getMerchant", "getItem",
    "createCart", "getCart", "getCartDeliveryMethods", "addItemToCart", "updateCartItem", "removeItemFromCart",
    "listVouchers", "setVoucher", "removeVoucher", "setCartDelivery", "listPaymentMethods", "setCartPayment",
    "submitOrder",
    "trackOrder", "getOrder",
]
# O diagnóstico nunca envia pedido nem escolhe pagamento/entrega/endereço.
PROIBIDAS = {"submitOrder", "setCartPayment", "setCartDelivery", "createAddress", "setVoucher"}
BUSCAS = ["pizza", "sorvete", "hambúrguer"]

# ---------- sanitização ----------
MASCARA = "***"
# Chaves sempre mascaradas (comparação sem caixa e sem "_"/"-").
_SEMPRE = {
    "fullname", "firstname", "lastname", "displayname", "nickname", "socialname", "email", "emails", "phone",
    "phones", "phonenumber", "mobilephone", "cellphone", "taxpayeridentificationnumber", "cpf", "cnpj",
    "document", "documentnumber", "documents", "birthdate", "birthday", "lastdigits", "last4", "bin",
    "cardnumber", "maskedcardnumber", "holdername", "cardholdername", "street", "streetname", "streetnumber",
    "number", "complement", "formattedaddress", "addressline", "addressline1", "addressline2", "zipcode",
    "postalcode", "cep", "reference", "landmark", "userid", "customerid", "accountid", "consumerid", "ip",
}
# Contextos: dentro de chaves "pessoais", `name`/`alias`/`label`... também são mascarados; dentro de chaves de
# endereço, TODO texto é mascarado exceto bairro/cidade/estado/país e ids. Formas de pagamento não são contexto
# pessoal: o nome "Pix"/"Crédito" importa para a pergunta 1 (os dígitos do cartão caem em `_SEMPRE`/filtro de texto).
_CONTEXTO_PESSOAL = {
    "user", "customer", "consumer", "account", "profile", "recipient", "contact", "holder", "owner", "buyer",
    "person", "me",
}
_CONTEXTO_ENDERECO = {
    "address", "addresses", "deliveryaddress", "useraddress", "shippingaddress", "billingaddress", "candidates",
}
_NOME_EM_CONTEXTO = {"name", "alias", "title", "label", "description", "nick"}
_TEXTO_SEGURO_ENDERECO = {
    "neighborhood", "district", "city", "cityname", "state", "statecode", "uf", "country", "countrycode",
    "id", "addressid", "candidateid", "type", "kind", "category", "status",
}
_SEM_CONTEXTO = {"agenthints", "hints", "_meta", "meta"}  # dicas do agente: texto técnico, fica legível
# Contexto da resposta inteira, por tool.
CONTEXTO_POR_TOOL = {"getUser": "pessoal", "listAddresses": "endereco", "createAddress": "endereco"}
_COORDENADAS = {"latitude", "longitude", "lat", "lng", "lon", "long"}

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_RE_JWT = re.compile(r"\beyJ[\w-]{5,}\.[\w-]{5,}\.[\w-]*")
_RE_BEARER = re.compile(r"(?i)bearer\s+[\w.~+/=-]{8,}")
_RE_CARTAO = re.compile(r"(?:[*•xX]{2,}[\s.-]*\d{4}\b)|(?i:\bfinal\s*\d{4}\b)")
_RE_TELEFONE = re.compile(r"(?<![\w.])\+?(?:55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?![\w.])")


def _norm(chave: str) -> str:
    return re.sub(r"[_\-\s]", "", str(chave)).lower()


def _limpar_texto(texto: str) -> str:
    texto = _RE_JWT.sub(MASCARA, texto)
    texto = _RE_BEARER.sub("Bearer " + MASCARA, texto)
    texto = _RE_EMAIL.sub(MASCARA, texto)
    texto = _RE_CPF.sub(MASCARA, texto)
    texto = _RE_CARTAO.sub(MASCARA, texto)
    return _RE_TELEFONE.sub(MASCARA, texto)


def _arredondar(valor: Any) -> Any:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)
    if isinstance(valor, str):
        try:
            return round(float(valor), 2)
        except ValueError:
            return MASCARA
    if isinstance(valor, list):
        return [_arredondar(v) for v in valor]
    if isinstance(valor, dict):
        return {k: _arredondar(v) for k, v in valor.items()}
    return valor


def _mascarar(valor: Any) -> Any:
    """Mantém a forma (lista/dict/tipo) para a 03.5 entender o formato, sem o conteúdo."""
    if valor is None or isinstance(valor, bool):
        return valor
    if isinstance(valor, dict):
        return {k: _mascarar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_mascarar(v) for v in valor[:3]]
    return MASCARA


def sanitizar(dados: Any, contexto: str | None = None) -> Any:
    """Cópia sem dados pessoais. `contexto`: None, "pessoal" (dados da pessoa) ou "endereco" (só bairro/cidade)."""
    if isinstance(dados, dict):
        saida = {}
        for chave, valor in dados.items():
            n = _norm(chave)
            if "token" in n or "secret" in n or "password" in n or n in _SEMPRE:
                saida[chave] = _mascarar(valor)
            elif n in _COORDENADAS or n == "coordinates":
                saida[chave] = _arredondar(valor)
            elif n in _SEM_CONTEXTO:
                saida[chave] = sanitizar(valor, None)
            elif n in _CONTEXTO_ENDERECO or contexto == "endereco":
                if isinstance(valor, (dict, list)):
                    saida[chave] = sanitizar(valor, "endereco")
                elif isinstance(valor, str) and not (contexto == "endereco" and n in _TEXTO_SEGURO_ENDERECO):
                    saida[chave] = MASCARA
                else:
                    saida[chave] = sanitizar(valor, "endereco")
            elif contexto == "pessoal" and n in _NOME_EM_CONTEXTO and not isinstance(valor, (dict, list)):
                saida[chave] = _mascarar(valor)
            else:
                saida[chave] = sanitizar(valor, "pessoal" if n in _CONTEXTO_PESSOAL else contexto)
        return saida
    if isinstance(dados, list):
        return [sanitizar(v, contexto) for v in dados]
    if isinstance(dados, str):
        return _limpar_texto(dados)
    return dados


# ---------- utilidades ----------
def _achar(obj: Any, chaves: tuple[str, ...]) -> Any:
    """Primeiro valor (busca em largura) de uma das chaves."""
    fila = [obj]
    while fila:
        atual = fila.pop(0)
        if isinstance(atual, dict):
            for c in chaves:
                if atual.get(c) not in (None, "", [], {}):
                    return atual[c]
            fila.extend(v for v in atual.values() if isinstance(v, (dict, list)))
        elif isinstance(atual, list):
            fila.extend(atual)
    return None


def _lista_resultados(resposta: Any) -> list[dict]:
    if isinstance(resposta, list):
        return [r for r in resposta if isinstance(r, dict)]
    if isinstance(resposta, dict):
        for chave in ("results", "items", "offers", "merchants", "data", "content"):
            valor = resposta.get(chave)
            if isinstance(valor, list):
                return [r for r in valor if isinstance(r, dict)]
            if isinstance(valor, dict):
                interna = _lista_resultados(valor)
                if interna:
                    return interna
    return []


def _caminhos_de_preco(dados: Any, prefixo: str = "") -> set[str]:
    """Caminhos (com [] para listas) de campos que parecem preço/taxa/total."""
    padrao = re.compile(r"(?i)price|fee|total|subtotal|cost|discount|amount|value|tax|preco|taxa|valor")
    achados: set[str] = set()
    if isinstance(dados, dict):
        for k, v in dados.items():
            caminho = f"{prefixo}.{k}" if prefixo else str(k)
            if padrao.search(str(k)):
                achados.add(caminho)
            achados |= _caminhos_de_preco(v, caminho)
    elif isinstance(dados, list):
        for v in dados[:20]:
            achados |= _caminhos_de_preco(v, prefixo + "[]")
    return achados


class Diagnostico:
    def __init__(self, cliente: ClienteIFood, saida: Path):
        self.cliente = cliente
        self.saida = saida
        self.schemas: dict[str, dict] = {}
        self.registros: dict[str, list[dict]] = {}

    def args_para(self, tool: str, candidatos: dict[str, Any]) -> dict[str, Any]:
        """Filtra os argumentos pelo input_schema real (se a tool existir e tiver `properties`)."""
        schema = self.schemas.get(tool) or {}
        props = schema.get("properties")
        args = {k: v for k, v in candidatos.items() if v is not None}
        if isinstance(props, dict) and props:
            args = {k: v for k, v in args.items() if k in props}
        return args

    async def chamar(self, tool: str, rotulo: str | None = None, **candidatos: Any) -> Any:
        if tool in PROIBIDAS:
            raise RuntimeError(f"O diagnóstico não chama {tool}.")
        args = self.args_para(tool, candidatos)
        inicio = time.perf_counter()
        registro: dict[str, Any] = {"rotulo": rotulo or tool, "args": sanitizar(args)}
        try:
            resposta = await self.cliente.chamar(tool, **args)
            registro |= {"ok": True, "resposta": sanitizar(resposta, CONTEXTO_POR_TOOL.get(tool))}
        except ErroMCP as e:
            resposta = None
            registro |= {"ok": False, "erro": _limpar_texto(str(e))}
        registro["ms"] = int((time.perf_counter() - inicio) * 1000)
        self.registros.setdefault(tool, []).append(registro)
        estado = "ok" if registro["ok"] else f"ERRO: {registro['erro'][:100]}"
        print(f"  {rotulo or tool:<40} {registro['ms']:>6} ms  {estado}")
        return resposta

    def gravar(self) -> None:
        self.saida.mkdir(parents=True, exist_ok=True)
        for tool, chamadas in self.registros.items():
            (self.saida / f"{tool}.json").write_text(
                json.dumps({"tool": tool, "chamadas": chamadas}, ensure_ascii=False, indent=2), encoding="utf-8")


async def executar(cliente: ClienteIFood, saida: Path, carrinho: bool = False) -> dict:
    d = Diagnostico(cliente, saida)
    saida.mkdir(parents=True, exist_ok=True)

    print("list_tools…")
    tools = await cliente.listar_tools()
    d.schemas = {t["name"]: t.get("input_schema") or {} for t in tools}
    (saida / "tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2), encoding="utf-8")
    nomes = [t["name"] for t in tools]

    print("Leitura:")
    await d.chamar("getUser")
    enderecos = await d.chamar("listAddresses")
    lista = enderecos.get("addresses") if isinstance(enderecos, dict) else None
    lista = [e for e in lista if isinstance(e, dict)] if isinstance(lista, list) else _lista_resultados(enderecos)
    endereco = lista[0] if lista else None
    endereco_id = _achar(endereco, ("addressId", "id")) if endereco else None
    lat = _achar(endereco, ("latitude", "lat")) if endereco else None
    lon = _achar(endereco, ("longitude", "lng", "lon")) if endereco else None
    geo = {"latitude": lat, "longitude": lon, "addressId": endereco_id}

    itens: list[dict] = []
    lojas: list[dict] = []
    for consulta in BUSCAS:
        for tipo in ("ITEM", "MERCHANT"):
            r = await d.chamar("searchOffers", rotulo=f"searchOffers {consulta} {tipo}", query=consulta,
                               resultKind=tipo, limit=5, **geo)
            (itens if tipo == "ITEM" else lojas).extend(_lista_resultados(r))

    primeiro = itens[0] if itens else None
    merchant_id = _achar(primeiro, ("merchantId",)) if primeiro else None
    merchant_id = merchant_id or (_achar(lojas[0], ("merchantId", "id")) if lojas else None)
    item_id = _achar(primeiro, ("itemId", "id")) if primeiro else None
    if merchant_id:
        await d.chamar("getMerchant", merchantId=merchant_id, **geo)
    if merchant_id and item_id:
        await d.chamar("getItem", merchantId=merchant_id, itemId=item_id, **geo)
    await d.chamar("getRecommendations", limit=5, **geo)

    resultado_carrinho = None
    if carrinho:
        print("Carrinho (sem submitOrder):")
        resultado_carrinho = await _testar_carrinhos(d, itens, endereco_id, geo)

    d.gravar()
    resumo = _resumo(nomes, d, resultado_carrinho)
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumo


async def _testar_carrinhos(d: Diagnostico, itens: list[dict], endereco_id: Any, geo: dict) -> dict:
    """Abre carrinhos em 2 lojas diferentes (1 item cada) e confere se os 2 continuam abertos."""
    escolhidos: list[tuple[Any, Any]] = []
    for item in itens:
        loja, item_id = _achar(item, ("merchantId",)), _achar(item, ("itemId", "id"))
        if loja and item_id and loja not in {e[0] for e in escolhidos}:
            escolhidos.append((loja, item_id))
        if len(escolhidos) == 2:
            break
    carrinhos: list[Any] = []
    for loja, item_id in escolhidos:
        criado = await d.chamar("createCart", merchantId=loja, addressId=endereco_id,
                                latitude=geo.get("latitude"), longitude=geo.get("longitude"))
        cart_id = _achar(criado, ("cartId", "id"))
        if not cart_id:
            continue
        carrinhos.append(cart_id)
        await d.chamar("addItemToCart", cartId=cart_id, itemId=item_id, quantity=1)
        await d.chamar("getCartDeliveryMethods", cartId=cart_id)
        await d.chamar("listPaymentMethods", cartId=cart_id)
    abertos = []
    for i, cart_id in enumerate(carrinhos):
        r = await d.chamar("getCart", rotulo=f"getCart carrinho {i + 1}", cartId=cart_id)
        abertos.append(r is not None)
    return {"lojas_tentadas": len(escolhidos), "carrinhos_criados": len(carrinhos),
            "getCart_ok_por_carrinho": abertos,
            "dois_carrinhos_abertos": len(carrinhos) == 2 and all(abertos)}


def _resumo(nomes: list[str], d: Diagnostico, carrinho: dict | None) -> dict:
    precos: dict[str, list[str]] = {}
    erros: dict[str, list[str]] = {}
    for tool, chamadas in d.registros.items():
        caminhos: set[str] = set()
        for c in chamadas:
            if c["ok"]:
                caminhos |= _caminhos_de_preco(c.get("resposta"))
            else:
                erros.setdefault(tool, []).append(c["erro"][:200])
        if caminhos:
            precos[tool] = sorted(caminhos)[:40]
    return {
        "total_tools": len(nomes),
        "tools": nomes,
        "faltando_vs_doc": [t for t in TOOLS_DA_DOC if t not in nomes],
        "sobrando_vs_doc": [t for t in nomes if t not in TOOLS_DA_DOC],
        "campos_de_preco_ou_taxa": precos,
        "erros": erros,
        "carrinho": carrinho,
    }


def _imprimir(resumo: dict, saida: Path) -> None:
    print("\n===== RESUMO =====")
    print(f"Tools no servidor: {resumo['total_tools']} (doc: {len(TOOLS_DA_DOC)})")
    print(f"Faltando vs. doc: {', '.join(resumo['faltando_vs_doc']) or 'nenhuma'}")
    print(f"Sobrando vs. doc: {', '.join(resumo['sobrando_vs_doc']) or 'nenhuma'}")
    print("Campos de preço/taxa:")
    for tool, caminhos in resumo["campos_de_preco_ou_taxa"].items():
        print(f"  {tool}: {', '.join(caminhos[:12])}{' …' if len(caminhos) > 12 else ''}")
    if resumo["erros"]:
        print("Erros:")
        for tool, msgs in resumo["erros"].items():
            print(f"  {tool}: {msgs[0][:150]}")
    if resumo["carrinho"] is not None:
        print(f"2 carrinhos abertos ao mesmo tempo? {resumo['carrinho']['dois_carrinhos_abertos']} "
              f"({resumo['carrinho']})")
    print(f"\nArquivos em {saida}. CONFIRA que não há dado pessoal antes de: git add docs/mcp-real")


async def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Diagnóstico do MCP real do iFood (só leitura; nunca submitOrder).")
    p.add_argument("--carrinho", action="store_true", help="também cria 2 carrinhos (sem enviar pedido)")
    p.add_argument("--demo", action="store_true", help="usa o servidor de demonstração (teste do diagnóstico)")
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO, help="pasta de saída (padrão docs/mcp-real)")
    args = p.parse_args(argv)
    cfg = replace(carregar(), ifood_mcp_modo="demo" if args.demo else "real")
    try:
        async with abrir_cliente(cfg) as cliente:
            resumo = await executar(cliente, args.saida, carrinho=args.carrinho)
    except ErroMCP as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    _imprimir(resumo, args.saida)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(asyncio.run(principal()))
