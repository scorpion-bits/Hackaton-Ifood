# Quadro de trabalho — quem está fazendo o quê

> Regras em `docs/AVISO-EQUIPE.md`; divisão em `docs/planos/etapa-05-dupla-milan-zenon.md`.
> Registrar a linha **antes** de começar e dar push; atualizar ao terminar.
> Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ⏸️ parado · ❌ desistiu. Hora em BRT.

| Pessoa | Branch | Tarefa | Arquivos reservados | Status | Início | Fim / commit / pendência |
|---|---|---|---|---|---|---|
| Milan | `claude/tender-dijkstra-rmqhjx` | Aviso, quadro, plano da etapa 05, roteiro de testes | `docs/AVISO-EQUIPE.md`, `docs/quadro.md`, `docs/planos/etapa-05-*`, `docs/testes/roteiro-testes.md`, `CLAUDE.md` | ✅ | 17/10 23h20 | integrado no `ccr-4c429dbb-lp7btg` |
| Milan | `ccr-4c429dbb-lp7btg` | A4 — integração e PR → `main` | `CLAUDE.md`, `docs/planos/*`, `docs/decisions.md` | 🔄 | 17/10 23h27 | 23h39: 4 branches do Zenon integradas, 375 testes; falta smoke no navegador e PR → `main` |
| Milan | `milan/a1-mcp-real` | A1 — T8 + C16 (MCP real até o pedido) | `backend/app/match/busca.py`, `checkout.py`, `modelos.py`, `backend/app/ifood_mcp/*`, `docs/feedback-mcp.md`, `docs/mcp-real/` | ⬜ espera 👥 amostras | | |
| Zenon | `match/04-so-eu` | B5 — Só eu (C15) | `telas/Inicio.tsx`, `Organizador.tsx`, `SoEu.tsx`, `estilo.css`, `BarraInferior.tsx` | ✅ | 17/10 23h22 | já no `ccr` (961a8a7, 23h26), antes de eu ver o aviso |
| Zenon | `match/04-ajustar-front` | B1 — C14 front (Ajustar com o IBits no deck; sala de 1 pessoa paga "junto" direto) | `telas/Deck.tsx`, `Resultado.tsx`, `Leilao.tsx`, `componentes/leilao/*`, `leilao.css`, `api.ts`, `tipos.ts` | ✅ | 17/10 23h22 | `5d16de5` — integrado 23h39 (build ok; falta teste no navegador contra a A2) |
| Zenon | `match/05-pacote-entrega` | B2 — `docs/ENTREGA.md` + PDF único dos 6 entregáveis (29 p.) | `docs/ENTREGA.md`, `docs/entrega/*` | ✅ | 17/10 23h22 | integrado 23h39; gerar o PDF de novo antes das 12h30 (`cd docs/entrega && npm i && node gerar_pdf.mjs`) |
| Zenon (para o Milan) | `match/03-pedido-real` | parte da A1 — C16 (pagamento real nunca Pix/online; `browseOffers` quando a busca volta vazia) | `match/checkout.py`, `match/busca.py`, `tests/test_pedido_real.py`, `test_checkout.py`, `test_motor.py` | ✅ | 17/10 23h22 | integrado 23h39; trava `pagamento.offline` mantida |
| Zenon (para o Milan) | `match/04-ajustar-back` | A2 — C14 backend (`ajuste.py`, `POST /ajustar`, `ajustes`) | `match/ajuste.py`, `rotas_match.py`, `salas.py`, `tests/test_ajuste.py` | ✅ | 17/10 23h22 | push 23h36; integrado pelo Milan 23h39 |
| Zenon | `zenon/b4-pagamento-na-tela` | B4 — mostrar a forma de pagamento do carrinho ("Pagamento: Dinheiro na entrega") e o aviso de conta de teste sem forma sem cobrança | `frontend/src/telas/Pagamento.tsx`, `frontend/src/tipos.ts` (só o campo `pagamento` do carrinho), `frontend/src/estilo.css` (classes `.loja-pagamento*`) | ✅ | 17/10 23h39 | `2331f9b` (17/10 23h40) — integrado 23h41 pelo Milan depois do `match/03-pedido-real`; sem o campo `pagamento` a tela não muda |
| Milan | `claude/tender-dijkstra-rmqhjx` → `ccr` | A5 — bug do otimizador (2 lojas corta itens "até 3 lojas") + `;` do Mermaid | `backend/app/match/otimizador.py`, `backend/tests/test_otimizador*.py`, `docs/tecnico.md` | ✅ | 17/10 23h54 | `65b4aeb` + `fb062f0` (17/10 23h58), 377 testes; caso do Zenon agora: 3 lojas, açaí entra, só o sorvete fica de fora (exigiria 4ª loja) |
| Zenon | `match/04-ajustar-back` | T18 (etapa 04) = A2 — fechamento a pedido do Milan | — (só conferência) | ✅ | 18/10 00h00 | nada pendente: `e845399` está no remoto e no `ccr`; C14 completo (200 com `entendido`+`resultado`, 422, 409 mantém a sala, `ajustes` no GET); 377 testes e typecheck ok no `ccr` às 00h00. Milan: na tabela da etapa 04 (`docs/planos/`, reservado a você) T18/T19/T21/T22 ainda aparecem 🔄 — podem virar ✅ |
| Zenon | `zenon/b3-pitch-final` | B3 — pitch final (T24): ~5 min, frase única do aviso, Ajustar, Só eu, MCP real sem inventar número | `pitch/*`, `docs/roteiro-demo.md`, `docs/roteiro-video.md`, `docs/pitch-perguntas-banca.md` | ✅ | 18/10 00h02 | `ce9296a` (18/10 00h11), pronto para integrar. 10 slides, ~5 min, sem Patrocinado; disputa = avaliação simulada por nós. Pendente 👥: confirmar no PC do Thales as frases marcadas (`<!-- CONFIRMAR NO PC DO THALES -->` no slide 6 e `> ⚠️ confirmar` nos roteiros) e 3 ensaios cronometrados; regerar o `pitch.pdf` se mudar algo |
| Zenon | `zenon/b4-fix-bolha-ajustar` | B4 — bolha do Ajustar mostra o nome duas vezes ("Entendi: Milan: Milan: açaí…"): o back já manda o `resumo` com o nome | `frontend/src/componentes/leilao/util.ts` | ✅ | 18/10 00h12 | `a6810d7` (18/10 00h14), pronto para integrar; typecheck, build e 377 testes ok. Visto pelo agente do pitch; não estava no `bugs.md` |
| Zenon | `zenon/plano-nota-maxima` | Plano "rumo à nota máxima" (sugestões por pilar, dono e prazo) | `docs/plano-nota-maxima.md` (novo) | ✅ | 18/10 00h47 | `4194a3d` (18/10 00h48) — **para o Milan integrar** (só 1 arquivo novo) |
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
- 17/10 23h39 · Milan → Zenon: integrei as 4 branches (375 testes, build ok) e concordo com a trava do
  `pagamento.offline`. Para você (B4): mostrar "Pagamento: Dinheiro na entrega" no front. O `;` do Mermaid em
  `docs/tecnico.md` e o bug do otimizador (3 lojas) ficam comigo.
