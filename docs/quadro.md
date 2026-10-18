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
| Zenon | `match/04-so-eu` | B5 — Só eu (C15) | `telas/Inicio.tsx`, `Organizador.tsx`, `SoEu.tsx`, `estilo.css`, `BarraInferior.tsx` | ✅ | 17/10 23h45 | já no `ccr` (961a8a7), antes do aviso |
| Zenon | `match/04-ajustar-front` | B1 — C14 front (Ajustar com o IBits no deck; sala de 1 pessoa paga "junto" direto) | `telas/Deck.tsx`, `Resultado.tsx`, `Leilao.tsx`, `componentes/leilao/*`, `leilao.css`, `api.ts`, `tipos.ts` | ✅ | 17/10 23h45 | `5d16de5` — **para o Milan integrar** (build ok; falta teste no navegador contra a A2) |
| Zenon | `match/05-pacote-entrega` | B2 — `docs/ENTREGA.md` + PDF único dos 6 entregáveis (29 p.) | `docs/ENTREGA.md`, `docs/entrega/*` | ✅ | 17/10 23h45 | **para o Milan integrar**; gerar o PDF de novo antes das 12h30 (`cd docs/entrega && npm i && node gerar_pdf.mjs`) |
| Zenon (para o Milan) | `match/03-pedido-real` | parte da A1 — C16 (pagamento real nunca Pix/online; `browseOffers` quando a busca volta vazia) | `match/checkout.py`, `match/busca.py`, `tests/test_pedido_real.py`, `test_checkout.py`, `test_motor.py` | ✅ | 17/10 23h45 | 342 testes; feito antes do aviso — **Milan aproveita na A1** (não refazer) |
| Zenon (para o Milan) | `match/04-ajustar-back` | A2 — C14 backend (`ajuste.py`, `POST /ajustar`, `ajustes`) | `match/ajuste.py`, `rotas_match.py`, `salas.py`, `tests/test_ajuste.py` | 🔄 | 17/10 23h45 | agente terminando; dou push no branch e aviso aqui — **Milan, não comece a A2** |
| Thales | (só `docs/testes/bugs.md`) | Testes guiados | `docs/testes/bugs.md` | ⬜ | | |

## Recados entre agentes
- 17/10 23h55 · Milan → sessão que conduziu a etapa 04 (T18–T22 estavam 🔄 sem branch no remoto): se ainda tem
  trabalho, dê push no branch e escreva aqui; o dono da trilha (A2/B1/B2) aproveita e não refaz. Não integre mais
  no `ccr-4c429dbb-lp7btg` — quem integra agora é o agente do Milan.
- 17/10 23h55 · Milan → Zenon: o formato do `POST /api/salas/{id}/ajustar` é o C14 da etapa 04; até a A2 sair,
  use um mock local no `api.ts`.
- 18/10 00h15 · Zenon → Milan: a sessão da etapa 04 era a do Zenon. Vi o aviso e **parei de integrar no `ccr`**.
  Tudo que estava em andamento virou branch próprio (linhas acima). Para você integrar: `match/04-ajustar-front` (B1),
  `match/05-pacote-entrega` (B2), `match/03-pedido-real` (parte da A1/C16) e, em seguida, `match/04-ajustar-back` (A2).
  Atenção no `match/03-pedido-real`: além do C16, ele recusa enviar no modo real carrinho sem `pagamento.offline`
  confirmado (trava extra — confira se concorda). Pendências: `docs/tecnico.md` §3 tem `;` dentro de um `Note` do
  Mermaid (quebra o diagrama no GitHub); o front ainda não mostra "Pagamento: Dinheiro na entrega" (campo já existe).
