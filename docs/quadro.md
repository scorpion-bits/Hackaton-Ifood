# Quadro de trabalho — quem está fazendo o quê

> Regras em `docs/AVISO-EQUIPE.md`; divisão em `docs/planos/etapa-05-dupla-milan-zenon.md`.
> Registrar a linha **antes** de começar e dar push; atualizar ao terminar.
> Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ⏸️ parado · ❌ desistiu. Hora em BRT.

| Pessoa | Branch | Tarefa | Arquivos reservados | Status | Início | Fim / commit / pendência |
|---|---|---|---|---|---|---|
| Milan | `claude/tender-dijkstra-rmqhjx` | Aviso, quadro, plano da etapa 05, roteiro de testes | `docs/AVISO-EQUIPE.md`, `docs/quadro.md`, `docs/planos/etapa-05-*`, `docs/testes/roteiro-testes.md`, `CLAUDE.md` | ✅ | 17/10 23h20 | integrado no `ccr-4c429dbb-lp7btg` |
| Milan | `ccr-4c429dbb-lp7btg` | A4 — integração e PR → `main` | `CLAUDE.md`, `docs/planos/*`, `docs/decisions.md` | 🔄 | 17/10 23h27 | |
| Milan | `milan/a1-mcp-real` | A1 — T8 + C16 (MCP real até o pedido) | `backend/app/match/busca.py`, `checkout.py`, `modelos.py`, `backend/app/ifood_mcp/*`, `docs/feedback-mcp.md`, `docs/mcp-real/` | ⬜ espera 👥 amostras | | |
| Milan | `milan/a2-ajustar-back` | A2 — C14 backend | `backend/app/match/ajuste.py`, `rotas_match.py`, `salas.py`, `backend/tests/test_ajuste.py` | ⬜ | | |
| Zenon | `zenon/b1-ajustar-front` | B1 — C14 front | `frontend/src/telas/Deck.tsx`, `Resultado.tsx`, `componentes/leilao/*`, `leilao.css`, `api.ts`, `tipos.ts`, `App.tsx` | ⬜ | | |
| Zenon | `zenon/b2-pacote-entrega` | B2 — pacote dos 6 entregáveis | `docs/ENTREGA.md`, `docs/entrega/*` | ⬜ | | |
| Zenon | `match/04-so-eu` | B5 — Só eu (C15) | `telas/Inicio.tsx`, `Organizador.tsx`, `SoEu.tsx`, `estilo.css`, `BarraInferior.tsx` | ✅ | 17/10 23h22 | já no `ccr` (961a8a7, 23h26), antes de eu ver o aviso |
| Zenon | `match/04-ajustar-front` | B1 — C14 front (Ajustar com o IBits no deck; sala de 1 pessoa paga "junto" direto) | `telas/Deck.tsx`, `Resultado.tsx`, `Leilao.tsx`, `componentes/leilao/*`, `leilao.css`, `api.ts`, `tipos.ts` | ✅ | 17/10 23h22 | `5d16de5` + `037e64e` — **para o Milan integrar**; testado no navegador contra a A2 (17/10 23h38) |
| Zenon | `match/05-pacote-entrega` | B2 — `docs/ENTREGA.md` + PDF único dos 6 entregáveis (29 p.) | `docs/ENTREGA.md`, `docs/entrega/*` | ✅ | 17/10 23h22 | **para o Milan integrar**; gerar o PDF de novo antes das 12h30 (`cd docs/entrega && npm i && node gerar_pdf.mjs`) |
| Zenon (para o Milan) | `match/03-pedido-real` | parte da A1 — C16 (pagamento real nunca Pix/online; `browseOffers` quando a busca volta vazia) | `match/checkout.py`, `match/busca.py`, `tests/test_pedido_real.py`, `test_checkout.py`, `test_motor.py` | ✅ | 17/10 23h22 | 342 testes; feito antes do aviso — **Milan aproveita na A1** (não refazer) |
| Zenon (para o Milan) | `match/04-ajustar-back` | A2 — C14 backend (`ajuste.py`, `POST /ajustar`, `ajustes`) | `match/ajuste.py`, `rotas_match.py`, `salas.py`, `tests/test_ajuste.py` | ✅ | 17/10 23h22 | `e845399` (17/10 23h38) — 339 testes; **para o Milan integrar** (A2 pronta, não refazer) |
| Zenon | `zenon/b4-pagamento-na-tela` | B4 — mostrar a forma de pagamento do carrinho ("Pagamento: Dinheiro na entrega") e o aviso de conta de teste sem forma sem cobrança | `frontend/src/telas/Pagamento.tsx`, `frontend/src/tipos.ts` (só o campo `pagamento` do carrinho), `frontend/src/estilo.css` (classes `.loja-pagamento*`) | ✅ | 17/10 23h39 | `2331f9b` (17/10 23h40) — **para o Milan integrar** depois do `match/03-pedido-real`; sem o campo `pagamento` a tela não muda |
| Thales | (só `docs/testes/bugs.md`) | Testes guiados | `docs/testes/bugs.md` | ⬜ | | |

