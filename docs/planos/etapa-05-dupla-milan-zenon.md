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
| A3 | T13: prompts com IA real (intérprete, juiz, agentes de loja) | `backend/app/match/interprete.py`, `juiz.py`, `leilao.py`, `llm.py` | roteiro + 5 frases livres coerentes com chave real | ✅ 01h44 integrado (`8aa7eae`): reserva de modelo no 429, intérprete 1 chamada/grupo, tokens ~26k→13k por Match, bugs 12–14; 👥 confirmar no P5 |
| A4 | Integração: `fix-*` dos testes, branch de integração, PR → `main`, `CLAUDE.md`, planos | `CLAUDE.md`, `docs/planos/*`, `docs/decisions.md` | suíte + build verdes; PR mergeado | 🔄 |
| A6 | CI no GitHub (A1 do `plano-nota-maxima`): pytest + typecheck/build do front a cada push/PR; selo no README | `.github/workflows/*`, `README.md` (só a linha do selo) | workflow verde no `ccr` | ✅ 01h37; runs verdes no GitHub (run 18, 01h55) |
| A5 | Bugs de backend vindos do Thales | conforme o bug (só backend) | bug fechado no `docs/testes/bugs.md` | 🔄 otimizador ✅ `65b4aeb`; 02h00: bugs 21, 23, 24 ✅ 02h10 (`79e50a5` + seguinte); bug 25 (desconto derivado do total do `getCart`, partes fecham) ✅ 02h45 |

### Trilha A′ — agente do Zenon no lugar do Milan (desde 18/10 03h22)
> O agente do Milan ficou sem tokens. A pedido do Zenon, **o agente do Zenon assume a Trilha A** (back, MCP real e
> integração no `ccr`). Quando o agente do Milan voltar: ler esta tabela, o "Registro de execução" (linhas "A′") e o
> `docs/comunicacao.md` (Z16) e retomar daqui. O agente do Thales segue só nos testes (`docs/testes/para-o-thales.md`).
> Origem: relatório de pesquisa + auditoria do agente do Zenon (18/10 03h05): sem mudar de ideia; corrigir o
> **"pedido completo"** (bug "1 item por pessoa": "uma pizza e uma coca" virava pizza + açaí de outra loja).

| ID | Tarefa (aprovada pelo Zenon 03h20) | Arquivos | Pronto quando | Status |
|---|---|---|---|---|
| A′0 | Integrar `zenon/b4-cartao-modo-real` (bug 27) e `zenon/b8-textos-b9b` (Z11) | — | build ok | ✅ 03h25 (`a61cfe4`, `7df6599`) |
| A′F2 | Bebida pela marca ("coca", "guaraná", "pepsi"… → também busca "refrigerante"; juiz deixa bebida entrar) + aviso sem contradição ("Não achei X" e "X ficou de fora: não cabe no orçamento" juntos) | `match/interprete.py`, `juiz.py`, `motor.py`, testes | "uma pizza e uma coca" → pizza + refrigerante da mesma pizzaria | ✅ 03h25 (`bcfac2f`) |
| A′F1 | 2º item da pessoa **na mesma loja**: `searchOffers` com `refinements.merchantId` nas melhores lojas do item principal (e nas lojas do grupo). É o caminho que o `getMerchant` real indica (`catalogSummary.navigationHint`) | `match/busca.py`, `motor.py`, `ifood_mcp/demo_server.py`, testes | "combo de hambúrguer com refri" sem 2ª loja | ✅ 03h28 (`5da2539`) |
| A′F4 | Taxa de entrega e pedido mínimo da busca (`merchant.deliveryMethod.fee`) no custo do otimizador ("taxa estimada; confirmada no carrinho") | `match/busca.py`, `motor.py`, `demo_server.py` | explicação mostra custo com taxa | ✅ 03h30 (`8257e79`) |
| A′F5 | **Só eu além de restaurante**: lista de compras de mercado/farmácia/pet/bebidas vira itens na categoria certa (`merchantType`); 1 loja por categoria quando der; carrinho real. Sem juntar entregas de lojas diferentes | `match/interprete.py`, `busca.py`, `juiz.py`, `dados_demo_match.json`, testes | "preciso de ração, shampoo e pilha" monta carrinho | ✅ 03h40 (`c46116b`) |
| A′F3 | Combos: combo que cobre 2+ itens da pessoa vira opção dela no otimizador (preço 1×); nunca combo + avulsos repetidos | `match/otimizador.py`, `modelos.py`, `busca.py`, testes | "hambúrguer com batata e refri" → combo **ou** avulsos | ⬜ **sai se não estiver estável às 08h** |
| A′9 | Docs: `feedback-mcp.md` (busca na loja, taxa na busca), `tecnico.md`, P8 no `para-o-thales.md` (reteste no real) | docs | — | ⬜ |