- 17/10 23h58 · Milan → Zenon: bug do otimizador corrigido (`65b4aeb`, no `ccr`). Com o teu caso o top 1 agora usa 3 lojas e só o sorvete fica de fora (aviso verdadeiro, com sugestão de 4ª loja). Pode aparecer o alerta "perecível chega em horário diferente" (açaí 20 min × japonês 45) — é real. `;` do Mermaid também corrigido.
- 18/10 00h14 · Zenon → Milan: para integrar (sem conflito entre elas e sem arquivo seu): `zenon/b3-pitch-final` (`ce9296a`, pitch final + roteiros + banca) e `zenon/b4-fix-bolha-ajustar` (`a6810d7`, 1 arquivo do front). O pitch novo segue o aviso: frase única, sem Patrocinado, disputa = avaliação simulada por nós. O slide 6 e os roteiros têm frases do pedido real marcadas para confirmar quando a A1 fechar no PC do Thales (se não fechar até 10h30, a demo é no modo demonstração e a fala alternativa já está no roteiro). Informação: no modo demonstração o Poke Verde ainda aparece na disputa com o rótulo "Patrocinado"; está congelado, então só deixei "não narrar" no roteiro. Pode registrar no "Próximo passo" do plano que a B3 está pronta.
- 18/10 00h41 · Milan → Zenon: você está remoto, então a trilha B fica só com o que dá para fazer pelo git: bugs de front do `bugs.md` (B4), regerar os PDFs da entrega/pitch perto das 12h30 e ajustar o texto do pitch quando eu ou o Thales registrarmos aqui o que mudou. Confirmar as frases do pedido real e os ensaios passaram para mim + Thales no evento. A chave Groq já está no PC do Thales; a A3 roda lá com `python -m app.match.testar_ia`.
- 18/10 00h48 · Zenon → Milan e Thales: **para tirar nota máxima, estas mudanças são necessárias** — lista completa, com dono,
  prazo e status em `docs/plano-nota-maxima.md` (branch `zenon/plano-nota-maxima`, `4194a3d`; Milan, integre e me diga
  quais itens 🔒 você libera). Resumo: **N1** pedido de verdade gravado (diagnóstico → A1 → carrinho real → `submitOrder`
  na conta de teste se um mentor confirmar, nunca Pix) e **N2** IA real no app (A3) são o que mais pesa — o regulamento
  pede "agente que faz pedidos de verdade". 🔒 Peço o ok para: **D1 modo palco** (4 celulares no projetor, só para a
  demo; eu faço no front), **D3** detalhes de UX, **D4** tirar o Patrocinado do `politica_lojas.json` (seu arquivo) e
  **D5** pedido por voz. **Thales/Antonio no evento:** D2 teste de usabilidade com 5 pessoas (cronometrar), I1 experimento
  WhatsApp × Match com 2–3 grupos, I2 formulário n ≥ 30 até 09h. **Milan:** A1 CI no GitHub, A2 feedback do MCP real, I3
  medir custo/tempo de um Match com IA real. Eu (remoto) faço A3 docs, D6 capturas, I4, O1–O3 e C1/C3 no pitch.
  "O jurado participa" fica de fora (pitch de 5 min).
- 18/10 00h49 · Milan → Zenon: três tarefas novas para você, todas de casa (detalhes na trilha B do plano da etapa 05), nesta ordem: **B6** smoke no navegador 390×780 no modo demonstração (fluxo completo com Ajustar + Só eu + Recarregar demo; o que quebrar vai para o `bugs.md`; capturas novas no `04-interface.md`) → **B7** gravar o vídeo do plano B (`docs/roteiro-video.md`) e mandar o arquivo ao Thales fora do git → **B8** jurado simulado no pitch e nos entregáveis + README com passo a passo para a banca. Registre aqui antes de começar.
