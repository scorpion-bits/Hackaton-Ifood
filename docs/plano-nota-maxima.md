# Rumo à nota máxima — o que falta para ganhar

> Escrito pelo agente do Zenon em 18/10 00h50, a pedido do Zenon, a partir do regulamento oficial (`index-v2.html` da
> organização) e das avaliações do jurado simulado (`docs/avaliacao-jurado.md`). **Não substitui o plano vigente**
> (`docs/planos/etapa-05-dupla-milan-zenon.md`): é a lista do que a equipe considera **necessário** para tirar nota
> máxima nos 5 pilares. Cada item tem dono, prazo e status. Quem pegar um item: registre no `docs/quadro.md`.
> Itens 🔒 abrem exceção ao congelamento do `docs/AVISO-EQUIPE.md` e precisam do ok do Milan antes de começar.

## Por que isto é necessário
- O regulamento repete **"um agente que faz pedidos de verdade usando o MCP do iFood"** e pede **"agentes
  conversacionais e ferramentas determinísticas trabalhando juntos"**. Até 18/10 00h47 o Match **não rodou com lojas
  reais** (`docs/mcp-real/` ainda não existe) e a IA real não foi ligada no app.
- Avaliação mais recente (jurado 2 + revisão do Zenon): **~35,5/50**. Com os itens abaixo: **~43–46/50**.

| Pilar (critério oficial) | Hoje | Alvo | Itens que levam ao alvo |
|---|---|---|---|
| Visão & Originalidade — "uso criativo do agente" | 7,5 | 9,5 | N1, N2, O1–O3 |
| Arquitetura & Engenharia — "uso correto do MCP, robustez" | 7 | 9,5 | N1, N2, A1–A3 |
| Design & Experiência — "fluidez da interação, clareza" | 8 | 10 | D1–D6 |
| Impacto — "problema real, viável na prática" | 6 | 9,5 | I1–I4 |
| Comunicação & Pitch — "clareza da demo, storytelling, respostas" | 7 | 9,5 | D1, C1–C3 |

## 0. Os dois que mudam tudo
| ID | O quê | Por quê | Dono | Prazo | Status |
|---|---|---|---|---|---|
| N1 | **Pedido de verdade, gravado.** Diagnóstico `--carrinho` → push de `docs/mcp-real/` → A1 (formato real) → Match com lojas reais de São Carlos até o `getCart` (taxa real) → se um mentor do iFood confirmar, `submitOrder` na conta de teste com pagamento na entrega (**nunca Pix**; `IFOOD_MCP_PERMITIR_ENVIO=true` só para isso). Gravar 30 s de tela (lojas reais, carrinho, pedido, `trackOrder`) | É a missão escrita no regulamento. Mesmo com a demo ao vivo no modo demonstração, o vídeo prova o "pedido de verdade" | 👥 Thales (PC) + Milan (A1); 👥 alguém pergunta ao mentor | 07h | ⬜ |
| N2 | **IA real ligada no app** (chave Groq já no PC do Thales): `python -m app.match.testar_ia`, ajuste de prompts (A3), roteiro + 5 frases livres coerentes | Sem IA real o "agente conversacional" (Ajustar, intérprete, avaliação das lojas) é regra; a banca pergunta "onde está o LLM?" | Milan (A3) + 👥 Thales | 05h | ⬜ |

