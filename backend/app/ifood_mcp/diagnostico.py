"""Diagnóstico do MCP real do iFood (contrato C10). Roda no PC da equipe, com o login já feito no app.

    Linux:   cd backend && .venv/bin/python -m app.ifood_mcp.diagnostico [--carrinho]
    Windows: cd backend; .venv\\Scripts\\python -m app.ifood_mcp.diagnostico [--carrinho]

1. `list_tools` → `docs/mcp-real/tools.json` (nome, descrição, input/output schema).
2. Só leitura: `getUser`, `listAddresses`, `searchOffers` ("pizza", "sorvete", "hambúrguer" × ITEM/MERCHANT),
   `getMerchant` e `getItem` do 1º resultado, `getRecommendations` → `docs/mcp-real/<tool>.json`.
3. Com `--carrinho`: `createCart` em 2 lojas diferentes, `addItemToCart`, `getCartDeliveryMethods`,
   `listPaymentMethods`, `getCart`. **Nunca chama `submitOrder`** (nem `setCartPayment`/`setCartDelivery`).

Tudo é SANITIZADO antes de gravar, inclusive as mensagens de erro (regras na seção "sanitização": getUser
inteiro mascarado, listPaymentMethods por lista branca, endereço só bairro/cidade, chaves por pedaço do nome,
coordenadas com 2 casas). Confira getUser/listAddresses/listPaymentMethods/getCart antes do commit mesmo assim.
`--demo` roda contra o servidor de demonstração (útil para testar o próprio diagnóstico, sem rede).
`--args-busca '{"campo": valor}'` mescla argumentos extras em cada searchOffers (se todas as buscas vierem vazias).
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
# Regras (chave normalizada = minúsculas, sem "_", "-" e espaço):
# - getUser: o arquivo inteiro é pessoal → todo valor vira "***" (a forma do JSON fica).
# - listPaymentMethods (e chaves paymentMethod*/card*): lista branca → só id/type/brand/method/status e
#   name/description (com o filtro de texto); todo o resto vira "***".
# - listAddresses (e chaves com "address"/"endereco"): só bairro/cidade/estado/país/ids ficam.
# - Em qualquer lugar: chaves que CONTÊM name/phone/mail/holder/digits/street/zip/postal/cpf/document/token/...
#   são mascaradas; location/coordinate/latitude/longitude são arredondadas a 2 casas (inclusive "lat,lng").
# - Texto livre: e-mail, CPF, telefone, JWT, Bearer, "final 1234"/"terminado em 1234", coordenadas.
MASCARA = "***"
# Chaves sempre mascaradas (nome exato).
_SEMPRE = {
    "email", "emails", "phone", "phones", "cpf", "cnpj", "birthdate", "birthday", "last4", "bin",
    "cardnumber", "maskedcardnumber", "complement", "cep", "reference", "landmark", "userid", "customerid",
    "accountid", "consumerid", "ip", "jwt", "nick", "alias", "expiration", "expirationdate", "expiry", "cvv",
}
# Chaves mascaradas se CONTÊM um destes pedaços.
_PEDACOS_SENSIVEIS = (
    "name", "nome", "phone", "telefone", "celular", "mail", "holder", "digits", "street", "logradouro", "zip",
    "postal", "cpf", "cnpj", "document", "taxpayer", "recipient", "receiver", "refresh", "auth", "session",
    "credential", "token", "secret", "password", "senha", "observation", "observacao", "comment", "instruction",
    "note", "birth", "contact", "contato",
)
# `name` puro é tratado pelo contexto (loja/item ficam; pessoa/pagamento seguem as regras do contexto).
_NOMES_SEGUROS = {
    "name", "merchantname", "itemname", "productname", "categoryname", "storename", "optionname", "groupname",
    "sectionname", "brandname", "tradename", "fantasyname", "offername", "dishname", "garnishname",
}
_PEDACOS_COORDENADA = ("location", "coordinate", "latitude", "longitude")
_COORDENADAS = {"lat", "lng", "lon", "long", "geo"}
_CONTEXTO_PESSOAL = {
    "user", "customer", "consumer", "account", "profile", "contact", "contacts", "owner", "buyer", "person",
    "me", "usuario", "cliente",
}
_TEXTO_SEGURO_ENDERECO = {
    "neighborhood", "district", "city", "cityname", "state", "statecode", "uf", "country", "countrycode",
    "bairro", "cidade", "estado", "id", "addressid", "candidateid", "type", "kind", "category", "status",
}
_LISTA_BRANCA_PAGAMENTO = {"id", "type", "brand", "method", "status"}
_TEXTO_PAGAMENTO = {"name", "description"}
_SEM_CONTEXTO = {"agenthints", "hints", "_meta", "meta"}  # dicas do agente: texto técnico, fica legível
_PEDACOS_TEMPO = ("timestamp", "epoch", "createdat", "updatedat", "expiresat", "time", "date")
# Contexto da resposta inteira, por tool.
CONTEXTO_POR_TOOL = {
    "getUser": "pessoal", "listAddresses": "endereco", "createAddress": "endereco",
    "listPaymentMethods": "pagamento",
}

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_RE_CPF = re.compile(r"(?<!\d)\d{3}[.\s-]?\d{3}[.\s-]?\d{3}[.\s-]?\d{2}(?!\d)")
_RE_JWT = re.compile(r"\beyJ[\w-]{5,}\.[\w-]{5,}\.[\w-]*")
_RE_BEARER = re.compile(r"(?i)bearer\s+[\w.~+/=-]{8,}")
_RE_CARTAO = re.compile(
    r"(?:[*•xX]{2,}[\s.-]*\d{4}\b)|(?i:\b(?:terminad[oa]|termina|final)\s*(?:em\s+)?\d{4}\b)")
_RE_TELEFONE = re.compile(r"(?<![\w.])\+?(?:55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?![\w.])")
_RE_PAR_COORD = re.compile(r"(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})")
_RE_PAR_TEXTO = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def _norm(chave: str) -> str:
    return re.sub(r"[_\-\s]", "", str(chave)).lower()


def _arredondar_par(m: re.Match) -> str:
    return f"{round(float(m.group(1)), 2)},{round(float(m.group(2)), 2)}"


def _limpar_texto(texto: str) -> str:
    texto = _RE_JWT.sub(MASCARA, texto)
    texto = _RE_BEARER.sub("Bearer " + MASCARA, texto)
    texto = _RE_EMAIL.sub(MASCARA, texto)
    texto = _RE_PAR_COORD.sub(_arredondar_par, texto)
    texto = _RE_CARTAO.sub(MASCARA, texto)
    texto = _RE_CPF.sub(MASCARA, texto)
    return _RE_TELEFONE.sub(MASCARA, texto)


def _arredondar(valor: Any) -> Any:
    if valor is None or isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)
    if isinstance(valor, str):
        try:
            return round(float(valor), 2)
        except ValueError:
            par = _RE_PAR_TEXTO.match(valor)
            return _arredondar_par(par) if par else MASCARA
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


def _chave_sensivel(n: str) -> bool:
    if n in _SEMPRE:
        return True
    if n in _NOMES_SEGUROS:
        return False
    return any(p in n for p in _PEDACOS_SENSIVEIS)


def _chave_de_coordenada(n: str) -> bool:
    return n in _COORDENADAS or any(p in n for p in _PEDACOS_COORDENADA)


def _chave_de_endereco(n: str) -> bool:
    return ("address" in n or "endereco" in n) and not n.endswith(("id", "ids"))


def _chave_de_pagamento(n: str) -> bool:
    return "paymentmethod" in n or "wallet" in n or (n.startswith(("card", "creditcard")) and "cardapio" not in n)


def _chave_de_id_ou_tempo(n: str) -> bool:
    return n == "id" or n.endswith(("id", "ids")) or any(p in n for p in _PEDACOS_TEMPO)


def _sanitizar_pagamento(dados: Any, chave_ok: bool = False) -> Any:
    """Lista branca: só tipo/bandeira/status/id e nome/descrição (com filtro de texto) passam."""
    if isinstance(dados, dict):
        saida = {}
        for chave, valor in dados.items():
            n = _norm(chave)
            if (n not in _TEXTO_PAGAMENTO and _chave_sensivel(n)) or n in _CONTEXTO_PESSOAL \
                    or _chave_de_endereco(n):
                saida[chave] = _mascarar(valor)
            else:
                saida[chave] = _sanitizar_pagamento(valor, n in _LISTA_BRANCA_PAGAMENTO or n in _TEXTO_PAGAMENTO)
        return saida
    if isinstance(dados, list):
        return [_sanitizar_pagamento(v, chave_ok) for v in dados]
    if dados is None or isinstance(dados, bool):
        return dados
    if not chave_ok:
        return MASCARA
    return _limpar_texto(dados) if isinstance(dados, str) else dados


def sanitizar(dados: Any, contexto: str | None = None) -> Any:
    """Cópia sem dados pessoais. `contexto`: None, "pessoal" (tudo mascarado), "endereco" (só bairro/cidade/ids)
    ou "pagamento" (lista branca)."""
    if contexto == "pessoal":
        return _mascarar(dados)
    if contexto == "pagamento":
        return _sanitizar_pagamento(dados)
    if isinstance(dados, dict):
        saida = {}
        for chave, valor in dados.items():
            n = _norm(chave)
            if _chave_sensivel(n) or n in _CONTEXTO_PESSOAL:
                saida[chave] = _mascarar(valor)
            elif _chave_de_coordenada(n):
                saida[chave] = _arredondar(valor)
            elif n in _SEM_CONTEXTO:
                saida[chave] = sanitizar(valor, None)
            elif _chave_de_pagamento(n):
                saida[chave] = _sanitizar_pagamento(valor)
            elif _chave_de_endereco(n) or contexto == "endereco":
                if isinstance(valor, (dict, list)):
                    saida[chave] = sanitizar(valor, "endereco")
                elif contexto == "endereco" and (n in _TEXTO_SEGURO_ENDERECO or n.endswith("id")):
                    saida[chave] = _limpar_texto(valor) if isinstance(valor, str) else valor
                else:
                    saida[chave] = _mascarar(valor)
            elif isinstance(valor, str) and _chave_de_id_ou_tempo(n) and re.fullmatch(r"\d+", valor):
                saida[chave] = valor  # id/epoch só de dígitos não é telefone nem CPF
            else:
                saida[chave] = sanitizar(valor, contexto)
        return saida
    if isinstance(dados, list):
        return [sanitizar(v, contexto) for v in dados]
    if isinstance(dados, str):
        return MASCARA if contexto == "endereco" else _limpar_texto(dados)
    if contexto == "endereco" and isinstance(dados, (int, float)) and not isinstance(dados, bool):
        return MASCARA
    return dados


def limpar_erro(mensagem: str, contexto: str | None = None) -> str:
    """Mensagem de erro com a mesma limpeza: JSON embutido passa por `sanitizar`, o texto pelo filtro."""
    mensagem = str(mensagem)
    inicio, fim = mensagem.find("{"), mensagem.rfind("}")
    if 0 <= inicio < fim:
        try:
            embutido = json.loads(mensagem[inicio:fim + 1])
        except ValueError:
            pass
        else:
            limpo = json.dumps(sanitizar(embutido, contexto), ensure_ascii=False)
            mensagem = mensagem[:inicio] + limpo + mensagem[fim + 1:]
    return _limpar_texto(mensagem)


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

    async def chamar(self, tool: str, rotulo: str | None = None, _extras: dict[str, Any] | None = None,
                     **candidatos: Any) -> Any:
        if tool in PROIBIDAS:
            raise RuntimeError(f"O diagnóstico não chama {tool}.")
        args = self.args_para(tool, candidatos) | (_extras or {})  # extras (--args-busca) vão como vieram
        inicio = time.perf_counter()
        registro: dict[str, Any] = {"rotulo": rotulo or tool, "args": sanitizar(args)}
        try:
            resposta = await self.cliente.chamar(tool, **args)
            registro |= {"ok": True, "resposta": sanitizar(resposta, CONTEXTO_POR_TOOL.get(tool))}
        except ErroMCP as e:
            resposta = None
            registro |= {"ok": False, "erro": limpar_erro(str(e), CONTEXTO_POR_TOOL.get(tool))}
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


AVISO_BUSCA = "searchOffers sem resultado: confira o input_schema em docs/mcp-real/tools.json"
LEMBRETE = ("Antes do git add, abra getUser.json, listAddresses.json, listPaymentMethods.json e getCart.json "
            "e confira que não há dado pessoal.")


async def executar(cliente: ClienteIFood, saida: Path, carrinho: bool = False,
                   args_busca: dict[str, Any] | None = None) -> dict:
    d = Diagnostico(cliente, saida)
    saida.mkdir(parents=True, exist_ok=True)
    avisos: list[str] = []

    print("list_tools…")
    try:
        tools = await cliente.listar_tools()
    except Exception as e:  # segue sem schemas (os argumentos vão sem filtro)
        tools = []
        avisos.append(f"list_tools falhou ({type(_desembrulhar(e)).__name__}): {limpar_erro(str(_desembrulhar(e)))}")
        print(f"  ERRO: {avisos[-1][:150]}")
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
            r = await d.chamar("searchOffers", rotulo=f"searchOffers {consulta} {tipo}", _extras=args_busca,
                               query=consulta, resultKind=tipo, limit=5, **geo)
            (itens if tipo == "ITEM" else lojas).extend(_lista_resultados(r))
    if not itens and not lojas:
        avisos.append(AVISO_BUSCA)
        print(f"  AVISO: {AVISO_BUSCA} (e tente --args-busca '{{...}}')")

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
    resumo = _resumo(nomes, d, resultado_carrinho) | {"avisos": avisos}
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


def _desembrulhar(erro: BaseException) -> BaseException:
    while isinstance(erro, BaseExceptionGroup) and len(erro.exceptions) == 1:
        erro = erro.exceptions[0]
    return erro


def _json_objeto(texto: str) -> dict[str, Any]:
    try:
        valor = json.loads(texto)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"JSON inválido ({e.msg}). Ex.: '{{\"sortBy\": \"RELEVANCE\"}}'") from None
    if not isinstance(valor, dict):
        raise argparse.ArgumentTypeError("--args-busca precisa ser um objeto JSON, ex.: '{\"x\": 1}'")
    return valor


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
    for aviso in resumo.get("avisos", []):
        print(f"AVISO: {aviso}")
    if resumo["carrinho"] is not None:
        print(f"2 carrinhos abertos ao mesmo tempo? {resumo['carrinho']['dois_carrinhos_abertos']} "
              f"({resumo['carrinho']})")
    print(f"\nArquivos em {saida}.")
    print(LEMBRETE)


async def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Diagnóstico do MCP real do iFood (só leitura; nunca submitOrder).")
    p.add_argument("--carrinho", action="store_true", help="também cria 2 carrinhos (sem enviar pedido)")
    p.add_argument("--demo", action="store_true", help="usa o servidor de demonstração (teste do diagnóstico)")
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO, help="pasta de saída (padrão docs/mcp-real)")
    p.add_argument("--args-busca", type=_json_objeto, default=None, metavar="JSON",
                   help="argumentos extras (objeto JSON) mesclados em cada searchOffers")
    args = p.parse_args(argv)
    try:
        cfg = replace(carregar(), ifood_mcp_modo="demo" if args.demo else "real")
        async with abrir_cliente(cfg) as cliente:
            resumo = await executar(cliente, args.saida, carrinho=args.carrinho, args_busca=args.args_busca)
    except Exception as bruto:  # inclusive ExceptionGroup do SDK; nada de traceback (pode ter dado pessoal)
        e = _desembrulhar(bruto)
        print(f"ERRO: {type(e).__name__}: {limpar_erro(str(e))}", file=sys.stderr)
        return 1
    _imprimir(resumo, args.saida)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(asyncio.run(principal()))
