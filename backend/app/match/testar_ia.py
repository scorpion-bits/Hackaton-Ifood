"""Testa a IA real (A3) em 1 comando: `python -m app.match.testar_ia` (em backend/, com o `.env` preenchido).

Roda o roteiro da demo + 5 frases livres no modo do `.env` (demo por padrão) e mostra, para cada caso, o que o
Match escolheu e quantas chamadas ao LLM deram certo (as que falham caem no fallback determinístico).
Não envia pedido nem mexe em carrinho. Nunca imprime a chave.
"""

import asyncio
import time

from .. import config
from ..ifood_mcp.cliente import abrir_cliente
from . import ajuste, interprete, juiz, leilao
from .llm import completar_json
from .modelos import Desejo
from .motor import rodar_match

ROTEIRO = [
    Desejo("p1", "Milan", "japonês e um sorvete, até 45"),
    Desejo("p2", "Zenon", "hambúrguer e sorvete, até 50"),
    Desejo("p3", "Antonio", "algo barato e vegetariano, até 25"),
]
FRASES_LIVRES = [
    "quero algo leve, sem lactose, até 40",
    "tô morrendo de fome, um lanche bem caprichado",
    "pizza pra dividir, mas eu não como carne",
    "uma comida caseira tipo marmita, até 30",
    "doce qualquer, chega rápido",
]

contagem = {"ok": 0, "falhou": 0, "segundos": 0.0}


async def _completar_contando(*args, **kwargs):
    inicio = time.perf_counter()
    dados = await completar_json(*args, **kwargs)
    contagem["segundos"] += time.perf_counter() - inicio
    contagem["ok" if dados is not None else "falhou"] += 1
    return dados


async def _caso(cfg, titulo: str, desejos: list[Desejo]) -> None:
    contagem.update(ok=0, falhou=0, segundos=0.0)
    async with abrir_cliente(cfg) as cliente:
        r = await rodar_match(cfg, cliente, desejos)
    print(f"\n=== {titulo} ===")
    for d in desejos:
        print(f"  {d.nome}: \"{d.texto}\"")
    if not r["combinacoes"]:
        print("  (nenhuma combinação)", "; ".join(r["avisos"]))
    else:
        top = r["combinacoes"][0]
        for slot, e in top["escolhas"].items():
            print(f"  → {slot}: {e['item_nome']} · {e['loja_nome']} · R$ {e['preco']:.2f}")
        print(f"  explicação: {top.get('explicacao', '')}")
    print(f"  LLM: {contagem['ok']} ok, {contagem['falhou']} caíram no fallback, {contagem['segundos']:.1f} s")


async def main() -> None:
    cfg = config.carregar()
    print(f"Provedor: {cfg.llm_provedor} · modelo: {cfg.llm_modelo or '(vazio)'} · "
          f"chave: {'sim' if cfg.llm_chave else 'não'} · MCP: {getattr(cfg, 'ifood_mcp_modo', 'demo')}")
    if cfg.llm_provedor == "mock" or not cfg.llm_modelo:
        print("Sem IA real: defina LLM_PROVIDER=groq, LLM_MODEL e GROQ_API_KEY no .env "
              "(modelos: python -m app.agente.listar_modelos).")
    for modulo in (interprete, juiz, leilao, ajuste):
        modulo.completar_json = _completar_contando
    await _caso(cfg, "Roteiro da demo (3 pessoas)", ROTEIRO)
    for i, frase in enumerate(FRASES_LIVRES, 1):
        await _caso(cfg, f"Frase livre {i}", [Desejo("p1", "Thales", frase)])


if __name__ == "__main__":
    asyncio.run(main())
