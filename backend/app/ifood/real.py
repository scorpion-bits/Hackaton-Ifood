"""Modo real: chama a Merchant API do iFood.

ATENÇÃO: o portal oficial (developer.ifood.com.br) bloqueou leitura automática durante a pesquisa.
Cada caminho abaixo tem um status. Antes de usar "NÃO VERIFICADO" na demo, confira no portal
e rode `python -m app.ifood.testar_real`. Detalhes e links: docs/ifood-apis.md.
"""

import time

import httpx

from ..config import Config
from .base import ErroIFood, NaoSuportado

ENDPOINTS = {
    # VERIFICADO (trecho da doc oficial): POST form-urlencoded com grantType, clientId, clientSecret.
    "token": "/authentication/v1.0/oauth/token",
    # NÃO VERIFICADO: caminho do módulo Merchant para listar lojas do token.
    "lojas": "/merchant/v1.0/merchants",
    # Sufixo VERIFICADO (/merchants/{merchantId}/catalogs/{catalogId}/categories); prefixo /catalog/v2.0 NÃO VERIFICADO.
    "catalogos": "/catalog/v2.0/merchants/{merchant_id}/catalogs",
    "categorias": "/catalog/v2.0/merchants/{merchant_id}/catalogs/{catalog_id}/categories",
}


class ClienteReal:
    modo = "real"
    fonte = "iFood"

    def __init__(self, cfg: Config, http: httpx.Client | None = None):
        if not cfg.ifood_client_id or not cfg.ifood_client_secret:
            raise ErroIFood("IFOOD_MODE=real exige IFOOD_CLIENT_ID e IFOOD_CLIENT_SECRET no .env.")
        self.cfg = cfg
        self.http = http or httpx.Client(base_url=cfg.ifood_base_url, timeout=15)
        self._token: str | None = None
        self._expira_em = 0.0

    # --- autenticação (fluxo centralizado, client_credentials) ---
    def _autenticar(self) -> str:
        if self._token and time.time() < self._expira_em - 60:
            return self._token
        r = self.http.post(
            ENDPOINTS["token"],
            data={
                "grantType": "client_credentials",
                "clientId": self.cfg.ifood_client_id,
                "clientSecret": self.cfg.ifood_client_secret,
            },
        )
        self._checar(r)
        corpo = r.json()
        self._token = corpo.get("accessToken") or corpo.get("access_token")
        self._expira_em = time.time() + float(corpo.get("expiresIn") or corpo.get("expires_in") or 21600)
        if not self._token:
            raise ErroIFood(f"Resposta de token sem accessToken: chaves {list(corpo)}")
        return self._token

    def _get(self, caminho: str) -> dict | list:
        r = self.http.get(caminho, headers={"Authorization": f"Bearer {self._autenticar()}"})
        self._checar(r)
        return r.json()

    @staticmethod
    def _checar(r: httpx.Response) -> None:
        if r.status_code == 429:
            raise ErroIFood("Limite de requisições do iFood atingido (HTTP 429). Tente de novo em instantes.")
        if r.status_code >= 400:
            raise ErroIFood(f"iFood respondeu HTTP {r.status_code}: {r.text[:300]}")

    # --- interface ---
    def listar_lojas(self) -> list[dict]:
        lojas = self._get(ENDPOINTS["lojas"])
        return [{"id": l.get("id"), "nome": l.get("name"), "fonte": self.fonte} for l in lojas]

    def listar_itens(self, loja_id: str) -> list[dict]:
        itens = []
        for catalogo in self._get(ENDPOINTS["catalogos"].format(merchant_id=loja_id)):
            catalog_id = catalogo.get("catalogId") or catalogo.get("id")
            caminho = ENDPOINTS["categorias"].format(merchant_id=loja_id, catalog_id=catalog_id)
            for categoria in self._get(caminho):
                for item in categoria.get("items", []):
                    preco = item.get("price") or {}
                    itens.append({
                        "id": item.get("id"), "loja_id": loja_id, "categoria": categoria.get("name"),
                        "nome": item.get("name"), "descricao": item.get("description", ""),
                        "preco": preco.get("value"), "disponivel": item.get("status") == "AVAILABLE",
                        "estoque": None, "fonte": self.fonte,
                    })
        return itens

    def buscar_itens(self, termo: str, preco_max: float | None = None) -> list[dict]:
        termo = termo.lower().strip()
        achados = []
        for loja in self.listar_lojas():
            for item in self.listar_itens(loja["id"]):
                if termo in (item["nome"] or "").lower() or termo in (item["categoria"] or "").lower():
                    if preco_max is None or (item["preco"] is not None and item["preco"] <= preco_max):
                        achados.append(item | {"loja_nome": loja["nome"]})
        return sorted(achados, key=lambda i: i["preco"] or 0)

    def alterar_disponibilidade(self, loja_id: str, item_id: str, disponivel: bool) -> dict:
        raise NaoSuportado(
            "Alterar status de item no iFood real ainda não foi ligado: a doc cita PATCH .../items/status e "
            ".../item/status (divergência) e o corpo não foi verificado. Ver docs/ifood-apis.md."
        )

    def criar_promocao(self, loja_id: str, item_id: str, desconto_pct: float) -> dict:
        raise NaoSuportado(
            "O módulo Promotion do iFood é restrito a parceiros de mercado (grocery) segundo a doc oficial. "
            "Ver docs/ifood-apis.md."
        )

    def criar_pedido(self, loja_id: str, itens: list[dict]) -> dict:
        raise NaoSuportado(
            "Não encontramos API pública do iFood para o CONSUMIDOR criar pedidos. "
            "Pedidos reais só existem no modo demonstração."
        )
