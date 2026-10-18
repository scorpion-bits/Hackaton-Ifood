"""Diagnóstico do MCP real do iFood (contrato C10). Roda no PC da equipe, com o login já feito no app.

    Linux:   cd backend && .venv/bin/python -m app.ifood_mcp.diagnostico --carrinho [--lat -22.02 --lng -47.89]
    Windows: cd backend; .venv\\Scripts\\python.exe -m app.ifood_mcp.diagnostico --carrinho [--lat -22.02 --lng -47.89]

1. `list_tools` → `docs/mcp-real/tools.json` (nome, descrição, input/output schema).
2. Só leitura: `getUser`, `listAddresses`, `searchOffers` ("pizza", "sorvete", "hambúrguer" × ITEM/MERCHANT),
   `getMerchant` e `getItem` do 1º resultado, `getRecommendations` → `docs/mcp-real/<tool>.json`.
3. Com `--carrinho`: `createCart` em 2 lojas diferentes, `addItemToCart`, `getCartDeliveryMethods`,
   `listPaymentMethods`, `getCart`. **Nunca chama `submitOrder`** (nem `setCartPayment`/`setCartDelivery`).

Tudo é SANITIZADO antes de gravar, inclusive as mensagens de erro (regras na seção "sanitização": getUser
inteiro mascarado, listPaymentMethods por lista branca, endereço só bairro/cidade, chaves por pedaço do nome,
coordenadas com 2 casas). Confira getUser/listAddresses/listPaymentMethods/getCart antes do commit mesmo assim.
Os argumentos de cada tool saem do `input_schema` que o próprio servidor devolve no `list_tools`: se a tool pede
`userLocation`, vai `userLocation={"latitude": …, "longitude": …}` (o MCP real recusa latitude/longitude soltos);
`addressId` e os demais campos só vão se existirem no schema. A localização vem do endereço do `listAddresses`
(busca recursiva por latitude/lat e longitude/lng/lon) ou de `--lat/--lng` (prioridade).
`--demo` roda contra o servidor de demonstração (útil para testar o próprio diagnóstico, sem rede).
`--args-busca '{"campo": valor}'` (ou `campo=valor,campo2=valor`, ou `@arquivo.json`) mescla argumentos extras em cada
searchOffers (se as buscas vierem vazias).
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
# Tools cujo input_schema resumido aparece no resumo (para a equipe ver o que é obrigatório).
TOOLS_SCHEMA_NO_RESUMO = ("searchOffers", "getRecommendations", "getMerchant", "getItem", "createCart",
                          "addItemToCart")

# ---------- sanitização ----------
# Regras (chave normalizada = minúsculas, sem "_", "-" e espaço):
# - getUser: o arquivo inteiro é pessoal → todo valor vira "***" (a forma do JSON fica).
# - listPaymentMethods (e chaves paymentMethod*/card*): lista branca → só id/type/brand/method/status e
#   name/description (com o filtro de texto); todo o resto vira "***".
# - listAddresses (e chaves com "address"/"endereco"): só bairro/cidade/estado/país/ids ficam.
# - Em qualquer lugar: chaves que CONTÊM name/phone/mail/holder/digits/street/zip/postal/cpf/document/token/...
#   são mascaradas; location/coordinate/latitude/longitude são arredondadas a 2 casas (inclusive "lat,lng").
# - Chaves com pedaços de pessoa (user/customer/driver/owner/…) → objeto inteiro mascarado.
# - Texto livre: e-mail, CPF, CNPJ, CEP, telefone, JWT, Bearer, `token=…`, "final 1234"/"terminado em 1234",
#   bandeira + 4 dígitos, número de cartão (Luhn), "Rua X, 123", "apto 42", coordenadas (2 casas).
# - Textos pessoais vistos no getUser/listAddresses (nome, rua) são apagados de TODAS as amostras.
MASCARA = "***"
# Chaves sempre mascaradas (nome exato).
_SEMPRE = {
    "email", "emails", "phone", "phones", "cpf", "cnpj", "rg", "birthdate", "birthday", "last4", "bin",
    "cardnumber", "maskedcardnumber", "complement", "complemento", "cep", "reference", "referencia", "landmark",
    "pontodereferencia", "userid", "customerid", "accountid", "consumerid", "ip", "jwt", "nick", "alias",
    "expiration", "expirationdate", "expiry", "cvv", "apartment", "apartamento", "apto",
}
# Chaves mascaradas se CONTÊM um destes pedaços (inclui token/secret/authorization/cookie/session).
_PEDACOS_SENSIVEIS = (
    "name", "nome", "phone", "telefone", "celular", "mail", "holder", "digits", "street", "logradouro", "zip",
    "postal", "cpf", "cnpj", "document", "taxpayer", "recipient", "receiver", "refresh", "auth", "session",
    "cookie", "credential", "token", "secret", "password", "senha", "observation", "observacao", "comment",
    "instruction", "note", "birth", "contact", "contato", "complement", "house", "passport", "fiscal",
    "lastfour", "last4", "ultimos", "referencepoint", "referencia", "landmark",
)
# `name` puro é tratado pelo contexto (loja/item ficam; pessoa/pagamento seguem as regras do contexto).
_NOMES_SEGUROS = {
    "name", "merchantname", "itemname", "productname", "categoryname", "storename", "optionname", "groupname",
    "sectionname", "brandname", "tradename", "fantasyname", "offername", "dishname", "garnishname",
}
_PEDACOS_COORDENADA = ("location", "coordinate", "latitude", "longitude")
_COORDENADAS = {"lat", "lng", "lon", "long", "geo"}
# Objetos de pessoa: mascarados inteiros (nome exato ou pedaço do nome da chave).
_CONTEXTO_PESSOAL = {
    "user", "customer", "consumer", "account", "profile", "contact", "contacts", "owner", "buyer", "person",
    "me", "usuario", "cliente",
}
_PEDACOS_PESSOAIS = ("user", "customer", "consumer", "person", "profile", "owner", "buyer", "driver", "courier",
                     "usuario", "cliente", "pessoa", "comprador", "entregador")
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
_RE_CNPJ = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)|(?i:\bcnpj\W{0,3}\d{14}\b)")
_RE_CEP = re.compile(r"(?<!\d)\d{2}\.?\d{3}-\d{3}(?!\d)|(?i:\bcep\W{0,3}\d{5}-?\d{3}\b)")
_RE_JWT = re.compile(r"\beyJ[\w-]{5,}\.[\w-]{5,}\.[\w-]*")
_RE_BEARER = re.compile(r"(?i)bearer\s+[\w.~+/=-]{8,}")
_RE_SEGREDO_CHAVE = re.compile(
    r"(?i)\b(access_token|refresh_token|id_token|client_secret|code_verifier|token|secret|password|cookie)"
    r"(\W{1,3})[\w.~+/=-]{6,}")
_RE_CARTAO = re.compile(
    r"(?:[*•xX]{2,}[\s.-]*\d{4}\b)|(?i:\b(?:terminad[oa]|termina|final)\s*(?:em\s+)?\d{4}\b)")
_RE_BANDEIRA = re.compile(
    r"(?i)\b(visa|master(?:card)?|elo|amex|american express|hipercard|hiper|diners|discover|cabal|maestro)"
    r"\b([^\d\n]{0,12}?)\d{4}\b")
_RE_NUMERO_LONGO = re.compile(r"(?<![\w.])(?:\d[ -]?){12,18}\d(?![\w.])")
_RE_TELEFONE = re.compile(r"(?<![\w.])\+?(?:55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?![\w.])")
_RE_PAR_COORD = re.compile(r"(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})")
_RE_COORD_SOLTA = re.compile(r"(?<![\d.])-?\d{1,3}\.\d{5,}(?!\d)")
_RE_PAR_TEXTO = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
# Endereço em texto livre: tipo de logradouro (com maiúscula, para não pegar "comida de rua") + nome + NÚMERO
# (sem número não mascara, para "Forno da Praça Pizzaria" continuar legível; a rua do listAddresses é apagada
# pelo nome em todas as amostras, veja `textos_pessoais`).
_RE_LOGRADOURO = re.compile(
    r"\b(?:Rua|RUA|R\.|Avenida|AVENIDA|Av\.?|AV\.?|Alameda|Al\.|Travessa|Tv\.|Estrada|Rodovia|Rod\.|Praça|Praca"
    r"|Largo|Viela|Servidão|Street|St\.|Avenue|Ave\.)\s+[^,;\n()\d]{2,60}?\s*,?\s*(?:n[º°o]?\.?\s*)?\d{1,6}[A-Za-z]?\b")
_RE_COMPLEMENTO = re.compile(
    r"(?i)\b(?:apto?|apartamento|bloco|bl|conj(?:unto)?|lote|quadra|qd|torre)\.?\s*n?[º°]?\s*\d+[A-Za-z]?\b")


def _norm(chave: str) -> str:
    return re.sub(r"[_\-\s]", "", str(chave)).lower()


def _arredondar_par(m: re.Match) -> str:
    return f"{round(float(m.group(1)), 2)},{round(float(m.group(2)), 2)}"


def _luhn(digitos: str) -> bool:
    soma = 0
    for i, c in enumerate(reversed(digitos)):
        d = int(c) * (2 if i % 2 else 1)
        soma += d - 9 if d > 9 else d
    return soma % 10 == 0


def _numero_longo(m: re.Match) -> str:
    digitos = re.sub(r"\D", "", m.group(0))
    return MASCARA if _luhn(digitos) else m.group(0)  # número de cartão (Luhn); ids/epochs passam


def _limpar_texto(texto: str) -> str:
    texto = _RE_JWT.sub(MASCARA, texto)
    texto = _RE_BEARER.sub("Bearer " + MASCARA, texto)
    texto = _RE_SEGREDO_CHAVE.sub(lambda m: m.group(1) + m.group(2) + MASCARA, texto)
    texto = _RE_EMAIL.sub(MASCARA, texto)
    texto = _RE_PAR_COORD.sub(_arredondar_par, texto)
    texto = _RE_COORD_SOLTA.sub(lambda m: str(round(float(m.group(0)), 2)), texto)
    texto = _RE_CARTAO.sub(MASCARA, texto)
    texto = _RE_BANDEIRA.sub(lambda m: f"{m.group(1)}{m.group(2)}{MASCARA}", texto)
    texto = _RE_NUMERO_LONGO.sub(_numero_longo, texto)
    texto = _RE_CNPJ.sub(MASCARA, texto)
    texto = _RE_CEP.sub(MASCARA, texto)
    texto = _RE_CPF.sub(MASCARA, texto)
    texto = _RE_TELEFONE.sub(MASCARA, texto)
    texto = _RE_LOGRADOURO.sub(MASCARA, texto)
    return _RE_COMPLEMENTO.sub(MASCARA, texto)


def _float_de_coordenada(valor: Any) -> Any:
    """Float com mais de 4 casas (cara de coordenada) vira 2 casas; preço/taxa (2 casas) não muda."""
    if isinstance(valor, float) and abs(valor) <= 180:
        texto = repr(valor)
        if "e" not in texto and "." in texto and len(texto.split(".")[1]) > 4:
            return round(valor, 2)
    return valor


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


def _chave_pessoal(n: str) -> bool:
    return n in _CONTEXTO_PESSOAL or any(p in n for p in _PEDACOS_PESSOAIS)


def _chave_de_coordenada(n: str) -> bool:
    return n in _COORDENADAS or any(p in n for p in _PEDACOS_COORDENADA)


def _chave_de_endereco(n: str) -> bool:
    return ("address" in n or "endereco" in n) and not n.endswith(("id", "ids"))


def _chave_de_pagamento(n: str) -> bool:
    return "paymentmethod" in n or "wallet" in n or ("card" in n and "cardapio" not in n)


def _chave_de_id_ou_tempo(n: str) -> bool:
    return n == "id" or n.endswith(("id", "ids")) or any(p in n for p in _PEDACOS_TEMPO)


def _sanitizar_pagamento(dados: Any, chave_ok: bool = False) -> Any:
    """Lista branca: só tipo/bandeira/status/id e nome/descrição (com filtro de texto) passam."""
    if isinstance(dados, dict):
        saida = {}
        for chave, valor in dados.items():
            n = _norm(chave)
            if (n not in _TEXTO_PAGAMENTO and _chave_sensivel(n)) or _chave_pessoal(n) or _chave_de_endereco(n):
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
            if _chave_sensivel(n):
                saida[chave] = _mascarar(valor)
            elif _chave_de_coordenada(n):
                saida[chave] = _arredondar(valor)
            elif _chave_pessoal(n):
                saida[chave] = _mascarar(valor)
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
    return _float_de_coordenada(dados)


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


# ---------- textos pessoais já conhecidos (apagados de TODAS as amostras) ----------
_PALAVRAS_COMUNS = {"da", "de", "do", "das", "dos", "e", "the", "null", "none", "true", "false"}
_CHAVES_LOGRADOURO = ("street", "logradouro", "formatted", "full", "line", "location", "reference", "referencia",
                      "complement", "alias", "label", "description", "address", "endereco")


def textos_pessoais(dados: Any, tool: str) -> set[str]:
    """Textos pessoais vistos no getUser (nomes, e-mail, telefone, documento) e no listAddresses (rua,
    complemento, endereço formatado) para apagar onde mais aparecerem (ex.: "Entregar para Thales")."""
    achados: set[str] = set()

    def visitar(obj: Any, chave_pai: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                visitar(v, _norm(k))
        elif isinstance(obj, list):
            for v in obj:
                visitar(v, chave_pai)
        elif isinstance(obj, str) and obj.strip():
            valor = obj.strip()
            if tool == "getUser" and (_chave_sensivel(chave_pai) or _chave_pessoal(chave_pai)
                                      or "name" in chave_pai or "nome" in chave_pai):
                if len(valor) >= 4:
                    achados.add(valor)
                if "name" in chave_pai or "nome" in chave_pai:
                    achados.update(p for p in re.findall(r"[^\W\d_]{3,}", valor) if p.lower() not in _PALAVRAS_COMUNS)
            elif tool == "listAddresses" and any(p in chave_pai for p in _CHAVES_LOGRADOURO) \
                    and chave_pai not in _TEXTO_SEGURO_ENDERECO and not _chave_de_id_ou_tempo(chave_pai):
                if len(valor) >= 5:
                    achados.add(valor)
                primeiro = valor.split(",")[0].strip()
                if len(primeiro) >= 5:
                    achados.add(primeiro)

    visitar(dados)
    return achados


def apagar_textos(dados: Any, padrao: re.Pattern | None) -> Any:
    if padrao is None:
        return dados
    if isinstance(dados, dict):
        return {k: apagar_textos(v, padrao) for k, v in dados.items()}
    if isinstance(dados, list):
        return [apagar_textos(v, padrao) for v in dados]
    if isinstance(dados, str):
        return padrao.sub(MASCARA, dados)
    return dados


def padrao_de_textos(textos: set[str]) -> re.Pattern | None:
    if not textos:
        return None
    partes = sorted((re.escape(t) for t in textos), key=len, reverse=True)
    return re.compile(r"(?i)(?<!\w)(?:" + "|".join(partes) + r")(?!\w)")


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


# ---------- localização (do listAddresses ou de --lat/--lng) ----------
_CHAVES_LAT = ("latitude", "lat")
_CHAVES_LNG = ("longitude", "lng", "lon", "long")


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def coordenada_valida(lat: float | None, lng: float | None) -> bool:
    return (lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180
            and not (lat == 0 and lng == 0))


def achar_coordenadas(obj: Any) -> tuple[float, float] | None:
    """Primeiro par latitude/longitude numérico (busca em largura, qualquer nível: `coordinates`, `location`,
    `geo`…). Aceita número ou texto, "lat,lng" num campo de localização e GeoJSON `coordinates: [lng, lat]`."""
    fila = [obj]
    while fila:
        atual = fila.pop(0)
        if isinstance(atual, dict):
            normal = {_norm(k): v for k, v in atual.items()}
            lat = next((_numero(normal[c]) for c in _CHAVES_LAT if c in normal and _numero(normal[c]) is not None),
                       None)
            lng = next((_numero(normal[c]) for c in _CHAVES_LNG if c in normal and _numero(normal[c]) is not None),
                       None)
            if coordenada_valida(lat, lng):
                return lat, lng
            for n, v in normal.items():
                if isinstance(v, str) and _chave_de_coordenada(n) and (par := _RE_PAR_TEXTO.match(v)):
                    lat, lng = float(par.group(1)), float(par.group(2))
                    if coordenada_valida(lat, lng):
                        return lat, lng
                if n == "coordinates" and isinstance(v, list) and len(v) == 2:
                    lng, lat = _numero(v[0]), _numero(v[1])  # GeoJSON: [longitude, latitude]
                    if coordenada_valida(lat, lng):
                        return lat, lng
            fila.extend(v for v in atual.values() if isinstance(v, (dict, list)))
        elif isinstance(atual, list):
            fila.extend(atual)
    return None


def lista_de_enderecos(resposta: Any) -> list[dict]:
    """A lista de endereços do listAddresses, em qualquer nível (`addresses`, `data.addresses`, `results`…)."""
    fila = [resposta]
    while fila:
        atual = fila.pop(0)
        if isinstance(atual, dict):
            for k, v in atual.items():
                if "address" in _norm(k) and isinstance(v, list) and any(isinstance(e, dict) for e in v):
                    return [e for e in v if isinstance(e, dict)]
            fila.extend(v for v in atual.values() if isinstance(v, (dict, list)))
        elif isinstance(atual, list):
            dicts = [e for e in atual if isinstance(e, dict)]
            if dicts and any(achar_coordenadas(e) for e in dicts):
                return dicts
            fila.extend(atual)
    return _lista_resultados(resposta)


def escolher_endereco(resposta: Any) -> dict | None:
    """Endereço para a busca: o último usado que tenha coordenadas; senão o 1º com coordenadas; senão o 1º."""
    enderecos = lista_de_enderecos(resposta)
    com_coord = [e for e in enderecos if achar_coordenadas(e)]
    for e in com_coord:
        if _achar(e, ("isLastUsedAddress", "lastUsed", "isDefault", "default")) is True:
            return e
    if com_coord:
        return com_coord[0]
    return enderecos[0] if enderecos else None


# ---------- argumentos a partir do input_schema ----------
# Nome "nosso" → nomes aceitos no schema (o 1º que existir recebe o valor).
_APELIDOS = {"query": ("query", "term", "searchTerm", "q", "text", "keyword"),
             "limit": ("limit", "size", "pageSize")}


def _propriedades(schema: Any) -> dict | None:
    props = schema.get("properties") if isinstance(schema, dict) else None
    return props if isinstance(props, dict) and props else None


def _campos_de_local(props: dict) -> list[tuple[str, str, str]]:
    """Campos-objeto de localização do schema: (campo, nome da latitude, nome da longitude).
    `userLocation` sempre conta; outro objeto conta se as propriedades dele têm latitude e longitude."""
    campos = []
    for nome, sub in props.items():
        internas = _propriedades(sub) or {}
        lat = next((k for k in internas if _norm(k) in _CHAVES_LAT), None)
        lng = next((k for k in internas if _norm(k) in _CHAVES_LNG), None)
        if nome == "userLocation" or (lat and lng):
            campos.append((nome, lat or "latitude", lng or "longitude"))
    return campos


def resumo_schema(schema: Any) -> dict:
    """Obrigatórios/opcionais de um input_schema (e as propriedades de campos-objeto, ex.: userLocation)."""
    props = _propriedades(schema) or {}
    obrigatorios = [c for c in (schema.get("required") or [])] if isinstance(schema, dict) else []
    resumo: dict[str, Any] = {"obrigatorios": obrigatorios, "opcionais": [c for c in props if c not in obrigatorios]}
    objetos = {nome: {"obrigatorios": list(sub.get("required") or []), "propriedades": list(_propriedades(sub))}
               for nome, sub in props.items() if _propriedades(sub)}
    if objetos:
        resumo["objetos"] = objetos
    return resumo


def _texto_schema(resumo: dict) -> str:
    def campo(c: str) -> str:
        sub = resumo.get("objetos", {}).get(c)
        return f"{c}{{{', '.join(sub['propriedades'])}}}" if sub else c
    obrig = ", ".join(campo(c) for c in resumo["obrigatorios"]) or "nenhum"
    opc = ", ".join(campo(c) for c in resumo["opcionais"]) or "nenhum"
    return f"obrigatórios: {obrig} · opcionais: {opc}"


class Diagnostico:
    def __init__(self, cliente: ClienteIFood, saida: Path):
        self.cliente = cliente
        self.saida = saida
        self.schemas: dict[str, dict] = {}
        self.registros: dict[str, list[dict]] = {}
        self.local: tuple[float, float] | None = None  # valor real só em memória; nas amostras vai arredondado
        self.endereco_id: Any = None
        self.avisos: list[str] = []
        self._textos_pessoais: set[str] = set()
        self._padrao_pessoal: re.Pattern | None = None

    def aprender(self, tool: str, resposta: Any) -> None:
        """Guarda textos pessoais (getUser/listAddresses) para apagá-los de todas as outras amostras."""
        novos = textos_pessoais(resposta, tool)
        if novos - self._textos_pessoais:
            self._textos_pessoais |= novos
            self._padrao_pessoal = padrao_de_textos(self._textos_pessoais)

    def limpar(self, dados: Any) -> Any:
        return apagar_textos(dados, self._padrao_pessoal)

    def args_para(self, tool: str, candidatos: dict[str, Any], com_local: bool = False) -> dict[str, Any]:
        """Monta os argumentos pelo input_schema real. Só vai o que o schema tem; a localização vai como
        `userLocation` objeto (ou outro campo-objeto com latitude/longitude) se o schema pedir, senão como
        latitude/longitude soltos se o schema tiver esses campos. Sem schema: tudo + `userLocation`."""
        valores = {k: v for k, v in candidatos.items() if v is not None}
        props = _propriedades(self.schemas.get(tool))
        if props is None:  # list_tools falhou ou a tool não está lá: formato que o MCP real pede
            if com_local and self.local:
                valores["userLocation"] = {"latitude": self.local[0], "longitude": self.local[1]}
            if com_local and self.endereco_id is not None:
                valores.setdefault("addressId", self.endereco_id)
            return valores
        args: dict[str, Any] = {}
        for chave, valor in valores.items():
            alvo = next((n for n in _APELIDOS.get(chave, (chave,)) if n in props), None)
            if alvo:
                args[alvo] = valor
        if com_local:
            if "addressId" in props and self.endereco_id is not None:
                args["addressId"] = self.endereco_id
            if self.local:
                objetos = _campos_de_local(props)
                for campo, nome_lat, nome_lng in objetos:
                    args[campo] = {nome_lat: self.local[0], nome_lng: self.local[1]}
                if not objetos:
                    for nomes, valor in ((_CHAVES_LAT, self.local[0]), (_CHAVES_LNG, self.local[1])):
                        alvo = next((n for n in props if _norm(n) in nomes), None)
                        if alvo:
                            args[alvo] = valor
        return args

    def falta_local(self, tool: str) -> bool:
        """A tool exige localização (userLocation/latitude obrigatório) e não temos coordenadas."""
        schema = self.schemas.get(tool) or {}
        props = _propriedades(schema) or {}
        exigidos = set(schema.get("required") or []) if isinstance(schema, dict) else set()
        campos_local = {c for c, _, _ in _campos_de_local(props)} | {n for n in props if _norm(n) in _CHAVES_LAT}
        return self.local is None and bool(exigidos & campos_local)

    async def chamar(self, tool: str, rotulo: str | None = None, _extras: dict[str, Any] | None = None,
                     com_local: bool = False, **candidatos: Any) -> Any:
        if tool in PROIBIDAS:
            raise RuntimeError(f"O diagnóstico não chama {tool}.")
        rotulo = rotulo or tool
        if com_local and self.falta_local(tool):
            aviso = f"{rotulo}: pulada — exige localização e não achei latitude/longitude (use --lat e --lng)."
            if aviso not in self.avisos:
                self.avisos.append(aviso)
            print(f"  {rotulo:<40}   PULADA (sem localização: rode com --lat e --lng)")
            return None
        args = self.args_para(tool, candidatos, com_local) | (_extras or {})  # extras (--args-busca) vão como vieram
        resposta, ok, erro = await self._chamar_e_registrar(tool, rotulo, args)
        if not ok and com_local and self.local and "userlocation" in erro.lower() and "userLocation" not in args:
            # O schema não declarou userLocation, mas o servidor pediu: repete 1 vez no formato que ele exige.
            args = {k: v for k, v in args.items() if _norm(k) not in _CHAVES_LAT + _CHAVES_LNG}
            args["userLocation"] = {"latitude": self.local[0], "longitude": self.local[1]}
            resposta, ok, erro = await self._chamar_e_registrar(tool, f"{rotulo} (com userLocation)", args)
        return resposta

    async def _chamar_e_registrar(self, tool: str, rotulo: str, args: dict[str, Any]) -> tuple[Any, bool, str]:
        inicio = time.perf_counter()
        registro: dict[str, Any] = {"rotulo": rotulo, "args": sanitizar(args)}
        try:
            resposta = await self.cliente.chamar(tool, **args)
            if tool in ("getUser", "listAddresses"):
                self.aprender(tool, resposta)
            registro |= {"ok": True, "resposta": sanitizar(resposta, CONTEXTO_POR_TOOL.get(tool))}
        except ErroMCP as e:
            resposta = None
            registro |= {"ok": False, "erro": limpar_erro(str(e), CONTEXTO_POR_TOOL.get(tool))}
        registro = self.limpar(registro)
        registro["ms"] = int((time.perf_counter() - inicio) * 1000)
        self.registros.setdefault(tool, []).append(registro)
        if not registro["ok"]:
            estado = f"ERRO: {registro['erro'][:100]}"
        elif tool == "searchOffers" and not _lista_resultados(resposta):
            estado = "ok, mas VAZIO"
        else:
            estado = "ok"
        print(f"  {rotulo:<40} {registro['ms']:>6} ms  {estado}")
        return resposta, registro["ok"], registro.get("erro", "")

    def gravar(self) -> None:
        self.saida.mkdir(parents=True, exist_ok=True)
        for tool, chamadas in self.registros.items():
            (self.saida / f"{tool}.json").write_text(
                json.dumps({"tool": tool, "chamadas": chamadas}, ensure_ascii=False, indent=2), encoding="utf-8")


AVISO_BUSCA = ("searchOffers não trouxe nenhum resultado. Veja os campos obrigatórios no resumo (ou em "
               "docs/mcp-real/tools.json) e rode de novo com --args-busca '{\"campo\": valor}' "
               "(mesclado em cada busca) e/ou com --lat e --lng.")
AVISO_BUSCA_ERRO = ("Todas as searchOffers deram erro (veja \"Erros\" abaixo). Confira os campos obrigatórios no "
                    "resumo e rode de novo com --args-busca '{\"campo\": valor}' e/ou --lat e --lng.")
AVISO_SEM_LOCAL = ("Não achei latitude/longitude no listAddresses{detalhe}. Rode de novo com --lat e --lng "
                   "(ex.: --lat -22.02 --lng -47.89, centro de São Carlos).")
LEMBRETE = ("Antes do git add, abra getUser.json, listAddresses.json, listPaymentMethods.json e getCart.json "
            "e confira que não há dado pessoal.")


async def executar(cliente: ClienteIFood, saida: Path, carrinho: bool = False,
                   args_busca: dict[str, Any] | None = None,
                   local: tuple[float, float] | None = None) -> dict:
    """`local` (de --lat/--lng) tem prioridade sobre as coordenadas do listAddresses."""
    d = Diagnostico(cliente, saida)
    saida.mkdir(parents=True, exist_ok=True)
    avisos = d.avisos

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
    endereco = escolher_endereco(enderecos)
    d.endereco_id = _achar(endereco, ("addressId", "id")) if endereco else None
    if local is not None:
        d.local = local
        print("  localização: --lat/--lng da linha de comando")
    else:
        d.local = achar_coordenadas(endereco) if endereco else None
        if d.local:
            print(f"  localização: endereço do listAddresses (~{d.local[0]:.2f}, {d.local[1]:.2f})")
        else:
            detalhe = (f" (chaves do endereço: {', '.join(sorted(map(str, endereco)))})" if endereco
                       else " (nenhum endereço salvo na conta)")
            avisos.append(AVISO_SEM_LOCAL.format(detalhe=detalhe))
            print(f"  AVISO: {avisos[-1]}")

    itens: list[dict] = []
    lojas: list[dict] = []
    buscas_ok = buscas_feitas = 0
    for consulta in BUSCAS:
        for tipo in ("ITEM", "MERCHANT"):
            r = await d.chamar("searchOffers", rotulo=f"searchOffers {consulta} {tipo}", _extras=args_busca,
                               com_local=True, query=consulta, resultKind=tipo, limit=5)
            ultimo = (d.registros.get("searchOffers") or [{}])[-1]
            if str(ultimo.get("rotulo", "")).startswith(f"searchOffers {consulta} {tipo}"):
                buscas_feitas += 1
                buscas_ok += bool(ultimo.get("ok"))
            (itens if tipo == "ITEM" else lojas).extend(_lista_resultados(r))
    if not itens and not lojas and buscas_feitas:
        aviso = AVISO_BUSCA if buscas_ok else AVISO_BUSCA_ERRO
        avisos.append(aviso)
        print(f"  AVISO: {aviso}")

    primeiro = itens[0] if itens else None
    merchant_id = _achar(primeiro, ("merchantId",)) if primeiro else None
    merchant_id = merchant_id or (_achar(lojas[0], ("merchantId", "id")) if lojas else None)
    item_id = _achar(primeiro, ("itemId", "id")) if primeiro else None
    if merchant_id:
        await d.chamar("getMerchant", com_local=True, merchantId=merchant_id)
    if merchant_id and item_id:
        await d.chamar("getItem", com_local=True, merchantId=merchant_id, itemId=item_id)
    # contentMode é obrigatório no real (enum; sem ele: "contentMode value is not valid")
    await d.chamar("getRecommendations", com_local=True, contentMode="RECOMMENDED", limit=5)

    resultado_carrinho = None
    if carrinho:
        print("Carrinho (sem submitOrder):")
        resultado_carrinho = await _testar_carrinhos(d, itens)

    d.gravar()
    resumo = _resumo(nomes, d, resultado_carrinho) | {"avisos": avisos}
    resumo = d.limpar(resumo)
    (saida / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumo


async def _testar_carrinhos(d: Diagnostico, itens: list[dict]) -> dict:
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
        # o real exige items na criação mesmo sem marcar no `required` (MISSING_REQUIRED_FIELDS); args_para tira
        # o campo se o schema não o declarar
        itens_iniciais = [{"itemId": item_id, "quantity": 1}]
        criado = await d.chamar("createCart", com_local=True, merchantId=loja, items=itens_iniciais)
        cart_id = _achar(criado, ("cartId", "id"))
        if not cart_id:
            continue
        carrinhos.append(cart_id)
        await d.chamar("addItemToCart", cartId=cart_id, itemId=item_id, quantity=1)
        await d.chamar("getCartDeliveryMethods", cartId=cart_id)
        await d.chamar("listPaymentMethods", merchantId=loja, cartId=cart_id)  # real: só merchantId (obrigatório)
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
        "schemas": {t: resumo_schema(d.schemas[t]) for t in TOOLS_SCHEMA_NO_RESUMO if t in d.schemas},
        "localizacao_encontrada": d.local is not None,
        "campos_de_preco_ou_taxa": precos,
        "erros": erros,
        "carrinho": carrinho,
    }


def _desembrulhar(erro: BaseException) -> BaseException:
    while isinstance(erro, BaseExceptionGroup) and len(erro.exceptions) == 1:
        erro = erro.exceptions[0]
    return erro


def _valor_simples(texto: str) -> Any:
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def _json_objeto(texto: str) -> dict[str, Any]:
    """`--args-busca`: objeto JSON, `@arquivo.json` ou pares `chave=valor,chave2=valor2`.
    Os pares existem porque o PowerShell 5 come as aspas duplas do JSON (vira `{sortBy: relevance}`)."""
    texto = texto.strip()
    if texto.startswith("@"):
        try:
            texto = Path(texto[1:]).read_text(encoding="utf-8-sig").strip()
        except OSError as e:
            raise argparse.ArgumentTypeError(f"não consegui ler {texto[1:]} ({type(e).__name__})") from None
    try:
        valor = json.loads(texto)
    except ValueError as e:
        miolo = texto[1:-1] if texto.startswith("{") and texto.endswith("}") else texto
        pares = [p for p in miolo.split(",") if p.strip()]
        if pares and all(re.match(r"^\s*[\w.-]+\s*[:=]", p) for p in pares):
            return {re.split(r"[:=]", p, maxsplit=1)[0].strip().strip("'\""):
                    _valor_simples(re.split(r"[:=]", p, maxsplit=1)[1].strip().strip("'"))
                    for p in pares}
        raise argparse.ArgumentTypeError(
            f"JSON inválido ({e.msg}). Use '{{\"sortBy\": \"relevance\"}}', sortBy=relevance,limit=10 "
            "ou @arquivo.json") from None
    if not isinstance(valor, dict):
        raise argparse.ArgumentTypeError("--args-busca precisa ser um objeto JSON, ex.: '{\"x\": 1}'")
    return valor


def _imprimir(resumo: dict, saida: Path) -> None:
    print("\n===== RESUMO =====")
    print(f"Tools no servidor: {resumo['total_tools']} (doc: {len(TOOLS_DA_DOC)})")
    print(f"Faltando vs. doc: {', '.join(resumo['faltando_vs_doc']) or 'nenhuma'}")
    print(f"Sobrando vs. doc: {', '.join(resumo['sobrando_vs_doc']) or 'nenhuma'}")
    if resumo.get("schemas"):
        print("Argumentos (input_schema):")
        for tool, sch in resumo["schemas"].items():
            print(f"  {tool}: {_texto_schema(sch)}")
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
    p.add_argument("--lat", type=float, default=None, help="latitude para as buscas (prioridade sobre o endereço)")
    p.add_argument("--lng", type=float, default=None, help="longitude para as buscas (use junto com --lat)")
    args = p.parse_args(argv)
    if (args.lat is None) != (args.lng is None):
        p.error("use --lat e --lng juntos (ex.: --lat -22.02 --lng -47.89)")
    local = None
    if args.lat is not None:
        if not coordenada_valida(args.lat, args.lng):
            p.error("--lat precisa estar entre -90 e 90 e --lng entre -180 e 180")
        local = (args.lat, args.lng)
    try:
        cfg = replace(carregar(), ifood_mcp_modo="demo" if args.demo else "real")
        async with abrir_cliente(cfg) as cliente:
            resumo = await executar(cliente, args.saida, carrinho=args.carrinho, args_busca=args.args_busca,
                                    local=local)
    except Exception as bruto:  # inclusive ExceptionGroup do SDK; nada de traceback (pode ter dado pessoal)
        e = _desembrulhar(bruto)
        print(f"ERRO: {type(e).__name__}: {limpar_erro(str(e))}", file=sys.stderr)
        if "Conecte o iFood" in str(e):
            print("Abra o app (iniciar.bat / ./iniciar.sh com IFOOD_MCP_MODO=real no .env), clique em "
                  "Conectar iFood, faça o login e rode este comando de novo.", file=sys.stderr)
        return 1
    _imprimir(resumo, args.saida)
    return 0


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(asyncio.run(principal()))
