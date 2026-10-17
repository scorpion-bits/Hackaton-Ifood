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

## "Quanto custa o LLM? Escala?"
- Poucas chamadas de LLM por Match: entender o desejo de cada pessoa e dar nota a uma lista curta de pratos
  (até 8 por pessoa). Combinar e somar é código, sem LLM. Não temos número medido de custo por Match
  `[preencher: medir tokens por Match no ensaio, se der]`.
- Sem chave de LLM, o modo determinístico roda a demo inteira.

## "E a privacidade (LGPD) do convidado sem login?"
- O convidado informa só um nome (pode ser apelido), a frase e o orçamento. Nada de CPF, e-mail ou telefone.
- "Lembrar de mim" fica só no celular dele. A conta do iFood e o pagamento ao iFood são só do organizador.
- No protótipo, a chave Pix do organizador fica no banco local, nunca no git.
