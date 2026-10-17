"""Lista os modelos do provedor configurado no .env: `python -m app.agente.listar_modelos` (em backend/).

Use para escolher LLM_MODEL sem chutar nome. Prefira modelos que suportem tool calling.
"""

import asyncio

from .. import config


async def main() -> None:
    cfg = config.carregar()
    print(f"Provedor: {cfg.llm_provedor}  base_url: {cfg.llm_base_url}")
    if cfg.llm_provedor == "mock":
        print("Modo mock não usa modelo. Defina LLM_PROVIDER no .env (groq, gemini, ollama...).")
        return
    if cfg.llm_provedor == "anthropic":
        import anthropic

        modelos = [m.id async for m in anthropic.AsyncAnthropic(api_key=cfg.llm_chave or None).models.list()]
    else:
        from openai import AsyncOpenAI

        cli = AsyncOpenAI(api_key=cfg.llm_chave or "sem-chave", base_url=cfg.llm_base_url)
        modelos = [m.id async for m in cli.models.list()]
    for m in sorted(modelos):
        print(" ", m)


if __name__ == "__main__":
    asyncio.run(main())
