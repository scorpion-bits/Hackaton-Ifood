# Perguntas difíceis da banca — respostas preparadas

Só para o Q&A do pitch. Nada aqui está no MVP, salvo indicação. Resposta em até 20 s; se não souber, dizer "não
medimos" e o que faríamos. As perguntas difíceis do jurado simulado (`docs/avaliacao-jurado.md`) estão no fim.

## "E se o grupo quiser pagar na entrega?"
- A doc do MCP (`listPaymentMethods`) cita crédito, débito, Pix e vale-refeição; "na entrega" não aparece → não
  prometemos.
- A dor é real: com 2 lojas são **2 entregadores, 2 cobranças, horários diferentes** — quem recebe precisa saber
  quanto pagar a cada um. Resposta: "o Match já separa o total por loja; se o iFood expuser pagamento na entrega,
  a tela mostra 'R$ X ao entregador da loja A, R$ Y ao da loja B' e o acerto de contas do grupo continua igual".
- Em países onde dinheiro na entrega é comum (América Latina), essa separação é ainda mais importante (pesquisa em
  `docs/planos/etapa-01b-match-estrategia.md` §11).

## "Por que não junta tudo numa entrega só, como a Uber Eats?"
- A taxa única da Uber/DoorDash é logística interna delas (fontes na §11). O MCP é 1 carrinho = 1 loja. O Match
  mostra o custo real de dividir e só divide quando compensa. Se o iFood abrir isso, o otimizador já pondera lojas.

## "O iFood já tem o Ailo. Qual a diferença?"
- O Ailo é conversa de 1 pessoa. O Match compõe para **N pessoas**, com orçamentos e restrições diferentes, entre
  lojas, com justiça e números explicados. É uma capacidade que o Ailo poderia usar.

## "Por que não é só um chatbot?"
- Um chatbot conversa com 1 pessoa. O Match junta **N pessoas**, com orçamentos e restrições diferentes, e escolhe a
  combinação de itens e lojas que atende todo mundo, com justiça (ninguém fica sem opção boa) e com a conta pronta.
- A IA entende o desejo e explica a escolha; a decisão numérica (orçamento, soma, taxa, divisão) é código.

## "E se o LLM errar o preço?"
- O LLM nunca dá preço. Preço, taxa, prazo e disponibilidade só vêm das respostas das tools do MCP (`getMerchant`,
  `getCart`). Antes de enviar, o app chama `getCart` de novo; se o total mudou, para e pede um novo ok.

## "Como evitam pedido sem consentimento?"
- `submitOrder` só é chamado com `userConsent: true` depois que o organizador confirma na tela, vendo cada pedido,
  loja e total. No modo separado, só depois de 100% pago. O rastro mostra cada tool chamada.

## "E se um pagamento falhar ou alguém não pagar?"
- O pedido não sai enquanto não estiver 100% pago. Acabou o prazo: o organizador escolhe cobrir a parte, tirar os
  itens dessa pessoa (as partes são recalculadas) ou cancelar o Match.
- Se um pedido falhar **depois** de enviado o outro: o app para, mostra qual loja falhou e propõe outra loja para
  aquela parte. O MCP não tem cancelamento; por isso validamos todos os carrinhos antes do 1º envio.

## "E a privacidade (LGPD) do convidado sem login?"
- O convidado informa só um nome (pode ser apelido), a frase e o orçamento. Nada de CPF, e-mail ou telefone.
- "Lembrar de mim" fica só no celular dele. A conta do iFood e o pagamento ao iFood são só do organizador.
- No protótipo, a chave Pix do organizador fica no banco local, nunca no git.

---

## Perguntas difíceis do jurado simulado (pitch v2)

### "É agente de verdade ou um workflow fixo?"
- As duas coisas, de propósito. A **ordem das tools** e **tudo que envolve dinheiro** ficam em código: é o que a doc
  do MCP pede (`listAddresses` antes da busca, `getCart` antes de enviar, consentimento) e é o que dá confiança.
- A IA decide o que não dá para fixar: o que buscar a partir da frase de cada pessoa, quanto cada prato combina com
  ela, e, no agente de cada loja, **quais itens oferecer a quem** e o que dizer. A réplica "fecho 2 sorvetes num
  pedido só" é decisão do agente da loja (agrupar para economizar entrega), não um texto fixo nosso.