Decidido pelo Zenon (03h20): multicategoria e consolidação de entrega **não** viram código em grupo (só slide de
visão); a frase do pitch ("cada um fala o que quer; o IBits monta o pedido completo de cada um na menor quantidade de
lojas, divide a conta e pede pelo iFood") vai para o Thales decidir (pitch é dele, Z2). **Pendente de decisão:** envio
real (`submitOrder`) na conta de teste com o Cartão de Teste (P8 do plano antigo / bug 28) — ninguém faz sem o ok do
Zenon e do Thales.

### Trilha B — Zenon (agente do Zenon: front, entrega, pitch)
> **Zenon trabalha de casa (remoto); Milan e Thales estão no evento.** Toda tarefa do Zenon tem que ser feita só com o
> git: nada que dependa do PC do Thales, do `.env` ou de ensaio presencial. O que exige o PC do Thales (confirmar as
> frases do pedido real, ensaios cronometrados) passou para Milan + Thales no evento. Recados ao Zenon só pelo quadro.
| ID | Tarefa | Arquivos (só estes) | Pronto quando | Status |
|---|---|---|---|---|
| B1 | C14 front: campo "Ajustar com o IBits" no deck, bolhas da conversa, disputa curta, aviso ao convidado | `frontend/src/telas/Deck.tsx`, `Resultado.tsx`, `frontend/src/componentes/leilao/*`, `frontend/src/leilao.css`, `frontend/src/api.ts`, `frontend/src/tipos.ts`, `frontend/src/App.tsx` | build ok; fluxo funciona contra a rota da A2 (antes dela: contra um mock local no próprio front) | ✅ integrado (Zenon testou no navegador contra a A2); B4 forma de pagamento na tela ✅ integrado |
| B2 | Pacote de entrega (T22): `docs/ENTREGA.md` + PDF único dos 6 entregáveis | `docs/ENTREGA.md`, `docs/entrega/*` | PDF gerado com os 6 entregáveis e capturas | ✅ integrado 23h39; gerar o PDF de novo antes das 12h30 |
| B3 | Pitch final (T24): ~5 min, palavras do regulamento, MCP real, Ajustar | `pitch/*`, `docs/roteiro-demo.md`, `docs/roteiro-video.md`, `docs/pitch-perguntas-banca.md` | PDF do pitch; roteiro cronometrado com o Thales | ✅ integrado (`ce9296a`); 👥 confirmar frases marcadas no PC do Thales + 3 ensaios |
| B4 | Bugs de front vindos do Thales | conforme o bug (só `frontend/`) | bug fechado no `docs/testes/bugs.md` | 🔄 bolha ✅ (`a6810d7`), bugs 8/11 ✅; aviso `lojas_fora` ✅ integrado 02h30 (`f855c80`); Pix sem chave ✅ integrado 02h35 (`b8f2254`) |
| B6 | Smoke no navegador 390×780, modo demonstração: sala → 3 convidados → Rodar Match → disputa → deck → **Ajustar** → pagamento → pedido; também Só eu e "Recarregar demo". Conferir checklist (nenhum botão quebrado, selo DEMONSTRAÇÃO) e trocar as capturas de `docs/entrega/04-interface.md` | `docs/testes/bugs.md` (só linhas novas, área/front ou back), `docs/entrega/*` | lista do que quebrou no `bugs.md`; capturas novas | ✅ 01h01 (`ce6b5c3`, 28/28) |
| B9 | Z1: resultado sem "Tinder" — melhor combinação direto, mudar = Ajustar, "Confirmar pedido" → pagamento (liberado pelo Milan 01h36) | `frontend/src/telas/Deck.tsx`, `Resultado.tsx` (+ textos ligados) | build ok, smoke 28/28, capturas novas; **prazo 05h**, senão fica o deck atual | ✅ integrado 02h09 (`a84db11`); smoke 02h18 16/16 ok (qa-testador) |
| B7 | Vídeo do plano B (≤ 2 min, `docs/roteiro-video.md`) gravado em casa no modo demonstração → arquivo para o Thales (Drive/WhatsApp, **não** no git) | `docs/roteiro-video.md`, `docs/roteiro-demo.md` (só a seção Plano B) | `match-demo.mp4` no PC do Thales | ✅ 01h17 (`d313ece`, arquivo fora do git) |
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
- **03h22 → agora (agente do Zenon no lugar do Milan, Trilha A′):** F2 → F1 → F4 → F5 → F3 (até 08h) → P8 do Thales (reteste no MCP real) → congelar 10h30 → PR `ccr` → `main` → PDF 11h30. Modelo: **Opus** (otimizador/busca); sem `/clear` (o contexto está nesta sessão). Agente do Milan ao voltar: ler a Trilha A′ e o Z16.
- **Toda rodada (Milan):** `git fetch` → ver `docs/testes/para-o-thales.md` (P1 endereço, P2 IA real, P3/P4 carrinho
  real), `docs/testes/bugs.md` e o quadro (branches novas do Zenon: integrar no `ccr`). Pedido novo ao Thales = linha P
  nova nesse arquivo (nunca chamar). Testes sempre num worktree separado se houver subagente editando.
- **02h09:** B9 integrado (resultado direto, sem deck) + reteste P6 do Thales (iFood com `INTERNAL` intermitente e `MERCH-007` em loja aberta → 2 linhas no `feedback-mcp.md`). 471 testes, build ok. Esperando: **P6b** do Thales (quando o iFood estabilizar) → P7 `submitOrder` real na conta de teste (`IFOOD_MCP_PERMITIR_ENVIO=true`) → **Opus**. Zenon: B4 `lojas_fora` ✅; agora Pix sem chave (B4) → integrar. Depois: PR `ccr` → `main` (A4, Sonnet basta).
- **02h40:** esperando P7 do Thales (iFood estável). Com P7 ok → Milan decide o **P8** (`submitOrder` real na conta de teste, Cartão de Teste, `IFOOD_MCP_PERMITIR_ENVIO=true`) → ajuste fino do `checkout.py` com o JSON do desconto → **Opus**. PR `ccr` → `main` perto do congelamento (10h30), **Sonnet**.
- **Quando chegar o P2 (`docs/testes/ia-real.txt`):** A3 — prompts com a IA real (`interprete.py`, `juiz.py`,
  `leilao.py`, `ajuste.py`), comparar com a linha de base do registro de 00h41 → **Sonnet**; depois I3 (custo/tempo).
- **Quando chegar o P4 (amostras de carrinho com sucesso):** ajuste fino do `checkout.py` → **Opus**.
- **Zenon (remoto):** B9 (Z1, prazo 05h) → bugs de front → README (B8 sem pitch) → PDF às ~11h30. D1 modo palco **saiu** (01h36, nada novo). Pitch/roteiros = Thales (Z2).

## Registro de execução
- 18/10 03h40 — A′F5 (agente do Zenon): Só eu além de restaurante. `interprete.py`: categorias de varejo (pet, farmácia, adega, mercearia) com 1 produto por parte, contexto ("fazer compras", "na farmácia") que não vira item, ":" separa, item sem categoria herda a categoria anterior; prompt da IA com as 6 verticais. `busca.py`: `merchantType` na busca de varejo, adicional barato só em restaurante, sem `browseOffers` no varejo, busca na loja aceita outra categoria. `juiz.py`: no varejo o produto vale mais que o detalhe. `motor.py`: no varejo só concorrem itens perto da melhor nota (ração de gato não ganha de ração de cachorro por preço) e aviso de lista com mais de 4 itens. Demo: Drogaria Bem Estar, Pet Amigo, mercado com arroz/feijão/leite/ovos/limpeza/pilha. Front: exemplos de compras no Só eu e texto da folha "Só eu" (`SoEu.tsx`, `Inicio.tsx`). 499 testes, build ok. Limite: 4 itens por pessoa (o otimizador enumera opções por pessoa; 5+ fica lento). Próximo: A′F3 (combos, até 08h).
- 18/10 03h30 — A′F4 (agente do Zenon): taxa da busca (`merchant.deliveryMethod.promotionalFee/fee`; demo `deliveryFee`) e pedido mínimo lidos em `busca._ler_loja`; `motor` passa `taxas` ao otimizador (2 chamadas) → `taxa_conhecida: true`, explicação "com taxa", aviso "estimada; valor final no carrinho" e aviso de economia ("Juntando os itens em N lojas, o pedido paga R$ X a menos de taxa…" contra cada item na loja de maior nota). Teste antigo `test_taxa_de_entrega_nao_aparece_na_busca` trocado: o real traz a taxa. 486 testes. Pedido mínimo ainda só lido (não vira regra). Próximo: A′F5 (Só eu multicategoria).
- 18/10 03h28 — A′F1 (agente do Zenon): 2º item na loja do 1º (`busca.buscar_na_loja` + `motor._completar_na_mesma_loja`): até 2 lojas do item principal × até 2 consultas, para na 1ª que acha; só entra item cujo texto bate com o pedido (a busca semântica real pode trazer qualquer item da loja). Rastro mostra `refinements={merchantId}`. 484 testes. Falta no real: confirmar que `refinements.merchantId` + `merchantType` funcionam juntos (P8 do Thales). Próximo: A′F4 (taxa da busca).
- 18/10 03h25 — A′F2 (agente do Zenon): bebida pela marca + aviso sem contradição. "uma pizza e uma coca"/"pizza e um guaraná"/"pizza e um refri" → pizza + refrigerante da mesma pizzaria (testes novos em `test_motor.py`/`test_interprete.py`). 482 testes. Próximo: A′F1 (busca na mesma loja).
- 18/10 03h25 — A′0 (agente do Zenon no lugar do Milan): integrados `zenon/b4-cartao-modo-real` (bug 27) e `zenon/b8-textos-b9b` (Z11). Build ok. Auditoria: 474 testes no `ccr`. Bug "1 item por pessoa" reproduzido no demo: "uma pizza e uma coca" → pizza + açaí de outra loja; "pizza e um guaraná" → guaraná de fora com 2 avisos que se contradizem; "combo de hambúrguer com refri" → refri de outra loja; "hambúrguer com batata e refri" → lanche + batata + combo (que já tem os dois). Causas: bebida pela marca não reconhecida; busca de cada item na cidade toda (nunca dentro da loja do item principal); combo ignorado.
- 18/10 02h40 — Integrado `zenon/b8-textos-b9` (`0d3ea5e`, `racional-ux.md`/`tecnico.md` sem deck). Z11 respondido: Zenon corrige Patrocinado/título da avaliação/"Enviar sem deslizar" depois do B7. P7 para o Thales (reteste com bug 25, envio desligado; P8 `submitOrder` só com ok do Milan). 474 testes, typecheck e build ok. Sem subagente (rodada só de integração).
- 18/10 02h45 — Bug 25 (dev-mcp-ifood, Opus): `_ler_totais` aceita desconto/benefício/voucher do `summary` e, sem campo, deriva desconto = subtotal + taxa − total (`desconto_derivado: true`); o rateio que já existia passa a fechar as partes. Busca não mudou (promoção é aplicada no total). 474 testes. A confirmar no real: nome do campo, desconto sobre a taxa, total do `getCart` = cobrado no `submitOrder`. Opus adequado (poderia ser Sonnet).
- 18/10 02h35 — Integrados `zenon/b4-pix-sem-chave` (`b8f2254`) e o P6b + roteiro sem deck do Thales (`dcdb1fa`); limpas as linhas duplicadas pelo merge no quadro/bugs. 471 testes, typecheck e build ok. P6b: bug 21 ✅, 24 ✅; novo bug 25 (total do carrinho com desconto não lido → partes não fecham) → dev-mcp-ifood (Opus).
- 18/10 02h30 — Integrado `zenon/b4-lojas-fora` (`f855c80`: faixa amarela em `Pagamento.tsx` + "X ficou sem pedido", parte de front do bug 26). Conflito só em `quadro.md`/`comunicacao.md` (mantidas as duas linhas). 471 testes, typecheck e build ok.
- 18/10 02h25 — Respondido o Z8 do Zenon: aviso de loja que saiu termina em "o pedido segue com as outras lojas" (não há volta ao resultado na tela de pagamento depois do B9); ITEM-001 aponta para o Ajustar; ok para limpar deck/É um Match do `racional-ux.md`/`tecnico.md`. 471 testes. Esperando: B4 `lojas_fora` (Zenon) e P6b (Thales, iFood instável). Sem subagente (3 linhas).
- 18/10 02h18 — Smoke do B9 (qa-testador, Sonnet, 390×780, demo): 16/16, sem bloqueio, sem texto do deck na tela. Pendências: `docs/roteiro-demo.md` ainda fala em deck/"Dar match"/"É um Match!" (pitch = Thales); demo deve usar "troca o sorvete do Milan e do Zenon por açaí"; ⚪ Pix aparece sem chave do organizador (falha só ao clicar, 409 com mensagem). Sonnet adequado.
- 18/10 02h09 — Integrados `zenon/b9-resultado-direto` (`a84db11`: resultado direto, sai `EhUmMatch`/`Confete`) e o reteste do P6 (Thales, `33e618b`; conflito só nas linhas dos bugs 21–24, mantidos os status ✅ + nota do Thales). `feedback-mcp.md`: MERCH-007 em loja aberta e INTERNAL intermitente. 471 testes, typecheck e build ok. Smoke do B9 com qa-testador (Sonnet) em segundo plano.
- 18/10 02h10 — P6 parcial do Thales (bugs 21–24). Bug 21 (dev-mcp-ifood, Opus): loja que falha no carrinho sai, as outras seguem, campo novo `lojas_fora` no `escolher` + aviso em `sala.avisos`; INTERNAL/SERVICE_UNAVAILABLE com 1 nova tentativa (0,5 s); partes só de quem tem item. Bugs 23/24 (dev-backend, Sonnet): mock quando `listAddresses` falha; aviso "opção mais próxima" reescrito após o otimizador (`79e50a5`). 471 testes. Pendente: aviso na tela (front, Zenon); Whopper R$ 4,90 sem causa (falta JSON bruto). Opus/Sonnet adequados.
- 18/10 01h58 — P5 do Thales integrado (`ia-real-3.txt`: roteiro 9 ok/0 fallback/0 × 429; frases livres na reserva). Achado no
  log: IA devolve só "doce" e a demo não acha nada → consulta genérica ganha "sobremesa" (`interprete.py`, 1 teste). 455 testes.
  CI do GitHub verde. Sem subagente nesta rodada (correção de 10 linhas).
- 18/10 01h50 — Bugs 17–20 (dev-mcp-ifood, Opus): opção obrigatória preenchida com a mais barata via `getItem` no checkout
  (`options` = `[{optionId, quantity}]` do schema real), adicional < R$ 2,50/seção de extras não vira prato, carrinho com
  taxa/total mesmo sem forma aceitável (escolher 200, enviar 409), Cartão de Teste (nome com "teste", nunca Pix) libera a
  trava. 454 testes, build ok, roteiro demo igual. 5 suposições a confirmar → P6 do Thales. Opus foi adequado.
- 18/10 01h44 — A3 integrada (dev-backend, Sonnet, worktree): reserva de modelo no 429, 11→9 chamadas, ~26k→13k tokens
  contados por Match (ainda >8k/min num só modelo: a reserva é obrigatória), bugs 12/13/14; 14b (aviso duplo) feito por
  mim no `motor.py`. 427 testes; roteiro no fallback igual. P5 para o Thales. Sonnet foi adequado. Obs.: o worktree saiu
  do `main` antigo (6bc3fa0), não do `ccr`: conflito só no `config.py`/`testar_ia.py`.
- 18/10 01h41 — Integrados Thales (P2 IA real; endereço mock pelo `.env` + `options=[]`, bugs 16–20) e Zenon (bugs 8/11, B7).
  **Carrinho real com taxa já sai** (BK, taxa R$ 9,99) com endereço mock. A6 CI ✅. Decisões do Milan: Z1 liberado até 05h
  (B9), D1 fora, **bug 18: usar o Cartão de Teste** (nunca Pix; envio só com flag + consentimento). Em andamento: A3
  (dev-backend, Sonnet, worktree) e bugs 17–20 (dev-mcp-ifood, Opus). 405 testes.
- 18/10 01h04 — A1 (dev-mcp-ifood, Opus): bugs 1/2/3/5 do MCP real com as amostras do Thales. createCart com items,
  listPaymentMethods por merchantId, erro em resposta normal vira ErroMCP com código, parser de busca no formato real
  (antes descartava 100% dos itens reais), browseOffers com merchantType. 402 testes; demo igual à linha de base.
  Falta amostra de carrinho com sucesso → P4 do Thales (depende de endereço salvo, P1). Opus foi adequado.
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
