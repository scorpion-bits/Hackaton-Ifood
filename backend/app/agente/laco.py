"""Laço do agente: modelo → ferramenta MCP → cliente iFood → resposta.

O agente fala com as ferramentas via protocolo MCP (cliente MCP em processo, sem subprocesso),
o mesmo servidor que o Claude Desktop ou o MCP Inspector usam por stdio.
"""

import json

from mcp import Client

from .. import config
from ..mcp_server import criar_servidor
from .provedores import Ferramenta, Resultado, criar_conversa

MAX_PASSOS = 6

SISTEMA = {
    "vendedor": (
        "Você é o agente de vendas do lojista da loja {loja_id} no iFood. Ajude a cuidar do cardápio, "
        "disponibilidade e promoções."
    ),
    "comprador": (
        "Você é o agente de compras de um cliente do iFood. Ajude a encontrar, comparar e montar pedidos "
        "dentro do orçamento."
    ),
}
REGRAS = (
    " Regras: responda em português, curto e direto. Sempre diga POR QUE escolheu algo. "
    "Respeite preço, estoque e orçamento. Ações com dinheiro, preço ou pedido: use a ferramenta 'propor_*', "
    "que só cria uma proposta, e peça para a pessoa confirmar no cartão da tela. Nunca diga que algo foi "
    "executado antes da confirmação. Se os dados vierem com fonte 'demonstração', não os trate como reais."
)


def _permitida(nome: str, lado: str) -> bool:
    return not nome.startswith(("vendedor_", "comprador_")) or nome.startswith(f"{lado}_")


async def responder(mensagem: str, lado: str = "comprador", historico: list[dict] | None = None,
                    loja_id: str = "loja-demo-1") -> dict:
    cfg = config.carregar()
    sistema = SISTEMA[lado].format(loja_id=loja_id) + REGRAS
    passos: list[dict] = []
    acoes: list[dict] = []

    async with Client(criar_servidor()) as mcp:
        ferramentas = [
            Ferramenta(t.name, t.description or "", t.input_schema)
            for t in (await mcp.list_tools()).tools if _permitida(t.name, lado)
        ]
        conversa = criar_conversa(cfg, sistema, historico or [], mensagem, ferramentas,
                                  {"lado": lado, "loja_id": loja_id})

        for _ in range(MAX_PASSOS):
            passo = await conversa.passo()
            if not passo.chamadas:
                return _resposta(passo.texto, passos, acoes, cfg)
            resultados = []
            for ch in passo.chamadas:
                if not _permitida(ch.nome, lado):
                    texto, erro = f"Ferramenta {ch.nome} não pertence ao lado '{lado}'.", True
                else:
                    r = await mcp.call_tool(ch.nome, ch.args)
                    texto = "\n".join(getattr(c, "text", "") for c in r.content)
                    erro = bool(r.is_error)
                passos.append({"ferramenta": ch.nome, "argumentos": ch.args, "ok": not erro, "resultado": texto[:400]})
                if not erro:
                    dados = _json(texto)
                    if isinstance(dados, dict) and dados.get("status") == "pendente":
                        acoes.append(dados)
                resultados.append(Resultado(ch.id, texto, erro))
            conversa.adicionar_resultados(resultados)

    return _resposta("Parei após muitos passos. Pode reformular o pedido?", passos, acoes, cfg)


def _resposta(texto: str, passos: list, acoes: list, cfg: config.Config) -> dict:
    return {"texto": texto, "passos": passos, "acoes": acoes, "provedor": cfg.llm_provedor, "modelo": cfg.llm_modelo}


def _json(texto: str):
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None
