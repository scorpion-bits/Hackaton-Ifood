"""Interface única do cliente iFood. O agente e o servidor MCP só conhecem esta interface."""

from typing import Protocol


class ErroIFood(Exception):
    """Erro de negócio ou de API que deve ser explicado ao usuário (ex.: item sem estoque)."""


class NaoSuportado(ErroIFood):
    """A operação não existe no modo atual (ex.: não há API pública de pedido do lado do consumidor)."""


class ClienteIFood(Protocol):
    modo: str  # "mock" ou "real"
    fonte: str  # rótulo mostrado na tela: "demonstração" ou "iFood"

    def listar_lojas(self) -> list[dict]: ...

    def listar_itens(self, loja_id: str) -> list[dict]: ...

    def buscar_itens(self, termo: str, preco_max: float | None = None) -> list[dict]: ...

    def alterar_disponibilidade(self, loja_id: str, item_id: str, disponivel: bool) -> dict: ...

    def criar_promocao(self, loja_id: str, item_id: str, desconto_pct: float) -> dict: ...

    def criar_pedido(self, loja_id: str, itens: list[dict]) -> dict: ...
