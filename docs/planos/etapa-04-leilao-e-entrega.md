# Etapa 04 — Leilão de agentes, MCP real e entrega (cobre as etapas 03-fim, 04 e 05)

> Escrito pelo engenheiro-chefe (Opus). Memória da etapa: depois de um `/clear`, `/continuar` lê só o `CLAUDE.md`
> e este plano e segue daqui.

- **Status da etapa:** em execução (rodada 1 desde 17/10 ~22h)
- **Objetivo (1 frase):** o Match vira um mercado de agentes — **cada restaurante tem um agente vendedor** que só
  enxerga o próprio cardápio (MCP) e disputa o pedido; o **IBits é o agente comprador** da turma — rodando no MCP real,
  com visual do app do iFood e os 6 entregáveis prontos.
- **Pronto quando:** (1) no PC da equipe, `IFOOD_MCP_MODO=real`: Match com lojas reais até o `getCart` (taxa real);
  (2) depois de "Rodar Match", organizador **e convidados** veem o leilão (lances e falas vindos de `resultado.leilao`),
  depois o deck de combinações (deslizar ou botões) e seguem o fluxo de pagamento já existente; (3) todas as telas no
  padrão visual do iFood; (4) `./iniciar.sh --testes` passa e o modo `mock` sustenta a demo sem internet;
  (5) os 6 entregáveis existem em `docs/` + pitch v2 com PDF.
- **Prazo (BRT):** sáb 17/10 22h → dom 18/10 **10h30 (congelar)** → 12h30 submissão.
- **Aprovado pela equipe em:** 17/10 ~22h ("mínimo de corte possível"; equipe delegou a decisão do Patrocinado).

## Contexto mínimo para retomar
- Etapa 03 (`etapa-03-mcp-real.md`): 03.1 (OAuth, cliente real, diagnóstico), 03.2, 03.3 ✅; 03.1b em andamento
  (assumida nesta etapa como T0); 03.4 (👥) e 03.5 (= T8 aqui) pendentes. 176 testes passam.
- Protótipo visual aprovado pela equipe (leilão + deck "É um Match!" + deslize para enviar):
  `/root/.claude/uploads/c9bdf935-3292-5de3-bc83-945c87eda7f5/6ee8986d-Match.html` (HTML único, motor próprio em JS —
  **não** reaproveitar o motor; só visual, textos e animações).
- **Branches:** cada tarefa tem branch próprio criado a partir do branch de integração `ccr-4c429dbb-lp7btg`; os
  subagentes trabalham em worktree próprio e não fazem commit; o engenheiro-chefe commita, dá push e integra no
  `ccr-4c429dbb-lp7btg` ao fim de cada rodada (testes + build + navegador 390×780).
- Regras de sempre: preço, taxa, prazo e disponibilidade só de resposta de tool; LLM nunca escreve número que não
  veio do lance; `submitOrder` só com `userConsent: true` após confirmação humana; selo DEMONSTRAÇÃO em dado simulado.

## Decisões desta etapa
- **D9. Leilão de agentes por loja (com LLM).** Cada agente de loja recebe só os itens da própria loja (achados pelo
  `searchOffers`/`getMerchant`/`getItem`) e os desejos da turma; o LLM decide **quais itens oferecer a quem** (≤ 2 por
  slot) e redige a fala. O otimizador só considera itens ofertados. Validação dura + fallback determinístico.
- **D10. Patrocinado = única política da loja, só visibilidade.** Loja patrocinada tem o lance mostrado primeiro e o
  rótulo "Patrocinado"; **nunca** muda nota, filtro ou escolha do otimizador. No demo, 1 loja patrocinada que **não**
  é vencedora no roteiro (mostra que pagar não compra o pedido). Modelo de negócio no pitch (como anúncios no app),
  com selo "demonstração". No modo real nenhuma loja é patrocinada.

## Contratos desta etapa

