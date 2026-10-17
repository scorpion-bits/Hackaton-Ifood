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

7. **Ideia: "Match" — composição de pedido por IA para 1 ou N pessoas, 1 ou mais lojas** (17/10 ~19h45).
   Escopo: §7 + §12 + §13 opção 1 de `docs/planos/etapa-01b-match-estrategia.md`. Demo = grupo multi-loja.
   Pagamento: só o organizador entra no iFood; "junto" (1 confirmação, N cobranças) ou "separado" (vaquinha: cada um
   paga a sua parte por Pix real para a chave do organizador, cartão simulado com selo ou dinheiro; o pedido só sai
   com 100% pago). Prazo: 10 min + 2 min por pessoa acima de 2. Descoberta contextual = extra abortável.
   Por quê: maior nota em originalidade e demo; o iFood já tem chat de pedido (Ailo), então o diferencial é a
   composição para grupo com números explicados. Aprovação: equipe. Reverter: o motor serve também 1 pessoa (modo individual).

8. **O Match é cliente MCP com servidor de demonstração local** (mesmos nomes de tools da doc, dados com selo);
   o modo real troca só o transporte (etapa 03). Por quê: desenvolver sem credencial e ter plano B sem internet.
   Aprovação: operacional (Claude). Agente `jurado` criado (aprovado pela equipe).

## Pendentes (👥 decisão humana na abertura)

- Provedor de IA da demo (Groq × Gemini × Ollama) depois de testar com a internet do evento.
