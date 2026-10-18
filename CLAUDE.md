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
- **Ideia aprovada: "Match"** — IA compõe o pedido de 1 ou N pessoas (1 ou mais lojas) a partir de frases livres;
  convidados entram por link/QR sem login; só o organizador usa o iFood. Pagamento "junto" ou "separado" (vaquinha:
  Pix real para a chave do organizador / cartão simulado / dinheiro; pedido só sai com 100% pago; prazo 10 min +
  2 min por pessoa acima de 2). Detalhes: `docs/planos/etapa-01b-match-estrategia.md` e `docs/decisions.md` (7–8).
- **Plano vigente:** `docs/planos/etapa-04-leilao-e-entrega.md` (leilão de agentes por loja + MCP real + entrega; branch de integração `ccr-4c429dbb-lp7btg`, 1 branch por tarefa). Etapas: `docs/planos/README.md`.
- ✅ Agente "IBits" **aprovado** (17/10). Portal: https://mcp-developer.ifood.com.br/pt-BR ("Faça login"). 3 contas de teste
  (`unique-`, `safe-`, `fair-thales@test.ifood.com.br`, expiram em ~16 dias; OTP no portal). Redirect URLs: `http://localhost:8000/oauth/callback` (app),
  `http://127.0.0.1:19876/mcp/oauth/callback` e `http://localhost:19876/mcp/oauth/callback` (opencode).
  Secret só no `.env` (`IFOOD_MCP_CLIENT_ID/SECRET`). Nunca pagar Pix de pedido de teste.
- Respostas para a banca: `docs/pitch-perguntas-banca.md`.

## Orquestração (detalhes em docs/orquestracao.md)
- O chat principal é o **engenheiro-chefe (Opus)**: escreve o plano de cada etapa em `docs/planos/etapa-NN-*.md`
  (modelo `TEMPLATE.md`), delega aos subagentes de `.claude/agents/`, integra, testa, commita.
- Cada tarefa do plano tem agente, **modelo e esforço**; ao delegar, passe exatamente esses `model` e `effort` ao Agent tool.
- Subagentes: `arquiteto`, `dev-backend`, `dev-mcp-ifood`, `dev-frontend`, `qa-testador`, `pitch-demo`, `pesquisador`, `jurado`.
- Comandos: `/tema` → `/executar` → `/continuar` (repetir) · `/status`. Reserva: `docs/prompt-abertura.md`.
- Tudo que precisa sobreviver a um `/clear` vai para o plano vigente ou para este arquivo.
- Tarefas paralelas só com arquivos separados; subagente não faz commit.

## Regra de memória deste arquivo
- Máximo **250 linhas**, só estado vigente. Passou do limite → mover o que não vale mais para `docs/historico.md`
  (topo, com data e motivo; arquivar, nunca apagar) e voltar a ~180 linhas. Um hook avisa automaticamente.

## Estado do código
- `backend/app/match/` — Match: `motor.py` (intérprete → busca MCP → juiz → otimizador; até 3 lojas), `llm.py`
  (provedor do `.env`, fallback offline), `otimizador.py` (pontuação §4 da 01b, vários itens por pessoa = slots `pid#k`),
  `acerto.py` (partes em centavos, prazo 10+2/pessoa), `pix.py` (BR Code), `checkout.py` (sequência MCP, consentimento),
  `salas.py` (estado em SQLite). Campos das tools só em `busca.py` e `checkout.py`.
- `backend/app/rotas_match.py` — API da sala (`/api/salas...`, contrato C7 da etapa 02). `main.py` serve `frontend/dist`.
- `backend/app/ifood_mcp/` — `cliente.py` (`abrir_cliente(cfg)`, rastro), `demo_server.py` + `dados_demo_match.json`
  (MCP de demonstração, 7 lojas fictícias). Modo real: etapa 03.
- `frontend/src/` — home estilo iFood (`telas/Inicio.tsx`), `Organizador`, `Convidado`, `Resultado`, `Pagamento`, `Pedidos`.
- Esqueleto antigo (`agente/`, `mcp_server.py`, `ifood/`, `acoes.py`) segue no repo só como referência; remover depois da 03.
- `pitch/` — slides do Match; `docs/roteiro-demo.md`. Testes: `./iniciar.sh --testes` (95).

## Como rodar
- Linux: `./iniciar.sh` (app em :8000) · `--dev` · `--testes`.
- Windows: `iniciar.bat` ou `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 [-Dev|-Testes]`.

## Pendências conhecidas
- `iniciar.ps1` não foi executado (sem PowerShell no container) → 👥 testar no PC do Thales.
- Provedor de IA gratuito ainda não testado com chave real → 👥 criar chave Groq/Gemini e rodar `listar_modelos`.
- Credenciais do MCP só no `.env` do PC da equipe (não no container da nuvem). Nomes das tools vêm da doc → confirmar com `list_tools`.
- O domínio antigo do esqueleto (lojas/vendedor/comprador, Merchant API) não é usado pelo Match; remover só depois da etapa 03.

## Docs
- `docs/mcp-ifood.md` (MCP do consumidor: conexão, 24 tools, sequência), `docs/feedback-mcp.md`, `docs/ifood-apis.md`
  (Merchant API, fora do foco), `docs/mcp.md` (como fazer servidor MCP), `docs/decisions.md`, `docs/design-ifood.md` (visual do app), `docs/checklist-entrega.md`. Horários: `docs/planos/README.md` (o `plano-horas.md` é antigo).