### C11. Leilão no resultado do motor (T1 produz, T2 consome)
`rodar_match` passa a devolver, além do que já devolve:
```jsonc
"leilao": {
  "llm": true,                     // ao menos 1 agente de loja usou LLM (false no mock)
  "demonstracao": true,            // espelha o modo do cliente MCP
  "lojas": [{
    "loja_id": "...", "loja_nome": "...", "vertical": "RESTAURANT",
    "eta_min": 35, "avaliacao": 4.7,          // null se a tool não trouxe
    "imagem_url": null,                        // T8 preenche no modo real se o MCP trouxer
    "patrocinado": false,
    "passou": false,                           // true = nada atende ninguém (ou o agente recusou)
    "ofertas": [{"slot_id": "p1#2", "participante_id": "p1", "nome": "Milan",
                 "item_id": "...", "item_nome": "...", "preco": 18.9, "nota": 0.92, "motivo": "..."}],
    "atende": 2,                               // pessoas distintas com oferta
    "afinidade": 88,                           // round(100 × média das notas das ofertas)
    "fala": "Eu atendo 2 de 3 com ...",        // fala do lance ou do passe
    "fonte_fala": "llm",                       // "llm" | "modelo"
    "vencedora": true                          // está na 1ª combinação
  }],
  "falas": [                                   // roteiro na ordem de exibição (o front só toca)
    {"quem": "ibits", "tipo": "abertura", "texto": "Pedido novo para 3 pessoas: ... Quem topa?"},
    {"quem": "<loja_id>", "tipo": "passe", "texto": "Aqui não tem japonês. Passo."},
    {"quem": "<loja_id>", "tipo": "lance", "texto": "...", "preco": 18.9, "afinidade": 88},
    {"quem": "<loja_id>", "tipo": "replica", "texto": "Fecho os 2 sorvetes num pedido só: 1 entrega."},
    {"quem": "ibits", "tipo": "fechamento", "texto": "Rodada fechada: ...", "vencedoras": ["<loja_id>"]}
  ],
  "vencedoras": ["<loja_id>"]
}
```
Cada item de `combinacoes[]` ganha `"afinidade"` (0–100, média por pessoa das notas) e `"felizes"` (pessoas com média
≥ 0,5). Sem candidatos → `leilao` com `lojas: []` e só abertura + fechamento "sem vencedor". Taxa de entrega **não**
aparece nas falas (só existe no carrinho): o fechamento diz "as taxas aparecem no carrinho antes do seu ok".
Limites: ≤ 8 lojas no leilão (as de melhor nota), ≤ 2 passes, ≤ 5 lances, ≤ 1 réplica mostrados.

### C12. Agente de loja (T1, `backend/app/match/leilao.py`)
- `async def rodar_leilao(cfg, slots, candidatos, detalhes, nomes, politica) -> tuple[dict[str, list[Candidato]], dict]`
  → candidatos filtrados pelas ofertas + o bloco `leilao` (sem `vencedora`/`vencedoras`, que o motor marca depois do
  otimizador). Chamado no `motor.py` logo antes de `otimizar` (depois dos ajustes de "opção aproximada").
- Um agente por loja, em paralelo (`asyncio.gather`, tempo máx. ~6 s cada; `llm.completar_json` ganha parâmetro
  opcional `timeout`). Prompt: só os itens daquela loja por slot (nome, descrição, tags, preço do MCP, nota do juiz) +
  o texto de cada pessoa. Saída JSON `{"ofertas": [{"slot_id", "item_id", "motivo"}], "passo": bool, "fala": str}`.
- Validação: `slot_id` existe; `item_id` é candidato daquela loja naquele slot; ≤ 2 por slot; motivo ≤ 90 chars;
  **todo número na fala** precisa estar no conjunto permitido (preços ofertados formatados, ETA, avaliação,
  contagens, afinidade) — senão fala do modelo determinístico (`fonte_fala: "modelo"`). Oferta inválida é descartada;
  se o agente ofertar nada válido sem dizer `passo`, usa o fallback.
- Fallback determinístico (mock, erro, timeout): top-2 por nota do juiz em cada slot da loja; falas por template a
  partir dos números (estilo do protótipo: "Eu atendo todo mundo com X, R$ Y. Nota 4,8, a melhor da sala.").
- **Garantia:** com `LLM_PROVIDER=mock` o top 1 do roteiro (`test_motor.py`) não muda.
- `backend/app/match/politica_lojas.json`: `{"<loja_id do demo>": {"patrocinado": true}}` (1 loja não vencedora).

