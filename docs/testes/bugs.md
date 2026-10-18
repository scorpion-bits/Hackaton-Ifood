# Bugs encontrados nos testes

> Só o agente do Thales cria linhas. Quem corrige muda o status para ✅ e põe o commit.
> Gravidade: 🔴 bloqueia a demo · 🟡 atrapalha · ⚪ detalhe. Área: back (Milan) · front (Zenon).

| # | Hora | Passo do roteiro | O que aconteceu | Esperado | Gravidade | Área | Status / commit |
|---|---|---|---|---|---|---|---|
| 1 | 18/10 00h48 | 3.2 MCP real (diagnóstico `--carrinho`, `docs/mcp-real/createCart.json`) | `createCart` só com `merchantId` volta `MISSING_REQUIRED_FIELDS`: "addressId, merchantId, and items are required when orderId is absent". O `checkout._montar_loja` chama `createCart(merchantId, addressId)` **sem `items`** e depois `addItemToCart` | `createCart` já com `items` (pelo menos o 1º item) e o resto por `addItemToCart` | 🔴 | back | ⬜ |
| 2 | 18/10 00h48 | 3.2 MCP real (`docs/mcp-real/createCart.json`) | O erro do MCP real vem como resposta **normal** (`{"error": {"code": …}}`, sem `isError`) — o diagnóstico marcou `ok` e o app pode seguir sem `cartId` | resposta com chave `error` tratada como erro da tool (mensagem legível com o `code`) | 🟡 | back | ⬜ |
| 3 | 18/10 00h48 | 3.2 MCP real (`tools.json`) | `listPaymentMethods` real exige `merchantId` (único campo, obrigatório); o `checkout._montar_loja` chama com `cartId` | chamar com o `merchantId` da loja | 🔴 | back | ⬜ |
| 4 | 18/10 00h48 | 3.1 MCP real (`docs/mcp-real/listAddresses.json`) | Conta de teste **sem endereço salvo** (`results: []`): sem `addressId` não há carrinho, e o Match real para em "sem endereço" | fluxo `createAddress` (2 passos: geocodifica → confirma `candidateId`) ou 👥 cadastrar um endereço na conta de teste antes da demo | 🔴 | back / 👥 | ⬜ |
| 5 | 18/10 00h48 | 3.2 MCP real (`docs/mcp-real/getRecommendations.json`) | `getRecommendations` exige `contentMode` (enum: RECOMMENDED, RECENT_ORDERS, FAVORITE_MERCHANTS, BEST_DEALS, …); o diagnóstico mandou vazio | mandar `contentMode=RECOMMENDED` se o app usar essa tool | ⚪ | back | ⬜ |
