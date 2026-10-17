"""Acesso ao MCP do consumidor do iFood (modo demonstração em processo; modo real na etapa 03)."""

from .cliente import ChamadaRastro, ClienteIFood, ErroMCP, abrir_cliente, resumir
from .demo_server import criar_servidor_demo, resetar_demo

__all__ = [
    "ChamadaRastro",
    "ClienteIFood",
    "ErroMCP",
    "abrir_cliente",
    "criar_servidor_demo",
    "resetar_demo",
    "resumir",
]
