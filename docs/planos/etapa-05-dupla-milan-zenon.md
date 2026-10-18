# Etapa 05 — Reta final em dupla: Milan (back + MCP) × Zenon (front + entrega) · Thales testa

> Plano vigente a partir de **17/10 ~23h27** (pedido do Milan). Continua a etapa 04
> (`etapa-04-leilao-e-entrega.md`: contratos C11–C16 valem como estão) e **substitui a divisão de tarefas dela**.
> Regras de autor, quadro e branches: `docs/AVISO-EQUIPE.md`. Antes de começar qualquer tarefa: `docs/quadro.md`.

- **Objetivo (1 frase):** o Match em grupo faz um pedido de verdade pelo MCP real na conta de teste, com a conversa
  "Ajustar com o IBits", testado no PC do Thales — e os 6 entregáveis + pitch final prontos.
- **Pronto quando:** (1) no PC com `.env`, `IFOOD_MCP_MODO=real`: sala → convidados → Rodar Match com lojas reais →
  `getCart` com taxa real → pedido (sem Pix); (2) "Ajustar com o IBits" refaz o Match; (3) `./iniciar.sh --testes` e
  `npm run build` passam; o modo demonstração sustenta a demo sem internet; (4) roteiro de testes do Thales sem
  bloqueio; (5) PR do branch de integração → `main` mergeado.
- **Prazo (BRT):** agora → **dom 10h30 congelar** → 12h30 submissão.

## Prioridade (corte de cima para baixo se faltar tempo)
1. **MCP real até o pedido** (T8 + C16) — pilar "uso correto do MCP".
2. **Ajustar com o IBits** (C14) — o regulamento pede agente conversacional + ferramentas determinísticas.
3. Testes do Thales → correções.
4. Pacote de entrega (6 entregáveis) e pitch final.
5. **Só eu** (C15) e polimento de UI — **só se 1–4 estiverem ok**. Nada além disto.

## Divisão — quem mexe em quê (arquivos exclusivos; não tocar no do outro)

### Trilha A — Milan (este agente: back, MCP, integração)
| ID | Tarefa | Arquivos (só estes) | Pronto quando | Status |
|---|---|---|---|---|
| A1 | T8 + C16: busca/checkout no formato real; `browseOffers` quando a busca vem vazia; pagamento real nunca Pix (prefere dinheiro/na entrega) | `backend/app/match/busca.py`, `checkout.py`, `modelos.py`, `backend/app/ifood_mcp/*`, `backend/tests/test_checkout.py`, `test_busca*.py`, `docs/feedback-mcp.md`, `docs/mcp-real/` | testes passam com as amostras reais; 👥 no PC: carrinho real com taxa | 🔄 C16 ✅ (Zenon, `match/03-pedido-real`, integrado 23h39); falta T8 formato real ⬜ 👥 amostras |
| A2 | C14 backend: `match/ajuste.py` + `POST /api/salas/{id}/ajustar` + campo `ajustes` | `backend/app/match/ajuste.py`, `backend/app/rotas_match.py`, `backend/app/match/salas.py`, `backend/tests/test_ajuste.py` | contrato C14 coberto por teste (200, 422, 409 mantém resultado) | ✅ (Zenon, `match/04-ajustar-back`, integrado 23h39) |
| A3 | T13: prompts com IA real (intérprete, juiz, agentes de loja) | `backend/app/match/interprete.py`, `juiz.py`, `leilao.py`, `llm.py` | roteiro + 5 frases livres coerentes com chave real | ⬜ (👥 chave) |
| A4 | Integração: `fix-*` dos testes, branch de integração, PR → `main`, `CLAUDE.md`, planos | `CLAUDE.md`, `docs/planos/*`, `docs/decisions.md` | suíte + build verdes; PR mergeado | 🔄 |
| A5 | Bugs de backend vindos do Thales | conforme o bug (só backend) | bug fechado no `docs/testes/bugs.md` | 🔄 otimizador (recado do Zenon 23h38) ✅ `65b4aeb` |

### Trilha B — Zenon (agente do Zenon: front, entrega, pitch)
| ID | Tarefa | Arquivos (só estes) | Pronto quando | Status |
|---|---|---|---|---|
| B1 | C14 front: campo "Ajustar com o IBits" no deck, bolhas da conversa, disputa curta, aviso ao convidado | `frontend/src/telas/Deck.tsx`, `Resultado.tsx`, `frontend/src/componentes/leilao/*`, `frontend/src/leilao.css`, `frontend/src/api.ts`, `frontend/src/tipos.ts`, `frontend/src/App.tsx` | build ok; fluxo funciona contra a rota da A2 (antes dela: contra um mock local no próprio front) | ✅ integrado (Zenon testou no navegador contra a A2); B4 forma de pagamento na tela ✅ integrado |
| B2 | Pacote de entrega (T22): `docs/ENTREGA.md` + PDF único dos 6 entregáveis | `docs/ENTREGA.md`, `docs/entrega/*` | PDF gerado com os 6 entregáveis e capturas | ✅ integrado 23h39; gerar o PDF de novo antes das 12h30 |
| B3 | Pitch final (T24): ~5 min, palavras do regulamento, MCP real, Ajustar | `pitch/*`, `docs/roteiro-demo.md`, `docs/roteiro-video.md`, `docs/pitch-perguntas-banca.md` | PDF do pitch; roteiro cronometrado com o Thales | ⬜ (depois de A1/A2) |
| B4 | Bugs de front vindos do Thales | conforme o bug (só `frontend/`) | bug fechado no `docs/testes/bugs.md` | ⬜ |
| B5 | Só eu (C15) + polimento de UI — **só se a prioridade 1–4 estiver ok** | `frontend/src/telas/Inicio.tsx`, `Organizador.tsx`, `Convidado.tsx`, `SoEu.tsx`, `componentes/Folha.tsx`, `estilo.css` | build ok; 1 pessoa pede em ~20 s | Só eu ✅ (T20, sessão da etapa 04, 961a8a7); polimento ⏸️ |

