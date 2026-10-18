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
> **Zenon trabalha de casa (remoto); Milan e Thales estão no evento.** Toda tarefa do Zenon tem que ser feita só com o
> git: nada que dependa do PC do Thales, do `.env` ou de ensaio presencial. O que exige o PC do Thales (confirmar as
> frases do pedido real, ensaios cronometrados) passou para Milan + Thales no evento. Recados ao Zenon só pelo quadro.
| ID | Tarefa | Arquivos (só estes) | Pronto quando | Status |
|---|---|---|---|---|
| B1 | C14 front: campo "Ajustar com o IBits" no deck, bolhas da conversa, disputa curta, aviso ao convidado | `frontend/src/telas/Deck.tsx`, `Resultado.tsx`, `frontend/src/componentes/leilao/*`, `frontend/src/leilao.css`, `frontend/src/api.ts`, `frontend/src/tipos.ts`, `frontend/src/App.tsx` | build ok; fluxo funciona contra a rota da A2 (antes dela: contra um mock local no próprio front) | ✅ integrado (Zenon testou no navegador contra a A2); B4 forma de pagamento na tela ✅ integrado |
| B2 | Pacote de entrega (T22): `docs/ENTREGA.md` + PDF único dos 6 entregáveis | `docs/ENTREGA.md`, `docs/entrega/*` | PDF gerado com os 6 entregáveis e capturas | ✅ integrado 23h39; gerar o PDF de novo antes das 12h30 |
| B3 | Pitch final (T24): ~5 min, palavras do regulamento, MCP real, Ajustar | `pitch/*`, `docs/roteiro-demo.md`, `docs/roteiro-video.md`, `docs/pitch-perguntas-banca.md` | PDF do pitch; roteiro cronometrado com o Thales | ✅ integrado (`ce9296a`); 👥 confirmar frases marcadas no PC do Thales + 3 ensaios |
| B4 | Bugs de front vindos do Thales | conforme o bug (só `frontend/`) | bug fechado no `docs/testes/bugs.md` | 🔄 bolha do Ajustar com nome duplicado ✅ (`a6810d7`) |
| B6 | Smoke no navegador 390×780, modo demonstração: sala → 3 convidados → Rodar Match → disputa → deck → **Ajustar** → pagamento → pedido; também Só eu e "Recarregar demo". Conferir checklist (nenhum botão quebrado, selo DEMONSTRAÇÃO) e trocar as capturas de `docs/entrega/04-interface.md` | `docs/testes/bugs.md` (só linhas novas, área/front ou back), `docs/entrega/*` | lista do que quebrou no `bugs.md`; capturas novas | ⬜ |
| B7 | Vídeo do plano B (≤ 2 min, `docs/roteiro-video.md`) gravado em casa no modo demonstração → arquivo para o Thales (Drive/WhatsApp, **não** no git) | `docs/roteiro-video.md`, `docs/roteiro-demo.md` (só a seção Plano B) | `match-demo.mp4` no PC do Thales | ⬜ |
| B8 | Jurado simulado no pitch final + 6 entregáveis e correção de texto do que tirar ponto; README com passo a passo para a banca | `README.md`, `pitch/*`, `docs/ENTREGA.md`, `docs/racional-ux.md`, `docs/proposta-negocio.md`, `docs/avaliacao-jurado.md` | nota do jurado registrada; README testado do zero | ⬜ |
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
- **O `.env` está no PC Windows do Thales** (MCP + chave Groq já lá). Milan e Thales juntos no evento:
  1. A1: `cd backend` → `.venv\Scripts\python.exe -m app.ifood_mcp.diagnostico --carrinho` → push de `docs/mcp-real/`.
  2. A3: no `.env`, `LLM_PROVIDER=groq` + `GROQ_API_KEY` → `.venv\Scripts\python.exe -m app.agente.listar_modelos`
     → escolher `LLM_MODEL` → `.venv\Scripts\python.exe -m app.match.testar_ia` → salvar a saída (sem a chave) em
     `docs/testes/ia-real.txt` e dar push. Linha de base sem IA (fallback) abaixo, no registro de 00h41.
  3. Thales: `iniciar.bat` e o roteiro de testes; confirmar as frases marcadas do pitch (`CONFIRMAR NO PC DO THALES`)
     e 3 ensaios cronometrados (antes eram do Zenon).
- **Zenon (remoto):** bugs de front que o Thales registrar no `bugs.md` (B4), regerar o PDF da entrega/pitch perto das
  12h30 (B2/B3) e ajustes de texto do pitch quando Milan/Thales registrarem no quadro o que mudou.

## Próximo passo (atualizar a cada etapa — é daqui que o `/continuar` parte)
- **Agora:** PR #6 já está **mergeado em `main`** (18/10 00h37 BRT; `cc5413f`). 378 testes + typecheck ok. Falta só
  👥: Thales rodar o `diagnostico --carrinho` no PC e dar push de `docs/mcp-real/` (destrava A1/T8) e criar chave
  Groq/Gemini (destrava A3). Sem isso, a demo vai no modo demonstração (já estável). Congelar código às 10h30.
- **Depois (Milan):** A1/T8 formato real assim que `docs/mcp-real/` chegar → **Opus** (MCP real, risco alto).
  A3 (prompts com IA real) quando houver chave → **Sonnet**.
- **Zenon (remoto, só git):** B6 smoke no navegador → Sonnet; B7 vídeo do plano B (👥); B8 jurado + README → Opus;
  B4 bugs de front do `bugs.md` → Sonnet; regerar PDFs (B2/B3) perto das 12h30 → Haiku.

## Registro de execução
- 18/10 00h52 — Integrado `zenon/plano-nota-maxima` (`docs/plano-nota-maxima.md`). Milan delegou os 🔒 ao engenheiro-chefe:
  D4 ✅ (sem Patrocinado na demo, `politica_lojas.json` + `test_leilao.py`), D1 liberado com prazo (03h; sai às 07h se
  instável), D3 parcial depois do B6, D5 fora (microfone exige HTTPS; o QR é http). Ordem do Zenon no quadro. 378 testes.
- 18/10 00h41 — Zenon passa a ser remoto: trilha B só com git; confirmação de frases e ensaios → Milan + Thales.
  A3: novo `backend/app/match/testar_ia.py` (roteiro + 5 frases livres, conta chamadas ao LLM ok × fallback). Linha de
  base sem IA: roteiro ok (todos bem atendidos); fallback erra em "pizza… não como carne" (põe um burger extra), "lanche
  caprichado" (2 burgers), "doce qualquer" (poke junto) e não acha "marmita". É isso que a Groq tem que melhorar.
- 18/10 00h37 — A4: PR #6 confirmado mergeado em `main` (`6bc3fa0`). 378 testes ok. `docs/mcp-real/` ainda não chegou → A1/T8 e A3 seguem bloqueadas por 👥.
- 18/10 00h30 — A4: integrados `zenon/b3-pitch-final` (pitch final) e `zenon/b4-fix-bolha-ajustar`. 377 testes, build ok. Smoke no navegador (qa-testador, Sonnet) em andamento; depois merge do PR #6 → `main`.
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
