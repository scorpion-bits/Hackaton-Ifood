# Roteiro da demo ao vivo — Match (v3, 2 minutos)

Slide 4 do pitch ("Demo ao vivo"). Apresentador: **Thales** (organizador, PC no projetor).
Convidados nos celulares: **Milan**, **Zenon**, **Antonio**.

Frase que guia tudo: *"pedido em grupo sem dor: cada um fala o que quer, o IBits monta, divide a conta e pede pelo iFood"*.

Regras:
- Ninguém lê número de cabeça. Valor, loja e taxa são os que aparecem na tela.
- **Não narrar o Patrocinado.** No modo demonstração, o Poke Verde aparece com rótulo "Patrocinado" e passa a vez;
  seguir em frente. Se perguntarem, resposta curta em `docs/pitch-perguntas-banca.md`.
- **Nunca dizer que os restaurantes têm agentes no iFood.** A disputa é a forma visual de mostrar que o IBits avalia
  cada loja (um avaliador por loja, que só lê o cardápio daquela loja). É simulação nossa.
- Selo na tela: "DEMONSTRAÇÃO · dados simulados" (demo) ou "iFood real · conta de teste" (MCP real). Falar só o que o selo permite.

## Orçamento de tempo (≤ 2:00)

| Bloco | Tempo | Corte se atrasar |
|---|---|---|
| Sala + QR | 0:00–0:12 | — |
| Convidados respondem | 0:12–0:35 | Thales lê as frases enquanto eles digitam |
| Rodar Match + disputa | 0:35–0:48 (disputa ≤ 10 s) | **Pular** assim que a rodada fechar |
| Opções (deck) | 0:48–0:58 | Não ler a lista; só loja + "3 de 3" |
| **Ajustar com o IBits** (momento uau) | 0:58–1:20 | Nunca cortar. Disputa curta: **Pular** |
| Dar match + vaquinha | 1:20–1:42 | Thales marca "Recebi" sem esperar ninguém |
| Confira antes do ok + deslize + rastro | 1:42–2:00 | Pular o rastro |

## Falas e cliques

| Tempo | Quem | Faz (clique) | Fala exata |
|---|---|---|---|
| 0:00–0:12 | Thales | Início → **Fazer um match** → **Em grupo** → cria a sala → QR no projetor | "Sexta à noite. Em vez de discutir no WhatsApp, eu abro o Match. Só eu entro no iFood. Meus amigos leem o QR, sem login." |
| 0:12–0:35 | Milan, Zenon, Antonio | Leem o QR, digitam nome e a frase, tocam **Enviar meu pedido** | Milan (em voz alta): "Japonês e um sorvete, até 45." · Zenon: "Hambúrguer e sorvete, até 50." · Antonio: "Algo barato e vegetariano, até 25." · Thales: "Cada um falou do seu jeito." |
| 0:35–0:38 | Thales | **Rodar Match** | "Agora o IBits monta o pedido." |
| 0:38–0:48 | Thales | A disputa toca sozinha. **Pular** se passar de 10 s | "Para cada loja, o IBits olha só o cardápio dela, que vem do iFood. A tela mostra isso como uma disputa. Preço e prazo vêm do iFood, não da IA." |
| 0:48–0:58 | Thales | **Ver as opções** → 1º cartão | "Kaigan, Gelato e Brasa. Três de três bem atendidos, e cada item diz o porquê." |
| 0:58–1:10 | Thales | Desce até **Ajustar com o IBits**, digita *troca o sorvete do Milan e do Zenon por açaí* e envia | **Momento uau:** "E se mudar de ideia? É só falar com o agente." |
| 1:10–1:20 | Thales | Bolha "Entendi: …" → disputa curta (**Pular**) → cartão com "Atualizado" e "Novo" | "Ele entendeu quem e o quê, refez só o que mudou, e o açaí entrou. Conversa com o agente; a conta, com o código." |
| 1:20–1:25 | Thales | **Dar match** → "É um Match!" → **Cada um paga a sua parte (vaquinha)** | "Agora, a conta. Cada um paga a sua parte; a taxa de cada loja só entre quem pediu dela." |
| 1:25–1:42 | Milan, Zenon, Antonio, Thales | Milan: **Pix** (QR aparece). Zenon e Antonio: **dinheiro**. Thales toca **Recebi** nos três | "O Pix vai para a minha chave, sem intermediário. O pedido só sai com 100% pago." |
| 1:42–1:55 | Thales | "Confira antes do ok" → **Deslize para enviar** | "Três lojas, três carrinhos no iFood, com a taxa de cada um. Nada sai sem o meu ok." |
| 1:55–2:00 | Thales | Abre **Como a IA chegou aqui** (rastro) por 3 s e volta ao slide | "Cada linha é uma tool do MCP do iFood. Do restaurante ao fechamento do carrinho." |