### C13. Telas do leilão (T2)
- Ao entrar em `match_pronto` (organizador e convidado), se `resultado.leilao` existe e o aparelho ainda não viu o
  leilão desta sala (`localStorage` `match.leilao.visto.<salaId>`, com try/catch): tela **Leilão ao vivo** — arena
  com avatares das lojas (emoji por vertical/categoria, sem foto do iFood; `imagem_url` quando houver), feed de falas
  tocado em sequência (digitando… → texto; ~0,8 s por fala, 1,4 s no fechamento), etiqueta de preço/afinidade no
  lance, "Patrocinado" com selo, vencedoras destacadas, botão **Pular**; rastro MCP resumido no topo ("MCP · N").
- Depois: **Deck** — 1 cartão por combinação (até 3): afinidade %, "N de M felizes", lojas, por pessoa item · loja ·
  preço · motivo; deslizar para a direita = Match, esquerda = próxima; **botões equivalentes** (acessibilidade);
  "É um Match!" → organizador escolhe junto/separado (mesma chamada `escolher` de hoje); convidado vê só leitura.
- Sem `leilao` (resultado antigo/erro) → direto ao deck; deck sem `afinidade` → calcula das notas.

## Tarefas

| ID | Branch | Tarefa | Agente | Modelo | Esforço | Arquivos (só estes) | Depende de | Pronto quando | Status |
|---|---|---|---|---|---|---|---|---|---|
| T0 | `match/03-sanitizacao` | 03.1b: sanitização do diagnóstico por lista branca/substring; aviso de busca vazia + `--args-busca`; sem traceback cru; erros de login → 401; `os.replace` | dev-mcp-ifood | opus | high | `backend/app/ifood_mcp/diagnostico.py`, `oauth.py`, `backend/app/rotas_match.py` (só `_erro_do_ifood`), `backend/app/rotas_oauth.py`, `backend/tests/test_oauth.py`, `backend/tests/test_diagnostico.py` | — | nada pessoal escapa em payloads adversariais; suíte passa || 🔄 |
| T1 | `match/04-leilao-motor` | Agentes por loja com LLM + validação + fallback + patrocinado + afinidade (C11, C12) | dev-backend | opus | high | `backend/app/match/leilao.py` (novo), `motor.py`, `llm.py` (só `timeout`), `politica_lojas.json` (novo), `backend/tests/test_leilao.py` (novo), `backend/tests/test_motor.py` | — | testes: fala com número inventado cai no modelo; item de outra loja é rejeitado; patrocinado não muda a escolha; roteiro mock inalterado; LLM falso cobre o caminho LLM; tempo limite respeitado || ✅ |
| T2 | `match/04-leilao-telas` | Leilão ao vivo + Deck (C13), visual do protótipo | dev-frontend | sonnet | high | `frontend/src/telas/Leilao.tsx`, `Deck.tsx` (novos), `frontend/src/componentes/leilao/*` (novos), `frontend/src/leilao.css` (novo), `telas/Resultado.tsx`, `App.tsx`, `tipos.ts` | C11 | build + typecheck ok; com fixture C11 o leilão toca, Pular funciona, deck com botões e gesto, escolher chama a API || ✅ |
| T3 | `match/04-visual-ifood` | Visual do app do iFood nas demais telas + estados carregando/erro/vazio | dev-frontend | sonnet | high | `frontend/src/estilo.css`, `telas/Inicio.tsx`, `Organizador.tsx`, `Convidado.tsx`, `Pagamento.tsx`, `Pedidos.tsx`, `frontend/src/componentes/*` existentes, `frontend/index.html` | — | build ok; tokens existentes mantidos (só acrescentar); telas no padrão do `design-ifood.md` e do protótipo || 🔄 |
| T4 | `match/05-doc-tecnico` | README do Match + doc técnico com diagramas (entregáveis 2 e 5) | arquiteto | opus | medium | `README.md`, `docs/tecnico.md` (novo) | — | README roda do zero (Windows/Linux); arquitetura, sequência MCP, leilão (C11/C12), segurança, testes, limites; Mermaid || ✅ |
| T5 | `match/05-pesquisa-impacto` | Pesquisa com fonte: anúncios patrocinados em marketplaces/iFood, comércio entre agentes, números do iFood; formulário da pesquisa da equipe | pesquisador | opus | medium | `docs/pesquisa-mercado.md`, `docs/pesquisa-usuarios.md` (novos) | — | todo fato com link e data; formulário de ≤ 6 perguntas (1 min) || ✅ |
| T6 | `match/05-racional-ux` | Racional de UX (entregável 3) | pitch-demo | opus | medium | `docs/racional-ux.md` (novo) | — | princípios, jornada do organizador/convidado, leilão, deck, confiança (consentimento, selo), acessibilidade, o que medimos || ✅ |
| T7 | (só leitura) | Avaliação 1 do jurado (produto atual + este plano) | jurado | opus | high | — (o engenheiro grava `docs/avaliacao-jurado.md`) | — | nota por critério + o que tira pontos || ✅ |
| T8 | `match/03-formato-real` | 03.5: busca e checkout no formato real; ≤ 8 lojas e concorrência limitada no `getMerchant`; `imagem_url`; feedback do MCP (entregável 6) | dev-mcp-ifood | opus | high | `match/busca.py`, `match/checkout.py`, `match/modelos.py`, `ifood_mcp/demo_server.py`, `backend/tests/test_formato_real.py`, `docs/feedback-mcp.md`, `docs/mcp-ifood.md` | 👥 03.4 | amostras reais viram fixtures e passam; Match real até `getCart` no PC | ⬜ |
| T9 | `match/04-limpeza-legado` | Remover domínio antigo (vendedor/comprador, Merchant API, `mcp_server.py`, `acoes.py`, `ifood/`, rotas e testes antigos) mantendo `agente/provedores.py` | dev-backend | sonnet | medium | `backend/app/agente/laco.py`, `mcp_server.py`, `mcp_stdio.py`, `acoes.py`, `ifood/`, `main.py`, testes antigos, `dados_demo.json`, `iniciar.*` se citarem | R1 integrada | suíte passa; app sobe; nada importa o legado | ✅ |
| T10 | (integração) | Integrar rodada 1 + navegador 390×780 | engenheiro-chefe | — | — | — | R1 | fluxo inteiro com leilão no mock | ⬜ |
| T11 | (só leitura) | QA do leilão, visual e números | qa-testador | opus | high | — | T10 | nada bloqueia a demo | ⬜ |
| T12 | `match/05-proposta-negocio` | Proposta de negócio (entregável 1) | pitch-demo | opus | medium | `docs/proposta-negocio.md` (novo) | T5 | problema, público, valor para o iFood, Patrocinado, métricas, riscos, com fonte | ✅ |
| T13 | `match/04-ajuste-ia` | Ajuste de prompts com IA real (intérprete, juiz, agentes) e tempo do leilão | dev-backend | sonnet | medium | `match/interprete.py`, `juiz.py`, `leilao.py` (só prompts) | 👥 chave, T10 | roteiro e frases livres coerentes com IA real; leilão ≤ 8 s | ⬜ |
| T14 | `match/05-pitch-v2` | Pitch v2 + roteiro 2 min + roteiro do vídeo + banca + PDF | pitch-demo | opus | medium | `pitch/*`, `docs/roteiro-demo.md`, `docs/pitch-perguntas-banca.md` | T8, T10, T12 | narrativa vendedores × comprador; fatos com fonte; PDF gerado | ⬜ |
| T15 | (integração) | Integrar rodadas 2–3; `CLAUDE.md`, `decisions.md`, checklist (congelar 10h30) | engenheiro-chefe | — | — | — | R2 | suíte, build, navegador | ⬜ |
| T16 | (só leitura) | Avaliação 2 do jurado (produto, pitch, 6 entregáveis) | jurado | opus | high | — | T15 | lista final de correções | ⬜ |
| T17 | `match/fix-*` | Correções do QA/jurado | conforme o arquivo | sonnet | high | conforme | T16 | — | ⬜ |

Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ❌ falhou (ver registro) · ⏸️ adiado