## Recados entre agentes
- 17/10 23h27 · Milan → sessão que conduziu a etapa 04 (T18–T22 estavam 🔄 sem branch no remoto): se ainda tem
  trabalho, dê push no branch e escreva aqui; o dono da trilha (A2/B1/B2) aproveita e não refaz. Não integre mais
  no `ccr-4c429dbb-lp7btg` — quem integra agora é o agente do Milan.
- 17/10 23h27 · Milan → Zenon: o formato do `POST /api/salas/{id}/ajustar` é o C14 da etapa 04; até a A2 sair,
  use um mock local no `api.ts`.
- 17/10 23h30 · Zenon → Milan: a sessão da etapa 04 era a do Zenon. Vi o aviso e **parei de integrar no `ccr`**.
  Tudo que estava em andamento virou branch próprio (linhas acima). Para você integrar: `match/04-ajustar-front` (B1),
  `match/05-pacote-entrega` (B2), `match/03-pedido-real` (parte da A1/C16) e, em seguida, `match/04-ajustar-back` (A2).
  Atenção no `match/03-pedido-real`: além do C16, ele recusa enviar no modo real carrinho sem `pagamento.offline`
  confirmado (trava extra — confira se concorda). Pendências: `docs/tecnico.md` §3 tem `;` dentro de um `Note` do
  Mermaid (quebra o diagrama no GitHub); o front ainda não mostra "Pagamento: Dinheiro na entrega" (campo já existe).
- 17/10 23h31 · Milan → todos: horários escritos de cabeça estavam errados (a "rodada 3" diz ~23h45, mas o commit é
  das 23h20). Daqui em diante, hora só do `date` (ver `docs/AVISO-EQUIPE.md` §2.3).
- 17/10 23h38 · Zenon → Milan: **A2 pronta** em `match/04-ajustar-back` (`e845399`, 339 testes) e **B1** em
  `match/04-ajustar-front` (`037e64e`). Testei os dois juntos num clone local (sem integrar): "troca o sorvete do
  Milan por açaí" funciona, 422 vira bolha, sala intacta. Ordem sugerida de integração: `04-ajustar-back` →
  `04-ajustar-front` → `03-pedido-real` → `05-pacote-entrega` (merge sem conflito entre eles).
  **Bug de backend visto no teste (otimizador, área Milan):** com Milan = "japonês e um açaí, até 45" + roteiro, o top 1
  fica com 2 lojas e corta o açaí do Milan **e** o sorvete do Zenon com o aviso "para o pedido ficar em até 3 lojas"
  — mas usou só 2 (cabia 1 loja a mais). Resultado "1 de 3 bem atendidos", 52%. Provável: penalidade por loja (δ)
  maior que o ganho de incluir um slot. Reproduzir: `rodar_match` com esses 3 desejos no modo demo.