Por que a frase do ajuste tem duas pessoas: com *"troca o sorvete do Milan por açaí"* (só o Milan), o modo demonstração
precisaria de uma 4ª loja para manter o sorvete do Zenon; o IBits avisa "Sorvete de Zenon ficou de fora para o pedido
ficar em até 3 lojas". É honesto, mas gasta tempo explicando. Com as duas pessoas, todo mundo continua atendido.

### MCP real × demonstração (dizer só o que for verdade)

| Situação | O que dizer | O que **não** dizer |
|---|---|---|
| Selo "DEMONSTRAÇÃO · dados simulados" | "Cada linha é uma tool do MCP, com os mesmos nomes da documentação. Aqui, com dados de demonstração; o mesmo código fala com o MCP real." | "chamada real", "pedido real", "taxa real" |
| Selo "iFood real · conta de teste" | "Isso é o MCP do iFood de verdade, numa conta de teste. Lojas, preço e taxa vêm do iFood." | "o pedido foi entregue", "pagamos" |
| Envio no real | "O envio fica travado de propósito: só com o meu ok e com a trava liberada. E nunca pagamos Pix de teste." | — |

> ⚠️ confirmar no PC do Thales (tarefa A1): no modo real, o Match chega ao carrinho da conta de teste com taxa e total do `getCart`.
> Se não chegar até 10h30, a demo é no modo demonstração e a fala do rastro é a da 1ª linha da tabela.

> ⚠️ confirmar no PC do Thales: com chave de IA no `.env`, quem entende a frase do ajuste é o LLM; sem chave, é o
> intérprete determinístico (entende "troca X do Fulano por Y", "mais barato pro Fulano" etc.). Os dois funcionam com a frase do roteiro.

## Resultado esperado (modo demonstração)

Conferido em 18/10/2026 ~03h, rodando o app em modo demonstração (`IFOOD_MCP_MODO=demo`, `LLM_PROVIDER=mock`,
`MATCH_LEILAO=on`) pela API da sala e no navegador (390 × 780). Lojas e preços são fictícios.

**Disputa** (ordem de exibição):
1. IBits: "Pedido novo para 3 pessoas: japonês, sorvete, hambúrguer, algo vegetariano. Quem topa?"
2. Poke Verde (demo) · rótulo Patrocinado: "Aqui não tem o que Antonio pediu dentro de R$ 25. Passo." (**não narrar**)
3. Kaigan Sushi (demo): "Eu atendo 2 de 3 com Sunomono, R$ 12,90. Chego em 45 min."
4. Brasa Burger (demo): "Eu atendo 2 de 3 com Smash burger clássico, R$ 29,90. Chego em 35 min."
5. Gelato Bom Clima (demo): "Eu atendo todo mundo com Sundae de morango, R$ 18,90. Nota 4,9, a melhor da sala."
6. Gelato Bom Clima: "Fecho 2 sorvetes num pedido só: 1 entrega em vez de 2." (juntar itens é regra nossa, não decisão da loja)
7. IBits: "Rodada fechada. Melhor opção: Kaigan Sushi (demo) + Gelato Bom Clima (demo) + Brasa Burger (demo), com 82%
   de afinidade e 3 de 3 bem atendidos. São 3 pedidos, e as taxas aparecem no carrinho antes do seu ok."

**1º cartão antes do ajuste** (82% de afinidade, 3 de 3 bem atendidos, R$ 103,50 só itens):

| Pessoa | Item | Loja | Preço |
|---|---|---|---|
| Milan | Guioza de legumes (6 un.) | Kaigan Sushi (demo) | R$ 22,90 |
| Milan | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 |
| Zenon | Smash burger clássico | Brasa Burger (demo) | R$ 29,90 |
| Zenon | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 |
| Antonio | Sunomono | Kaigan Sushi (demo) | R$ 12,90 |

**Ajuste** *"troca o sorvete do Milan e do Zenon por açaí"* → IBits entende "Milan: açaí no lugar do sorvete" e
"Zenon: açaí no lugar do sorvete" → **1º cartão depois** (marcado "Atualizado"; os açaís com "Novo"):
Kaigan Sushi + Açaí do Campus + Brasa Burger, **76% de afinidade, 3 de 3 bem atendidos, R$ 99,50 só itens**.

| Pessoa | Item | Loja | Preço |
|---|---|---|---|
| Milan | Guioza de legumes (6 un.) | Kaigan Sushi (demo) | R$ 22,90 |
| Milan | Açaí 300 ml puro | Açaí do Campus (demo) | R$ 16,90 |
| Zenon | Smash burger clássico | Brasa Burger (demo) | R$ 29,90 |
| Zenon | Açaí 300 ml puro | Açaí do Campus (demo) | R$ 16,90 |
| Antonio | Sunomono | Kaigan Sushi (demo) | R$ 12,90 |