### "Quem roda o agente do restaurante? A loja consentiu?"
- Hoje, **ninguém da loja**: simulamos o agente de cada loja com o cardápio público que o próprio MCP devolve. Ele
  só oferece itens que existem, com o preço do MCP. Por isso o rótulo na tela é honesto ("texto conferido" ou
  "agente da loja (IA)") e as lojas da demo são fictícias.
- Em produção: a loja **pluga a própria política** (promoção, combo) pelo Portal do Parceiro; o iFood controla as
  regras (validação, rótulo, nada de número inventado). A loja controla a oferta; o iFood controla o jogo.

### "Por que uma loja pagaria Patrocinado se não ganha?"
- Porque ela compra **atenção**, não a decisão, e isso já é o modelo do iFood Ads: leilão por visita, e o próprio
  iFood diz "Dinheiro sozinho não compra posição" ([Blog iFood Parceiros, 18/09/2026](https://blog-parceiros.ifood.com.br/como-usar-ifood-ads-para-crescer-na-plataforma/)).
- A patrocinada fala primeiro para um grupo inteiro que está decidindo agora. Quando ela **atende** o grupo, ganha;
  quando não atende, aparece para quem pode voltar sozinho. Se o pagamento comprasse a escolha, ninguém confiaria no
  agente comprador e o canal perderia valor para todo mundo, inclusive para quem paga.
- O que medir no piloto: CTR do lance patrocinado e se o NPS e a conversão das salas caem com o rótulo.

### "Quanto custa o LLM com 8 agentes? E o rate limit?"
- Até 8 lojas na disputa, **uma chamada por loja, em paralelo**, com tempo máximo de ~6 s cada; mais o intérprete e
  o juiz. A conta, a escolha e o carrinho são código, sem LLM.
- Custo por Match: **não medimos ainda** com IA real `[preencher depois do ensaio com IA real: chamadas e tempo de
  leilao.medicoes]`.
- Erro 429, timeout ou resposta inválida → **fallback determinístico** (top 2 por nota e fala por modelo). A demo
  inteira roda sem chave nenhuma. Em produção: cache de cardápio por loja e lote de chamadas.

### "E a latência no MCP real?"
- Cada chamada aparece no rastro com o tempo em ms. Medido no PC: `[preencher: searchOffers ___ ms, getCart ___ ms,
  Match inteiro ___ s]`. Se não tiver medido: "não medimos o fluxo inteiro no real; o rastro mostra cada chamada".
- A disputa tem limite: ~6 s por agente em paralelo; meta ≤ 8 s com IA real.

### "A Rappi já faz pedido em grupo."
- Faz, e está no nosso slide comparativo ([Supervarejo, 11/2023](https://www.supervarejo.com.br/varejo/rappi-lanca-recurso-que-permite-fazer-pedidos-em-grupo)).
  Lá cada pessoa escolhe à mão, numa loja. No Match: a **IA compõe** o pedido do grupo a partir de frases, junta
  **até 3 lojas**, as **lojas disputam** o pedido com agentes, e a **vaquinha** trava o envio até 100% pago.

### "O que é esse 82% (ou 92%) de afinidade?"
- É a média, por pessoa, da nota que a IA deu para quanto cada prato combina com o que a pessoa escreveu (0 a 100).
  A legenda está no cartão. **Não é satisfação medida** e não é promessa; é para comparar as opções entre si.
- "Bem atendidos" = pessoas com nota média ≥ 0,5.

### "Escala para 15 pessoas?"
- Hoje não: até **6 pessoas por sala** (limite do otimizador, que testa as combinações). Para 15+: poda por loja
  (cada agente oferece no máximo 2 itens por pessoa, o que já reduz muito) e votação no deck. Dizemos o limite, não
  escondemos.

### "E alergia?"
- O cardápio nem sempre informa. A restrição só é afirmada se o item tem a etiqueta (tag) no MCP; se não tem, aparece
  "segundo a descrição" e o aviso "pode não estar informado, confirme com a loja". O agente da loja não pode dizer
  "sem lactose" se nenhum item ofertado tem essa etiqueta (a fala é trocada pelo texto pronto).
- Para alergia grave, a resposta honesta é: confirme com a loja. Não prometemos segurança alimentar.

### "Por que a doc diz 24 tools e vocês falam em 23?"
- Porque o `list_tools` real devolveu 23 (falta `listItemTaxonomy`). Está no nosso feedback do MCP, com o
  `userLocation` que a doc não cita e é obrigatório no `searchOffers`.