**Paralelismo:** Rodada 1 (22h → ~01h30): T0–T7 · Rodada 2 (→ 04h): T8 (quando chegar a 03.4), T9, T10, T11, T12 ·
Rodada 3 (→ 07h): T13, T14, T15, T16 · Rodada 4 (→ 10h30): T17, QA final, 👥 ensaios e vídeo.
**Arquivos exclusivos por tarefa paralela** (ver coluna). T2 só usa tokens CSS que já existem; T3 só acrescenta tokens.

**Por que esses modelos/esforços:** T1 opus/high: é o diferencial e tem regra de honestidade (número de LLM). T2/T3
sonnet/high: telas grandes mas padrão. T4–T6 e T12/T14 opus/medium: texto que a banca lê. T9 sonnet/medium: remoção mecânica.

## 👥 Equipe
- Agora: login + diagnóstico no PC quando o T0 sair (`python -m app.ifood_mcp.diagnostico --carrinho`) e push de
  `docs/mcp-real/`; chave Groq/Gemini + `listar_modelos`; aplicar a pesquisa (T5) no evento; descobrir o formato da
  submissão; revezar o sono (1 pessoa acordada com o PC).
- Até 07h: `iniciar.bat` no PC do Thales. 07h–10h: vídeo do plano B, 3 ensaios cronometrados.

