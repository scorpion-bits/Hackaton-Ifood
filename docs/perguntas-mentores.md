# Perguntas para o time do iFood

Anotar a resposta embaixo de cada uma, com o nome de quem respondeu e a hora.

## 🔴 Desbloqueiam agora
1. **Homologação:** quanto tempo leva a aprovação do agente no Portal? Quem aprova, e dá para acelerar se avisarmos alguém?
   - R:
2. **Carrinhos:** um mesmo usuário pode ter **dois carrinhos abertos ao mesmo tempo**, de restaurantes diferentes? E dá para enviar dois pedidos seguidos?
   - R:
3. **Login:** o fluxo "Pending Action" (QR code / device code) que aparece na doc funciona para os nossos agentes? Ele não aparece nos metadados do `id.ifood.com.br`.
   - R:
4. **Contas de teste:** quanto tempo valem? O vídeo fala "16 G" (16 dias?). Elas têm histórico de pedidos, para testar `getRecommendations` e os dados de comportamento?
   - R:
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
