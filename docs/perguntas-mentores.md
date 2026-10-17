# Perguntas para o time do iFood

Anotar a resposta embaixo de cada uma, com o nome de quem respondeu e a hora.

## 🔴 Desbloqueiam agora
1. **Aprovação do agente:** "Criamos nosso agente no Portal. Quanto tempo demora para ele ser aprovado? Tem alguém para quem a gente possa avisar?" (sem aprovação não recebemos o client ID/secret e ficamos parados)
   - R:
2. **Carrinhos:** um mesmo usuário pode ter **dois carrinhos abertos ao mesmo tempo**, de restaurantes diferentes? E dá para enviar dois pedidos seguidos?
   - R:
3. **Login por QR code:** "A documentação fala de um login por QR code. Isso funciona no hackathon ou é só o login pelo navegador?" (o login pelo navegador funciona com certeza; o de QR não deu sinal nos nossos testes)
   - R:
4. **Contas de teste:** "As contas de teste duram quanto tempo? E como elas são novas, a parte de 'recomendados / pedidos recentes' funciona ou volta vazia?" (o vídeo fala "16 G", talvez 16 dias; a ideia do "o de sempre" depende do histórico)
   - R: **validade já respondida pela doc: apagadas 15 dias após a criação.** Falta só: o histórico funciona?
5. **Entrega:** onde e como submetemos os 6 entregáveis (repositório, PDF, formulário)? Quanto dura o pitch, e a demo precisa ser ao vivo?
   - R:

## 🟡 Técnicas, para o MCP
6. A taxa de entrega aparece só em `getCartDeliveryMethods`, depois de criar o carrinho? Ou dá para ver antes, na busca?
   - R:
7. O `getMerchant` devolve o cardápio inteiro, com descrição dos itens? Existe algum campo estruturado de restrição (vegano, sem glúten, sem lactose)?
   - R:
8. Qual é o limite de chamadas (rate limit) por agente ou usuário? E um carrinho abandonado expira sozinho?
   - R:
9. Com conta de teste, quais formas de pagamento funcionam além do Pix? O status do pedido avança sozinho até "entregue"? Em quanto tempo?
   - R:
10. A doc cita `auth.ifood.com`, `api-mcp.ifood.com` e o pacote `@ifood/mcp-sdk`, mas não encontramos nenhum deles. O certo é só `consumer-mcp.ifood.com.br/marketplace` com `id.ifood.com.br`?
    - R:

## 🟢 Produto e avaliação
11. Que tipo de solução vocês **ainda não viram** nenhum grupo fazer? E o que já está repetido?
    - R:
12. Na prática, o pedido em grupo é uma dor que o iFood vê? Vocês podem compartilhar algum dado ou indício que a gente possa citar no pitch? (só vira número no pitch se vier com fonte)
    - R:
13. Para a banca, "uso correto do MCP" significa o quê? Seguir a ordem das tools, tratar erros, pedir consentimento?
    - R:
14. Que formato de feedback sobre o MCP é mais útil para o time de vocês: lista de problemas, sugestões, ou registro de erros com horário?
    - R:
