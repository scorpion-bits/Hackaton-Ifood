# CLAUDE.md — memória operacional (só estado vigente; máx. 250 linhas — o hook arquiva o excesso)

## Evento
- Hackathon SEMCOMP × iFood "Vendendo com Agentes", São Carlos. Prêmios R$ 4.000 / 2.000 / 1.000.
- **Desafio oficial:** agente de IA que opera o **MCP do iFood (consumidor)** para fazer pedidos — da escolha do
  restaurante ao fechamento do carrinho. Resumo técnico: `docs/mcp-ifood.md`.
- **Horários:** dev sáb 17/10 13h → **dom 18/10 12h30 (submissão)**; pitches dom 13h–16h; resultado 17h.
- **Critérios (5 pilares):** Visão & Originalidade · Arquitetura & Engenharia (uso correto do MCP) · Design &
  Experiência · Impacto · Comunicação & Pitch.
- **6 entregáveis:** proposta de negócio · desenho de solução · racional de UX · interface visual · doc técnico ·
  **feedback sobre o MCP** (anotar em `docs/feedback-mcp.md` durante todo o evento).
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
- **Etapa 01 (análise) feita; aguardando a equipe escolher a ideia** (`/executar <ideia>`). Recomendação: "Racha Aí"
  (pedido em grupo). O esqueleto da Fase 0 é **só referência**.
- **Plano vigente:** `docs/planos/etapa-01-analise.md`. Índice: `docs/planos/README.md`.
- 👥 Acesso ao MCP: criar conta e agente no Portal (escopos todos, redirect `http://localhost:8000/oauth/callback`),
  esperar a homologação, guardar o client secret só no `.env`.

## Orquestração (detalhes em docs/orquestracao.md)
- O chat principal é o **engenheiro-chefe (Opus)**: escreve o plano de cada etapa em `docs/planos/etapa-NN-*.md`
  (modelo `TEMPLATE.md`), delega aos subagentes de `.claude/agents/`, integra, testa, commita.
- Cada tarefa do plano tem agente, **modelo e esforço**; ao delegar, passe exatamente esses `model` e `effort` ao Agent tool.
- Subagentes: `arquiteto`, `dev-backend`, `dev-mcp-ifood`, `dev-frontend`, `qa-testador`, `pitch-demo`, `pesquisador`.
- Comandos: `/tema` → `/executar` → `/continuar` (repetir) · `/status`. Reserva: `docs/prompt-abertura.md`.
- Tudo que precisa sobreviver a um `/clear` vai para o plano vigente ou para este arquivo.
- Tarefas paralelas só com arquivos separados; subagente não faz commit.

## Regra de memória deste arquivo
- Máximo **250 linhas**, só estado vigente. Passou do limite → mover o que não vale mais para `docs/historico.md`
  (topo, com data e motivo; arquivar, nunca apagar) e voltar a ~180 linhas. Um hook avisa automaticamente.

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
- Credenciais do MCP ainda não existem (homologação pendente). Nomes das tools vêm da doc → confirmar com `list_tools`.
- O esqueleto usa a Merchant API (lojista), que não é o foco: será trocado pelo cliente MCP do consumidor.

## Docs
- `docs/mcp-ifood.md` (MCP do consumidor: conexão, 24 tools, sequência), `docs/feedback-mcp.md`, `docs/ifood-apis.md`
  (Merchant API, fora do foco), `docs/mcp.md` (como fazer servidor MCP), `docs/decisions.md`, `docs/plano-horas.md`, `docs/checklist-entrega.md`.
