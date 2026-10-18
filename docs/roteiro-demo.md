# Roteiro da demo ao vivo — Match (v2, 2 minutos)

Slide 4 do pitch ("Demo ao vivo"). Apresentador: **Thales** (organizador, PC no projetor).
Convidados nos celulares: **Milan**, **Zenon**, **Antonio**. Selo DEMONSTRAÇÃO visível, salvo se a demo estiver no MCP real.

Regras:
- Ninguém lê número de cabeça. Valor, loja e taxa são os que aparecem na tela.
- Os textos do quadro e da disputa abaixo são a saída real do motor com `LLM_PROVIDER=mock` e o MCP de demonstração
  (`backend/tests/test_motor.py` trava o resultado). Com IA real, a fala das lojas pode mudar; os números, não.

## Orçamento de tempo (≤ 2:00)

| Bloco | Tempo | Corte se atrasar |
|---|---|---|
| Sala + QR | 0:00–0:15 | — |
| Convidados respondem | 0:15–0:40 | Thales lê as frases enquanto eles digitam |
| Rodar Match + **disputa** | 0:40–1:00 (disputa ≤ 10 s) | **Pular** assim que o IBits fechar a rodada |
| Deck: **1 gesto** + "É um Match!" | 1:00–1:10 | Botão "Dar match" em vez do gesto |
| Separado + pagamento comprimido | 1:10–1:35 | Thales marca "Recebi" sem esperar ninguém |
| Deslize para enviar + rastro | 1:35–2:00 (rastro 5 s) | Pular o "Atualizar" do pedido |

## Falas e cliques

| Tempo | Quem | Faz (clique) | Fala exata do Thales |
|---|---|---|---|
| 0:00–0:15 | Thales | Início → banner "Pedir em grupo? Dê um Match" → cria a sala → QR no projetor | "Sexta à noite. Em vez de discutir no WhatsApp, eu abro o Match. Só eu entro no iFood. Meus amigos leem o QR, sem login." |
| 0:15–0:40 | Milan, Zenon, Antonio | Leem o QR, digitam nome e a frase, tocam em **Enviar meu pedido** | Milan (em voz alta): "Japonês e um sorvete, até 45." · Zenon: "Hambúrguer e sorvete, até 50." · Antonio: "Algo barato e vegetariano, até 25." · Thales, quando os 3 ficam "respondeu": "Cada um escreveu do seu jeito, em segundos." |
| 0:40–0:43 | Thales | **Rodar Match** | "Agora as lojas vão disputar o nosso pedido." |
| 0:43–0:53 | Thales | Tela "A disputa pelo seu pedido" toca sozinha. Toca **Pular** se passar de 10 s | **Momento uau, narração do Patrocinado:** "Cada restaurante tem um agente vendedor, que só enxerga o próprio cardápio. Olha quem fala primeiro: o Poke Verde. Ele é **Patrocinado**, pagou para aparecer primeiro… e atende só 1 de 3. A sorveteria decide sozinha: 'fecho 2 sorvetes num pedido só, 1 entrega em vez de 2'. Pagar não compra o pedido." |
| 0:53–1:00 | Thales | Fechamento do IBits na tela → **Ver as opções** | "O IBits, nosso agente comprador, fechou: Kaigan, Gelato e Brasa, 3 de 3 bem atendidos." |
| 1:00–1:10 | Thales | Deck: **1 deslize para a direita** no 1º cartão → "É um Match!" | "Um gesto. É um Match." |
| 1:10–1:15 | Thales | **Separado** | "Cada um paga a sua parte; a taxa de cada loja é dividida só entre quem pediu dela." |
| 1:15–1:35 | Milan, Zenon, Antonio, Thales | Milan: **Pix** (QR aparece). Zenon e Antonio: **dinheiro**. Thales toca **Recebi** nos três | "O Pix vai direto para a minha chave, sem intermediário. E o pedido só sai com 100% pago." |
| 1:35–1:50 | Thales | "Confira antes do ok" → **Deslize para enviar** | "Os preços e as taxas vieram do iFood, não da IA. São 3 lojas, 3 pedidos, e a tela avisou antes. Nada sai sem o meu ok." |
| 1:50–2:00 | Thales | Abre o **rastro** do MCP (5 s) e volta para o slide | **Fechamento:** "E cada linha aqui é uma tool do MCP do iFood, com o tempo de cada chamada. Ninguém virou gerente do pedido." |

### MCP real × demonstração (dizer só o que for verdade)

| Situação | O que dizer no rastro | O que **não** dizer |
|---|---|---|
| Modo demonstração (selo DEMONSTRAÇÃO) | "Cada linha é uma tool do MCP, com os mesmos nomes da documentação. Hoje rodamos com dados de demonstração; o mesmo código fala com o MCP real." | "chamada real", "pedido real", "taxa real" |
| MCP real, conta de teste (selo "iFood real · conta de teste") | "Isso é uma chamada real ao MCP do iFood, em conta de teste. O envio está travado de propósito: não pagamos pedido de teste." | "o pedido foi entregue" |
| No MCP real não há Patrocinado | Pular a narração do Patrocinado na tela; dizer no slide 5: "no modo real nenhuma loja é patrocinada; mostramos o Patrocinado no modo demonstração" | — |