### Trilha C — Thales (agente do Thales guia os testes; não edita código)
- Segue `docs/testes/roteiro-testes.md` e registra cada problema em `docs/testes/bugs.md` (só o agente do Thales
  escreve lá; Milan e Zenon só mudam o status da linha do bug que corrigirem).

### Fronteira entre A e B (o contrato é a API)
- O formato das rotas está nos contratos C7 (etapa 02) e C11/C14 (etapa 04). **O back não muda o formato sem recado**
  no `docs/quadro.md`; o front não muda arquivo de `backend/`.
- `api.ts`/`tipos.ts` são do Zenon; `rotas_match.py`/`salas.py` são do Milan.
- Arquivo que não está em nenhuma lista → pedir no "Recados" antes de mexer.

## Fluxo de branches
- Cada tarefa: branch `milan/<id>-<nome>` ou `zenon/<id>-<nome>` saído do `ccr-4c429dbb-lp7btg`.
- Ao terminar: testes + build → push → atualizar o quadro → o Milan (A4) integra no `ccr-4c429dbb-lp7btg`.
- Commit com autor humano (`--author="Nome <email>"` + `Responsável: Nome`).

## 👥 Agora
- **O `.env` está no PC Windows do Thales.** 17/10 23h53: ele está fazendo login (Conectar iFood no app) e vai rodar `.venv\Scripts\python.exe -m app.ifood_mcp.diagnostico --carrinho` e dar push de `docs/mcp-real/` (destrava A1).
- Chave Groq/Gemini no `.env` + `python listar_modelos.py` (destrava A3).
- Thales: `iniciar.bat` no PC dele e o roteiro de testes.

## Próximo passo (atualizar a cada etapa — é daqui que o `/continuar` parte)
- **Agora (Milan):** smoke do fluxo completo com "Ajustar" no navegador 390×780 (modo demonstração) → se ok, merge
  do PR #6 (`ccr-4c429dbb-lp7btg` → `main`) → **Sonnet**. Bug do otimizador e `;` do Mermaid ✅ (17/10 23h58).
  Começar com `/clear` → `/continuar`.
- **Depois (Milan):** A1/T8 formato real assim que `docs/mcp-real/` chegar → **Opus** (MCP real, risco alto).
  A3 (prompts com IA real) quando houver chave → **Sonnet**.
- **Zenon:** B4 (mostrar "Pagamento: Dinheiro na entrega" + bugs do Thales) → Sonnet; B3 pitch final → Opus.

## Registro de execução
- 17/10 ~23h27 — plano criado; divisão Milan × Zenon; Thales nos testes. A sessão que conduziu a etapa 04 tinha
  T18–T22 marcados 🔄 sem branch no remoto: **se essa sessão ainda tem trabalho, ela dá push no branch e escreve no
  quadro**; o dono da trilha aproveita o que vier e não refaz.
- 17/10 23h39 — A4: integrados `match/03-pedido-real`, `match/04-ajustar-back`, `match/04-ajustar-front`,
  `match/05-pacote-entrega` (todos do Zenon) sem conflito. **375 testes**, typecheck e build ok. Sem teste no navegador
  ainda. Trava extra do Zenon (modo real só envia com `pagamento.offline` confirmado) mantida: protege a conta de teste.
- 17/10 23h42 — integrados também `037e64e` (Ajustar front) e `zenon/b4-pagamento-na-tela` (forma de pagamento na tela). 375
  testes, build ok. Pushed no `ccr-4c429dbb-lp7btg`.
- 17/10 23h58 — A5: bug do otimizador (Opus, dev-backend): ordem passou a ser "menos itens de fora → score"; aviso de "até 3
  lojas" só quando usa 3. Caso do Zenon: 2 lojas/1 de 3 bem atendidos → 3 lojas/2 de 3 (sorvete exigiria 4ª loja).
  `65b4aeb`, 377 testes. `;` do Mermaid em `docs/tecnico.md` corrigido (`fb062f0`). Opus foi adequado (lógica de pontuação).
  Pendência menor: score exibido pode não decrescer entre combinações com nº diferente de itens de fora.
