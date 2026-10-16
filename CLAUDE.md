# CLAUDE.md — memória operacional (só estado vigente; substituir linhas, não acumular)

## Evento
- Hackathon iFood × SEMCOMP 29, ONOVOLAB (São Carlos). 17/10 12h30 → 18/10 18h00 (BRT). Prêmio R$ 7 mil.
- Tema: comércio com agentes, nos DOIS lados (vender e comprar). Enunciado oficial: **pendente (abertura 17/10 12h30)**.
- Prazo de entrega e formato do pitch: **pendente**. ICMC fala em 27h — confirmar.
- Objetivo: 1º lugar (na última ficamos em 2º por 1 ponto com o AgroBits).

## Equipe
- Thales Miguel Hajes — pitch (apresentador principal), front, testes. PC da apresentação: Windows, sem Docker, Python 3.14, Node 24.
- Milan — IA, back, design.
- Zenon — testes, apoio ao pitch.
- Antonio — testes.

## Papéis e regras
- Decisão estratégica (problema, público, ideia, escopo, arquitetura, demo) → alternativas, recomendação, riscos, esforço, e AGUARDAR aprovação.
- Decisão operacional (nomes, refatoração, bugfix, testes, docs, visual) → Claude decide.
- 👥 = ação humana; 🤖 = Claude executa.
- Nunca inventar número, endpoint ou dado. Simulado = selo "demonstração".
- Ação com dinheiro/pedido/preço/mensagem a cliente → só proposta + confirmação humana.
- Segredos só no `.env`. Commits pequenos em português: `tipo(escopo): descrição`.
- Resposta longa termina com: o que mudou · 🧪 como testar · 👥 o que a equipe faz. Máx. 3 perguntas por vez.

## Fase atual
- **Fase 0 concluída** (esqueleto genérico). Próximo: receber o enunciado → produzir a análise da Fase 4 e PARAR.

## Estado do código
- `backend/app/main.py` — FastAPI: `/api/saude`, `/api/chat`, `/api/acoes[/{id}/confirmar|recusar]`, `/api/lojas`, `/api/demo/resetar`; serve `frontend/dist`.
- `backend/app/agente/` — laço do agente (`laco.py`) + provedores (`provedores.py`: mock, OpenAI-compatível [groq/gemini/ollama/openai], anthropic). Lado `vendedor` ou `comprador` filtra ferramentas pelo prefixo.
- `backend/app/mcp_server.py` — servidor MCP (SDK `mcp` 2.x, `MCPServer`). Ferramentas `vendedor_*`, `comprador_*`, `consultar_acao`. `propor_*` só cria ação pendente.
- `backend/app/acoes.py` — ações pendentes; `EXECUTORES` mapeia tipo → chamada no cliente iFood.
- `backend/app/ifood/` — interface única; `mock.py` (SQLite, dados de `dados_demo.json`), `real.py` (token + leitura; escrita = `NaoSuportado`).
- `backend/mcp_stdio.py` — servidor MCP sozinho (stdio; `--http` em :8001/mcp).
- `frontend/src/App.tsx` — chat mobile first, abas Cliente/Lojista, cartões de confirmação, selo DEMONSTRAÇÃO, "Recarregar demo".
- `pitch/` — Reveal.js local; `npm run pdf` gera `pitch/pitch.pdf` (versionado).
- Testes: `backend/tests` (13, pytest). Typecheck: `cd frontend && npm run typecheck`.

## Como rodar
- Linux: `./iniciar.sh` (app em :8000) · `--dev` · `--testes`.
- Windows: `iniciar.bat` ou `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 [-Dev|-Testes]`.

## Pendências conhecidas
- `iniciar.ps1` não foi executado (sem PowerShell no container) → 👥 testar no PC do Thales.
- Provedor de IA gratuito ainda não testado com chave real → 👥 criar chave Groq/Gemini e rodar `listar_modelos`.
- Caminhos NÃO VERIFICADOS do iFood: ver `docs/ifood-apis.md` §3 (prefixos `/merchant/v1.0`, `/catalog/v2.0`).
- Não há API pública do iFood para o consumidor: lado comprador real depende do que o iFood liberar no evento.

## Docs
- `docs/ifood-apis.md` (fontes + status), `docs/mcp.md`, `docs/decisions.md`, `docs/plano-horas.md`, `docs/checklist-entrega.md`.
