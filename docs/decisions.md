# Decisões

Formato: data · decisão · por quê · quem aprovou · como reverter.

## 16/10/2026 — Fase 0 (antes do tema)

1. **Stack: FastAPI + SQLite + React/TS (Vite) + servidor MCP em Python (SDK `mcp` 2.x).**
   Por quê: uma linguagem no back reduz risco no Windows sem Docker; o SDK oficial em Python cobre stdio e HTTP.
   Aprovação: stack pedida pela equipe; linguagem do MCP decidida pelo Claude (equipe respondeu "não sei").
   Reverter: o servidor MCP é um arquivo (`backend/app/mcp_server.py`); trocar por TypeScript custa ~2h.

2. **IA gratuita com provedor plugável no `.env`:** `mock` (padrão, offline), `groq`, `gemini`, `ollama`;
   `openai`/`anthropic` opcionais. Por quê: a equipe pediu opção gratuita e a internet do evento é incerta.
   Modelo **não** vem pré-escolhido: `python -m app.agente.listar_modelos` mostra os disponíveis (evita nome inventado).
   Aprovação: equipe ("vamos usar alguma gratuita").

3. **Agente usa as ferramentas pelo protocolo MCP, em processo** (`mcp.Client(MCPServer)`), em vez de subprocesso.
   Por quê: uso real de MCP sem depender de subprocessos/event loop no Windows. O mesmo servidor sobe por stdio/HTTP.
   Aprovação: operacional (Claude).

4. **Ações com dinheiro/preço/pedido = proposta + confirmação humana na tela.** Nenhuma ferramenta MCP executa.
   Por quê: regra de qualidade da equipe e argumento de pitch ("agente confiável").
   Aprovação: regra da equipe (prompt inicial).

5. **iFood em dois modos com a mesma interface: `mock` (demonstração, padrão) e `real`.**
   O modo real só implementa leitura (token, lojas, cardápio); escrita levanta `NaoSuportado` até confirmarmos a doc.
   Por quê: o portal bloqueou leitura automática; não inventar endpoint. Ver `docs/ifood-apis.md`.
   Aprovação: regra da equipe ("nunca suponha endpoint").

6. **Frontend compilado servido pelo próprio FastAPI em :8000.** Um processo, uma URL na demo.
   Aprovação: operacional (Claude).

## Pendentes (👥 decisão humana na abertura)

- Problema, público, ideia e escopo do MVP → depois do enunciado oficial (Fase 4 do plano).
- Nome do produto.
- Provedor de IA da demo (Groq × Gemini × Ollama) depois de testar com a internet do evento.