## Riscos e plano B
- MCP real não fecha → demo no modo demonstração (pronto) + rastro real gravado no pitch.
- Leilão no front não fecha até 04h → sai da demo, vira slide com o protótipo; o motor com agentes continua.
- IA real lenta/fora → fallback determinístico em ≤ 6 s; `mock` sustenta a demo.
- Conflito de branch → arquivos exclusivos; integração só pelo engenheiro-chefe.

## Registro de execução
- 17/10 ~22h — plano aprovado; branches criados a partir de `ccr-4c429dbb-lp7btg` (= etapa 03 em 7cef578); rodada 1 disparada.
- 17/10 ~22h20 — 👥 1º diagnóstico real no PC: 23 tools (falta `listItemTaxonomy` vs. doc); `getUser`/`listAddresses`
  ok; **`searchOffers` e `getRecommendations` exigem `userLocation: {latitude, longitude}` (objeto)** — o diagnóstico
  mandava lat/lng soltos → 0 resultados. Pedido ao T0: montar argumentos pelo `input_schema` + `--lat/--lng`.
  **Para o T8:** `busca.py`/`checkout.py` devem mandar `userLocation` (e o `demo_server.py` passa a aceitar `userLocation`
  também, para o demo espelhar o real); registrar no `feedback-mcp.md` (doc não cita `userLocation`; 23 × 24 tools).

- 17/10 ~22h40 — T6 ✅ (racional de UX), T4 ✅ (README + `docs/tecnico.md`), T5 ✅ (pesquisa com fontes + formulário),
  T7 ✅ (`docs/avaliacao-jurado.md`: 28,5 → 39/50 projetado). Achados do jurado repassados a T1 (validação semântica,
  agrupamento/promo, `MATCH_LEILAO`, `medicoes`), T2 (rótulo honesto, `fonte_fala`, legenda da afinidade, "bem
  atendidos", ≤ 10 s) e T3 (toast nos itens inertes, `ip_local` no QR).
- 👥 No modo real a sala dizia "Nenhum endereço salvo": `ler_endereco` só lia o formato da doc. Correção
  (`match/03-endereco-localizacao`, engenheiro-chefe): leitor de endereço/coordenadas em formatos variados; no modo
  real o `ClienteIFood` lê o `input_schema` (1 `list_tools`) e converte lat/lng em `userLocation`, descartando
  argumentos não declarados; **`submitOrder` real travado** salvo `IFOOD_MCP_PERMITIR_ENVIO=true`. 187 testes.
- Pendências para T8 (vindas do T4/jurado): `_ler_pagamento` pode escolher Pix na conta de teste → preferir forma
  que não cobra (na entrega/dinheiro) e nunca Pix no modo real; usar `getItem` se trouxer preço promocional/tags;
  buscas em paralelo com limite; `ip_local` em `/api/saude` (backend, `main.py`) — fazer junto com a T9.
- Novas tarefas do jurado: nota "substituída por D9" no §8 da 01b (T14), slide do rastro real com ms (T14), seção
  "avaliar em 5 min" no README (T15), orçamento de tempo do roteiro v2 (T14).

## Fechamento
(preenchido ao concluir)