## 1. Design & Experiência → 10
| ID | O quê | Por quê | Dono | Esforço | Status |
|---|---|---|---|---|---|
| D1 🔒 | **"Modo palco"**: página só de apresentação (ex.: `#/palco/{sala}`) com 4 telas de celular lado a lado no projetor — organizador + 3 convidados — ao vivo. Não é funcionalidade nova do produto: é ferramenta de demo | A banca vê tudo acontecendo ao mesmo tempo (convidados escrevendo, "3 de 3", resultado, pagamento) sem olhar celular; elimina o risco do Wi-Fi do evento isolar aparelhos | Zenon (front, remoto) | ~1,5 h | ⬜ |
| D2 | **Teste de usabilidade com números**: 5 pessoas do evento usam o app no celular; cronometrar tempo do convidado responder, sala → carrinho, onde travou. Corrigir o que aparecer (B4) e citar no racional de UX e no pitch ("convidados responderam em X s, n = 5, SEMCOMP") | Troca a "meta de 30 s (não medida)" por evidência; o critério é "fluidez" | 👥 Antonio + Thales (aplicam); Zenon registra e corrige | ~40 min | ⬜ |
| D3 🔒 | **Detalhes de app grande** (B5): na sala "Milan está escrevendo…" e avatares acendendo; vibração no "É um Match!" e no pagamento confirmado; recibo do convidado ("sua parte R$ X · paga ✓") e aviso "seu pedido saiu"; estados vazio/carregando/erro revisados (skill de UX copy) e auditoria de acessibilidade (skill própria) | É a diferença entre protótipo e "app do iFood" | Zenon (front) | 1–2 h | ⬜ |
| D4 🔒 | **Coerência tela × pitch**: o pitch não fala de Patrocinado, mas a demo ainda mostra o Poke "Patrocinado" → `backend/app/match/politica_lojas.json` sem lojas patrocinadas (1 linha). Título da disputa alinhado ao pitch ("Como o IBits avaliou cada loja") | A banca não pode ver na tela algo que o pitch não explica | Milan (config) + Zenon (título no front) | 10 min | ⬜ |
| D5 🔒 | **Pedido por voz**: botão de microfone no "O que você quer?" (Web Speech API, pt-BR; sem suporte → botão some) | Reforça "conversa com o agente" e acessibilidade | Zenon (front) | ~1 h | ⬜ |
| D6 | **Capturas novas** do app integrado (Só eu, Ajustar, pagamento) no pitch e no PDF dos entregáveis; legendas certas em `docs/entrega/04-interface.md` | O PDF ainda tem as telas antigas (2 legendas erradas) — é o entregável 04 | Zenon | 30 min | ⬜ |

## 2. Impacto → 10
| ID | O quê | Por quê | Dono | Esforço | Status |
|---|---|---|---|---|---|
| I1 | **Experimento WhatsApp × Match**: 2–3 grupos de participantes decidem um pedido como fazem hoje (cronometrado) e depois com o Match. Pitch: "X min no grupo × Y s no Match, N grupos da SEMCOMP" | Dado próprio e inédito; nenhum outro grupo terá | 👥 Antonio + Thales | ~1 h | ⬜ |
| I2 | **Formulário n ≥ 30** (`docs/pesquisa-usuarios.md`) até 09h → preencher os 11 `[preencher]` de `docs/proposta-negocio.md` e o slide 2 | Hoje o slide 2 usa número do Reino Unido | 👥 Antonio (aplica); Zenon preenche | — | ⬜ |
| I3 | **Viabilidade em números próprios**: com a IA real, medir custo e tempo de um Match (`leilao.medicoes`, chamadas de IA, tokens, segundos) → "cada pedido em grupo custa R$ 0,00X de IA e leva Y s" | O critério diz "viável de usar na prática" | Milan (mede) → Zenon (pitch/proposta) | 20 min | ⬜ |
| I4 | **Conta de impacto honesta**: tabela de cenários marcada como hipótese ("se 1% dos 180 mi de pedidos/mês forem ocasiões de grupo…", premissas explícitas, fonte do 180 mi em `docs/pesquisa-mercado.md`) + os 3 ganhadores: quem pede (ninguém vira gerente; quem tem restrição não fica de fora), restaurante (pedido maior), iFood (ocasiões novas, mais lojas por sessão) | Impacto concreto sem inventar número | Zenon (proposta + pitch) | 40 min | ⬜ |