## Resultado esperado (modo demonstração)

Disputa (ordem de exibição):
1. IBits: "Pedido novo para 3 pessoas: japonês, sorvete, hambúrguer, algo vegetariano. Quem topa?"
2. Poke Verde (demo) · PATROCINADO: "Eu atendo 1 de 3 com Suco verde 400 ml, R$ 12,90. Chego em 30 min."
3. Kaigan Sushi (demo): "Eu atendo 2 de 3 com Sunomono, R$ 12,90. Chego em 45 min."
4. Brasa Burger (demo): "Eu atendo 2 de 3 com Smash burger clássico, R$ 29,90. Chego em 35 min."
5. Gelato Bom Clima (demo): "Eu atendo todo mundo com Sundae de morango, R$ 18,90. Nota 4,9, a melhor da sala."
6. Gelato Bom Clima (réplica): "Fecho 2 sorvetes num pedido só: 1 entrega em vez de 2."
7. IBits: "Rodada fechada. Melhor opção: Kaigan Sushi (demo) + Gelato Bom Clima (demo) + Brasa Burger (demo), com 82%
   de afinidade e 3 de 3 bem atendidos. São 3 pedidos, e as taxas aparecem no carrinho antes do seu ok."

No modo mock todas as falas são "texto conferido" (modelo determinístico). Com IA real, o rótulo pode virar
"agente da loja (IA)".

1ª combinação do deck (82% de afinidade, 3 de 3 bem atendidos):

| Pessoa (orçamento) | Item | Loja | Preço |
|---|---|---|---|
| Milan (até R$ 45) | Guioza de legumes (6 un.) | Kaigan Sushi (demo) | R$ 22,90 |
| Milan | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 |
| Zenon (até R$ 50) | Smash burger clássico | Brasa Burger (demo) | R$ 29,90 |
| Zenon | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 |
| Antonio (até R$ 25, vegetariano) | Sunomono | Kaigan Sushi (demo) | R$ 12,90 |

- Itens: Milan R$ 41,80 · Zenon R$ 48,80 · Antonio R$ 12,90 · **R$ 103,50 sem taxa**.
- Taxas de demonstração (fictícias): Kaigan R$ 7,99 · Brasa R$ 5,99 · Gelato R$ 4,99. Vale o que o carrinho mostrar.
- "Afinidade" = quanto os pratos combinam com o que cada um pediu, segundo a IA (média por pessoa). Se perguntarem,
  dizer isso; não é satisfação medida.

## Se algo falhar (sem parar de falar)

| Falha | O que fazer |
|---|---|
| QR não abre | Thales lê o link em voz alta (tela "O link não abre no celular?") ou o convidado usa o link salvo |
| Celular sem rede | Thales responde por ele numa aba anônima ("o Antonio está sem sinal, eu faço por ele") |
| Rodar Match > 10 s | "Os agentes das lojas estão olhando o cardápio." Passou de 20 s: plano B |
| Disputa trava ou demora | **Pular**. Se a disputa não abrir, seguir pelo deck e narrar o Patrocinado no slide 5 |
| Erro na tela / app cai | **Recarregar demo** e ir para o plano B |
| Pix não gera QR | Trocar Milan para dinheiro e seguir |
| Projetor/PC trava | Vídeo no celular do Zenon; Thales narra por cima com as mesmas falas |

## Plano B (nesta ordem)
1. **Sem a disputa:** `MATCH_LEILAO=off` no `.env` e reiniciar o app. O Match vai direto ao deck; a narração do
   Patrocinado vai para o slide 5 (capturas `f4-disputa` e `f5-deck`).
2. **Modo demonstração offline:** `IFOOD_MCP_MODO=demo` e `LLM_PROVIDER=mock`. Não precisa de internet nem de chave.
3. **Vídeo gravado** (`docs/roteiro-video.md`): `[preencher: caminho do arquivo no PC e no celular do Zenon]`.

## Checklist pré-demo (15 min antes)
- [ ] `.env` no PC do Thales: `IFOOD_MCP_MODO` (demo ou real), `LLM_PROVIDER` (ou `mock`), `MATCH_LEILAO=on`,
      `IFOOD_MCP_PERMITIR_ENVIO=false`. Chave Pix do organizador digitada na tela, nunca no git.
- [ ] App iniciado (`iniciar.bat`), aberto em `http://localhost:8000`, **Recarregar demo** clicado.
- [ ] Celulares na mesma rede do PC; link do QR testado num celular (IP do PC, não `localhost`):
      `[preencher: http://IP-DO-PC:8000]`. Firewall do Windows liberando a porta 8000.
- [ ] Cada aparelho ainda não viu a disputa desta sala (sala nova resolve).
- [ ] Zoom 125–150%, tela cheia, notificações desligadas; celulares com brilho alto.
- [ ] Vídeo do plano B aberto no celular do Zenon.
- [ ] 3 ensaios cronometrados. Tempos: `[preencher]` · `[preencher]` · `[preencher]`.