**Carrinhos** (vaquinha, taxas fictícias do modo demonstração): Kaigan R$ 35,80 + taxa R$ 7,99 = R$ 43,79 ·
Açaí do Campus R$ 33,80 + R$ 3,99 = R$ 37,79 · Brasa R$ 29,90 + R$ 5,99 = R$ 35,89.
**Partes:** Milan R$ 45,80 · Zenon R$ 54,78 · Antonio R$ 16,89 (o orçamento vale para os itens; a taxa vem por cima).
Se perguntarem: "a parte do Zenon passa de 50 porque a taxa de entrega entra depois; o orçamento é dos itens".

Frase que **não** entende (só se sobrar tempo): *"bom dia"* → o servidor responde 422 e a bolha do IBits diz
"Não entendi quem ou o quê. Ex.: "troca o sorvete do Milan por açaí"". O pedido anterior continua na tela.

> Bug visto em 18/10 ~03h (front, não é do pitch): a bolha mostra o nome duas vezes ("Entendi: Milan: Milan: açaí…").
> Se ainda estiver assim na hora, ignorar e seguir a fala. Recado deixado para o engenheiro-chefe.

**Só eu** (se perguntarem ou sobrar tempo): Início → **Fazer um match** → **Só eu** → nome "Thales", frase
*"hambúrguer até R$ 40"* → **Encontrar meu pedido** → Brasa Burger, Smash burger clássico, R$ 29,90 só itens,
1 pedido, 90% de afinidade → **Fechar meu pedido** (paga junto, sem QR).

## Se algo falhar (sem parar de falar)

| Falha | O que fazer |
|---|---|
| QR não abre | Thales lê o link em voz alta ou o convidado usa o link salvo |
| Celular sem rede | Thales responde por ele numa aba anônima ("o Antonio está sem sinal, eu faço por ele") |
| Rodar Match > 10 s | "O IBits está lendo os cardápios." Passou de 20 s: plano B |
| Disputa trava | **Pular** e seguir pelo deck |
| Ajuste responde "Não entendi" | Tocar no chip **Mais barato pra Zenon** (sempre funciona) e seguir: "ele pede outro jeito em vez de chutar" |
| Ajuste demora | "Ele está refazendo o pedido com as lojas." Passou de 15 s: seguir com o cartão anterior |
| Erro na tela / app cai | **Recarregar demo** e ir para o plano B |
| Pix não gera QR | Trocar Milan para dinheiro e seguir |
| MCP real falha no meio (login, busca vazia, carrinho) | Trocar para o modo demonstração (plano B 2) e dizer "vou mostrar no modo demonstração, com o mesmo código" |
| Projetor/PC trava | Vídeo no celular do Zenon; Thales narra por cima com as mesmas falas |

## Plano B (nesta ordem)
1. **Sem a disputa:** `MATCH_LEILAO=off` no `.env` e reiniciar o app. O Match vai direto às opções; o Ajustar continua.
2. **Modo demonstração offline:** `IFOOD_MCP_MODO=demo` e `LLM_PROVIDER=mock`. Não precisa de internet nem de chave.
   Resultado esperado: a seção acima.
3. **Vídeo gravado** (`docs/roteiro-video.md`): `match-demo-rascunho.mp4` (1080p, 98 s, sem voz, falas na tela),
   enviado pelo Zenon ao Thales fora do git em 18/10. Thales narra ao vivo lendo o painel da direita.
   (👥 anotar aqui a pasta exata no PC do Thales.)

## Checklist pré-demo (15 min antes)
- [ ] `.env` no PC do Thales: `IFOOD_MCP_MODO` (demo ou real), `LLM_PROVIDER` (ou `mock`), `MATCH_LEILAO=on`.
      No real: `IFOOD_MCP_PERMITIR_ENVIO` só `true` se a equipe decidiu enviar na conta de teste; nunca pagar Pix de teste.
      Chave Pix do organizador digitada na tela, nunca no git.
- [ ] App iniciado (`iniciar.bat`), aberto em `http://localhost:8000`, **Recarregar demo** clicado.
- [ ] Celulares na mesma rede do PC; link do QR testado num celular (o IP do PC aparece no QR, não `localhost`).
      Firewall do Windows liberando a porta 8000. Rede do evento isolando aparelhos → hotspot do celular.
- [ ] Sala nova (cada aparelho ainda não viu a disputa desta sala).
- [ ] Testar a frase do ajuste uma vez numa sala de ensaio.
- [ ] Zoom 125–150%, tela cheia, notificações desligadas; celulares com brilho alto.
- [ ] Vídeo do plano B aberto no celular do Zenon.
- [ ] 3 ensaios cronometrados do pitch inteiro (alvo ~5 min) — 👥 anotar os tempos aqui.