## 3. Visão & Originalidade → 10
| ID | O quê | Por quê | Dono | Esforço | Status |
|---|---|---|---|---|---|
| O1 | **Nomear a categoria**: "o primeiro agente que pede por um grupo, não por uma pessoa" — **pedido coletivo** (todos, inclusive o Ailo, fazem agente para 1 pessoa) | Uma frase que a banca repete na deliberação | Zenon (pitch, slide 1 e 8) | 15 min | ⬜ |
| O2 | **Mostrar o que é impossível à mão**: narrar o conflito do roteiro (Antonio vegetariano com R$ 25 + Milan japonês e sorvete + 3 lojas) como "ninguém fica de fora — e o que ficou, o IBits diz por quê" | Mostra o otimizador justo, que é o coração técnico | Zenon (roteiro); 👥 Thales narra | 15 min | ⬜ |
| O3 | **Visão em 3 horizontes (1 slide)**: hoje (link/QR, até 3 lojas) → próximo (o IBits **dentro do grupo de WhatsApp**, onde o grupo já está, via Ailo — "@IBits monta o pedido da turma"; recorrência "toda sexta da república"; memória do grupo) → depois (**churrasco da turma no Mercado iFood**: cada um diz o que come e bebe e a lista sai dividida — o MCP já tem a vertical de mercado; restaurantes plugando os próprios agentes, como visão honesta) | Visão grande e plausível, dentro do ecossistema iFood | Zenon (pitch + proposta §7) | 30 min | ⬜ |

## 4. Arquitetura & Comunicação
| ID | O quê | Por quê | Dono | Esforço | Status |
|---|---|---|---|---|---|
| A1 | **CI no GitHub**: workflow que roda `pytest` + `npm run build` a cada push; selo no README | Quem abrir o repositório vê os testes passando ("qualidade do código") | Milan (integração) | 20 min | ⬜ |
| A2 | **Feedback do MCP com o uso real**: busca, carrinho, pagamento, latência medida, resposta do mentor sobre `submitOrder` | É o entregável destacado no regulamento ("insumo direto para o time") | Milan (depois da A1) | 30 min | ⬜ |
| A3 | **Docs com o que mudou**: Ajustar com o IBits (C14), Só eu (C15) e pedido real (C16) em `docs/racional-ux.md`, `docs/proposta-negocio.md`, `README.md` e `docs/tecnico.md` (este com ok do Milan) | Os entregáveis 02, 03 e 05 ainda quase não citam o Ajustar, que é a interação central | Zenon | 1 h | ⬜ |
| C1 | **Pitch**: abrir perguntando "quem aqui já foi o gerente do pedido?" (mãos levantadas); o Thales conta uma história real dele; incluir O1–O3, I1–I4 e a prova do N1 | Storytelling + dados próprios | Zenon (texto) + 👥 Thales | 30 min | ⬜ |
| C2 | **3 ensaios cronometrados + vídeo de plano B** (`docs/roteiro-video.md`) | Pitch de 5 min sem sobra | 👥 Thales + Milan | 1 h | ⬜ |
| C3 | **Folha de respostas para a banca impressa** (`docs/pitch-perguntas-banca.md`, atualizada com N1–N2 e I3) | "Qualidade das respostas às perguntas" | Zenon (texto) + 👥 imprimir | 20 min | ⬜ |

## Fora (decidido)
- **"O jurado participa"** (um avaliador lê o QR e pede ao vivo): **não entra**. O pitch tem só 5 min e não queremos
  gastar tempo nem correr risco com isso (decisão do Zenon, 18/10 00h50).

## Se só der para fazer 6
1. N1 pedido real gravado · 2. N2 IA real · 3. I1 + I2 experimento e formulário · 4. D1 modo palco 🔒 ·
5. D2 teste de usabilidade com números · 6. O1 + O3 "pedido coletivo" e visão (WhatsApp, churrasco).

## Linha do tempo sugerida (BRT)
| Até | O quê |
|---|---|
| 03h | N2 (IA real), D4, A1 (CI), D1 modo palco, A3 docs |
| 07h | N1 (MCP real e pedido gravado), D3, D5, D6, I4, O1–O3 |
| 09h | I1 experimento, I2 formulário, D2 usabilidade (com o evento acordado) → I3 números no pitch |
| 10h30 | **congelar código**; C1 pitch final, C3 folha da banca |
| 12h30 | C2 ensaios e vídeo; PDFs da entrega e do pitch gerados de novo; submissão |
