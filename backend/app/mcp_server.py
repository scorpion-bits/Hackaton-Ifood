"""Servidor MCP com ferramentas dos dois lados do comércio com agentes.

- vendedor_*  : agente do lojista/restaurante (cardápio, disponibilidade, promoções).
- comprador_* : agente do cliente (lojas, busca, montar pedido).

Ferramentas que mexem com dinheiro, preço ou pedido só criam uma AÇÃO PENDENTE; a pessoa confirma na tela.
Rodar sozinho (Claude Desktop / MCP Inspector): `python mcp_stdio.py` dentro de backend/.
"""

import functools

from pydantic import BaseModel, Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import acoes
from .ifood import ErroIFood, obter_cliente

# Teto de desconto do módulo Promotion do iFood (doc oficial, ver docs/ifood-apis.md).
DESCONTO_MAX_PCT = 70

LEITURA = ToolAnnotations(read_only_hint=True)
PROPOSTA = ToolAnnotations(read_only_hint=False, destructive_hint=False)

INSTRUCOES = (
    "Ferramentas de comércio com agentes sobre o iFood. Leituras são livres. Toda ferramenta 'propor_*' "
    "apenas cria uma ação pendente: explique o motivo, mostre o resumo e peça confirmação humana. "
    "Nunca diga que algo foi executado antes da confirmação."
)


def _erros_legiveis(fn):
    """Erros de negócio viram ToolError: o MCP repassa a mensagem ao modelo, que explica à pessoa."""

    @functools.wraps(fn)
    def envolvida(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ErroIFood as e:
            raise ToolError(str(e)) from e

    return envolvida


class ItemPedido(BaseModel):
    item_id: str = Field(description="id do item no cardápio")
    quantidade: int = Field(ge=1, le=20)


def criar_servidor() -> MCPServer:
    mcp = MCPServer("comercio-agentes-ifood", instructions=INSTRUCOES)

    # ---------- lado VENDEDOR (lojista / restaurante) ----------
    @mcp.tool(annotations=LEITURA)
    @_erros_legiveis
    def vendedor_listar_cardapio(loja_id: str) -> dict:
        """Lista o cardápio da loja (itens, preço, disponibilidade, estoque)."""
        cli = obter_cliente()
        return {"fonte": cli.fonte, "itens": cli.listar_itens(loja_id)}

    @mcp.tool(annotations=PROPOSTA)
    @_erros_legiveis
    def vendedor_propor_disponibilidade(loja_id: str, item_id: str, disponivel: bool, motivo: str) -> dict:
        """Propõe pausar (disponivel=false) ou reativar um item. Exige confirmação humana."""
        item = _item(loja_id, item_id)
        verbo = "Reativar" if disponivel else "Pausar"
        return acoes.propor(
            "alterar_disponibilidade", f"{verbo} '{item['nome']}'", motivo,
            {"loja_id": loja_id, "item_id": item_id, "disponivel": disponivel},
        )

    @mcp.tool(annotations=PROPOSTA)
    @_erros_legiveis
    def vendedor_propor_promocao(loja_id: str, item_id: str, desconto_pct: float, motivo: str) -> dict:
        """Propõe um desconto percentual em um item (máx. 70%). Exige confirmação humana."""
        if not 1 <= desconto_pct <= DESCONTO_MAX_PCT:
            raise ErroIFood(f"Desconto deve ficar entre 1% e {DESCONTO_MAX_PCT}% (limite da API do iFood).")
        item = _item(loja_id, item_id)
        novo = round(item["preco"] * (1 - desconto_pct / 100), 2)
        return acoes.propor(
            "criar_promocao", f"{desconto_pct:g}% em '{item['nome']}': {brl(item['preco'])} → {brl(novo)}", motivo,
            {"loja_id": loja_id, "item_id": item_id, "desconto_pct": desconto_pct},
        )

    # ---------- lado COMPRADOR (cliente) ----------
    @mcp.tool(annotations=LEITURA)
    @_erros_legiveis
    def comprador_listar_lojas() -> dict:
        """Lista as lojas disponíveis com nota, tempo e taxa de entrega."""
        cli = obter_cliente()
        return {"fonte": cli.fonte, "lojas": cli.listar_lojas()}

    @mcp.tool(annotations=LEITURA)
    @_erros_legiveis
    def comprador_buscar_itens(termo: str, preco_max: float | None = None) -> dict:
        """Busca itens por nome ou categoria em todas as lojas, do mais barato ao mais caro."""
        cli = obter_cliente()
        return {"fonte": cli.fonte, "itens": cli.buscar_itens(termo, preco_max)}

    @mcp.tool(annotations=PROPOSTA)
    @_erros_legiveis
    def comprador_propor_pedido(
        loja_id: str, itens: list[ItemPedido], motivo: str, orcamento_max: float | None = None
    ) -> dict:
        """Monta um pedido e checa estoque e orçamento. Exige confirmação humana antes de comprar."""
        cardapio = {i["id"]: i for i in obter_cliente().listar_itens(loja_id)}
        loja = next((l for l in obter_cliente().listar_lojas() if l["id"] == loja_id), {})
        total, linhas = float(loja.get("taxa_entrega") or 0), []
        for pedido_item in itens:
            item = cardapio.get(pedido_item.item_id)
            if not item:
                raise ErroIFood(f"Item {pedido_item.item_id!r} não existe na loja {loja_id!r}.")
            if not item["disponivel"] or (item["estoque"] is not None and item["estoque"] < pedido_item.quantidade):
                raise ErroIFood(f"'{item['nome']}' indisponível ou sem estoque suficiente.")
            total += item["preco"] * pedido_item.quantidade
            linhas.append(f"{pedido_item.quantidade}x {item['nome']}")
        total = round(total, 2)
        if orcamento_max is not None and total > orcamento_max:
            raise ErroIFood(f"Total {brl(total)} passa do orçamento de {brl(orcamento_max)}.")
        return acoes.propor(
            "criar_pedido", f"Pedido em {loja.get('nome', loja_id)}: {', '.join(linhas)} — total {brl(total)}",
            motivo, {"loja_id": loja_id, "itens": [i.model_dump() for i in itens], "total_estimado": total},
        )

    # ---------- comum ----------
    @mcp.tool(annotations=LEITURA)
    @_erros_legiveis
    def consultar_acao(acao_id: str) -> dict:
        """Consulta se uma ação proposta foi confirmada, recusada ou executada."""
        return acoes.obter(acao_id)

    return mcp


def brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _item(loja_id: str, item_id: str) -> dict:
    item = next((i for i in obter_cliente().listar_itens(loja_id) if i["id"] == item_id), None)
    if not item:
        raise ErroIFood(f"Item {item_id!r} não encontrado na loja {loja_id!r}.")
    return item
