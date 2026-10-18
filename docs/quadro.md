# Quadro de trabalho — quem está fazendo o quê

> Regras em `docs/AVISO-EQUIPE.md`; divisão em `docs/planos/etapa-05-dupla-milan-zenon.md`.
> Registrar a linha **antes** de começar e dar push; atualizar ao terminar.
> Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ⏸️ parado · ❌ desistiu. Hora em BRT.

| Pessoa | Branch | Tarefa | Arquivos reservados | Status | Início | Fim / commit / pendência |
|---|---|---|---|---|---|---|
| Milan | `claude/tender-dijkstra-rmqhjx` | Aviso, quadro, plano da etapa 05, roteiro de testes | `docs/AVISO-EQUIPE.md`, `docs/quadro.md`, `docs/planos/etapa-05-*`, `docs/testes/roteiro-testes.md`, `CLAUDE.md` | ✅ | 17/10 23h15 | integrado no `ccr-4c429dbb-lp7btg` |
| Milan | `ccr-4c429dbb-lp7btg` | A4 — integração e PR → `main` | `CLAUDE.md`, `docs/planos/*`, `docs/decisions.md` | 🔄 | 17/10 23h55 | |
| Milan | `milan/a1-mcp-real` | A1 — T8 + C16 (MCP real até o pedido) | `backend/app/match/busca.py`, `checkout.py`, `modelos.py`, `backend/app/ifood_mcp/*`, `docs/feedback-mcp.md`, `docs/mcp-real/` | ⬜ espera 👥 amostras | | |
| Milan | `milan/a2-ajustar-back` | A2 — C14 backend | `backend/app/match/ajuste.py`, `rotas_match.py`, `salas.py`, `backend/tests/test_ajuste.py` | ⬜ | | |
| Zenon | `zenon/b1-ajustar-front` | B1 — C14 front | `frontend/src/telas/Deck.tsx`, `Resultado.tsx`, `componentes/leilao/*`, `leilao.css`, `api.ts`, `tipos.ts`, `App.tsx` | ⬜ | | |
| Zenon | `zenon/b2-pacote-entrega` | B2 — pacote dos 6 entregáveis | `docs/ENTREGA.md`, `docs/entrega/*` | ⬜ | | |
| Thales | (só `docs/testes/bugs.md`) | Testes guiados | `docs/testes/bugs.md` | ⬜ | | |

## Recados entre agentes
- 17/10 23h55 · Milan → sessão que conduziu a etapa 04 (T18–T22 estavam 🔄 sem branch no remoto): se ainda tem
  trabalho, dê push no branch e escreva aqui; o dono da trilha (A2/B1/B2) aproveita e não refaz. Não integre mais
  no `ccr-4c429dbb-lp7btg` — quem integra agora é o agente do Milan.
- 17/10 23h55 · Milan → Zenon: o formato do `POST /api/salas/{id}/ajustar` é o C14 da etapa 04; até a A2 sair,
  use um mock local no `api.ts`.
