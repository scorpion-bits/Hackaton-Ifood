# MCP do iFood (consumidor) — resumo de trabalho

Fonte oficial: https://mcp-developer.ifood.com.br/pt-BR/docs/guides · texto completo para LLM:
https://mcp-developer.ifood.com.br/llms-full.txt (baixe e leia por trecho; não colar inteiro no contexto).
Verificado ao vivo em 17/10/2026 (sem credenciais) o que está marcado ✅.

## Conexão
- ✅ Endpoint MCP (Streamable HTTP): `POST https://consumer-mcp.ifood.com.br/marketplace` (sem token → 401).
- ✅ Metadados: `/.well-known/oauth-protected-resource/marketplace` → autorização em `https://id.ifood.com.br`.
- ✅ OAuth: `https://id.ifood.com.br/authorize` e `/token`; `authorization_code` + `refresh_token`; **PKCE S256**;
  client secret (`client_secret_basic` ou `_post`). **Sem registro dinâmico** → `client_id`/`secret` do Portal.
- Access token ~1h, refresh ~30 dias (doc). Redirect URI exata, sem curinga.
- ⚠️ A doc cita `auth.ifood.com`, `api-mcp.ifood.com/v3/*`, `mcp.ifood.dev`, `@ifood/mcp-sdk`: **não existem**.
- ⚠️ Login por QR ("Pending Action", `/device`): está na doc, não nos metadados reais → NÃO VERIFICADO.

## Tools (24) — confirmar nomes com `list_tools` no primeiro acesso
| MCP | Tools | Notas |
|---|---|---|
| User | `getUser`, `listAddresses`, `createAddress` | `listAddresses` primeiro em todo fluxo; traz `topMerchantTypes`, pedidos por dia/turno. `createAddress` geocodifica (2 passos com `candidateId`). |
| Offer Discovery (só leitura) | `searchOffers`, `browseOffers`, `getRecommendations`, `listItemTaxonomy`, `getMerchant`, `getItem` | `query` só descritivo; preço/distância/tempo vão em `refinements`. `resultKind`: `MERCHANT` ou `ITEM`. `getItem` traz `optionGroups` e preço promocional. |
| Cart (13) | `createCart`, `getCart`, `getCartDeliveryMethods`, `addItemToCart`, `updateCartItem`, `removeItemFromCart`, `listVouchers`, `setVoucher`, `removeVoucher`, `setCartDelivery`, `listPaymentMethods`, `setCartPayment`, `submitOrder` | 1 carrinho = 1 restaurante + 1 endereço. `createCart` **não é idempotente**. Não confundir `itemId`, `cartItemId`, `cartId`. |
| Order Tracking (só leitura) | `trackOrder`, `getOrder` | `status = {code, description}`; seguir `agentHints.retryMessage` e parar em `pollingStop`. |

## Sequência obrigatória do pedido
`listAddresses` → `searchOffers` → `getMerchant` → `getItem` → `createCart` → `addItemToCart` →
`getCartDeliveryMethods` → `setCartDelivery` → `listPaymentMethods` → `setCartPayment` → (`listVouchers` → `setVoucher`)
→ `getCart` (conferir total) → **`submitOrder({cartId, userConsent: true})`** → `trackOrder`.

`userConsent: true` só depois da confirmação humana na tela (regra nossa e do iFood).

## Contas de teste (Portal) — [doc](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/test-account)
- Só aparecem **depois que o agente é aprovado** (total ou parcialmente).
- Portal gera e-mail `@test.ifood.com.br` + telefone inválido (DDD terminado em 0); nada recebe SMS/WhatsApp.
- Login no id.ifood normal: e-mail ou telefone de teste + código gerado no Portal ("Gerar código" → código de e-mail e
  de telefone; uso único; "Gerar novamente" se expirar).
- Até **10 por usuário do Portal**; **apagadas 15 dias após a criação**. Pedido não vai ao restaurante.
- ⚠️ **Não pagar o Pix de pedido de teste: não há reembolso.**
