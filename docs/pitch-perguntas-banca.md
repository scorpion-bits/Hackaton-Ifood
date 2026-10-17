# Perguntas difíceis da banca — respostas preparadas

Só para o Q&A do pitch. Nada aqui está no MVP, salvo indicação.

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
