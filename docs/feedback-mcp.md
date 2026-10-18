# Feedback sobre o MCP do iFood (entregável 06)

## Top 4 por gravidade

1. **Conta de teste não consegue salvar endereço (`ADR-2001`).** `createAddress` geocodifica (`SINGLE`), mas salvar
   falha sempre com `ADDRESS_CREATION_FAILED` / `ADR-2001` ("unexpected status: 400 Bad Request") nas **3 contas de
   teste**, inclusive repetindo o exemplo exato da doc do portal. O erro não está documentado e vem com
   `retryable: true`, mas nunca passa. Sem endereço não há `createCart`, ou seja, nenhum pedido. Pedimos ajuda aos mentores.
2. **`userLocation` exigido e sem documentação.** `searchOffers` e `getRecommendations` recusam `latitude`/`longitude`
   soltos (como nos exemplos da doc) e pedem `userLocation: {latitude, longitude}`. No 1º teste real nenhuma busca
   funcionou. Contornamos lendo o `input_schema` do `list_tools` e montando o objeto (`backend/app/ifood_mcp/cliente.py`).
3. **23 tools no servidor × 24 na documentação.** `listItemTaxonomy` está na doc e não existe no `list_tools` real.
4. **`listAddresses` com formato diferente do exemplo da doc.** Nosso leitor não achou a lista e a sala dizia
   "nenhum endereço salvo", sem erro. Contornamos com um leitor que aceita formatos variados (`match/busca.py`).

## O que funcionou bem

- **OAuth com PKCE S256 conforme os metadados** de `id.ifood.com.br`: seguindo os metadados (não a doc), o login da
  conta de teste funcionou.
- **Mensagem de erro do `userLocation` clara:** diz o campo, o tipo (objeto) e os subcampos numéricos; deu para
  corrigir sem adivinhar.
- **`getMerchant` ensina a buscar dentro da loja:** `catalogSummary.navigationHint` diz para usar `searchOffers` com
  `refinements.merchantId`. Foi o que resolveu o "pedido completo" (o refri vem da mesma pizzaria da pizza). Sugestão:
  pôr esse caminho também na descrição do `searchOffers`, onde o agente decide a busca.
- **Taxa de entrega e pedido mínimo já no `searchOffers`** (`merchant.deliveryMethod.fee`/`promotionalFee`,
  `minimumOrderAmount`): dá para comparar custo total (itens + taxa) entre lojas antes de criar carrinho. A doc não
  destaca isso; nós só achamos lendo a amostra.
- **`list_tools` com `input_schema` útil:** foi o que permitiu adaptar os argumentos ao servidor real e descartar o
  que a tool não declara.

Amostras sanitizadas do MCP real (`list_tools` e respostas de leitura, geradas por `app.ifood_mcp.diagnostico` no PC
da equipe): [`docs/mcp-real/`](mcp-real/) — enviadas pela equipe; se a pasta não estiver no repositório, ainda não
foram publicadas.

## Registro

Anotar **na hora** cada dor real: data/hora, o que tentamos, o que aconteceu, impacto, sugestão.

| Quando | Situação | O que aconteceu | Impacto | Sugestão |
|---|---|---|---|---|
| 17/10 manhã | `POST /marketplace` sem token | 401 diz "Your client should automatically re-register and obtain new tokens", mas o `id.ifood.com.br` não publica `registration_endpoint` (sem registro dinâmico de cliente) | Clientes MCP que seguem a mensagem tentam DCR e falham; confunde quem está começando | Ajustar a mensagem ("use o client_id/secret do MCP Portal") ou oferecer DCR |
| 17/10 manhã | Documentação (llms-full.txt, seção de endpoints e quickstart) | Cita `auth.ifood.com`, `dev-auth.ifood.com`, `api-mcp.ifood.com/v3/*`, `mcp.ifood.dev` e `npm install @ifood/mcp-sdk` — nenhum resolve / o pacote não existe no npm. O real é `id.ifood.com.br` + `consumer-mcp.ifood.com.br/marketplace` | Quem segue a doc perde tempo com URLs mortas | Atualizar os exemplos com os endpoints reais |
| 17/10 manhã | Doc recomenda "Pending Action" (QR/device code) para agentes | `/device` e o grant `device_code` não aparecem em `id.ifood.com.br/.well-known/openid-configuration` | Não dá para saber se o fluxo recomendado para agentes existe | Publicar o grant nos metadados ou marcar como "em breve" |
| 17/10 manhã | Doc da Web Login | Diz `code_challenge_method: pkce` e scopes "comma-separated"; os metadados reais pedem `S256` e o padrão OAuth separa scopes por espaço | Implementação literal da doc falha | Corrigir para `S256` e espaço |
| 17/10 manhã | Cadastro do agente | O vídeo dizia "uma Redirect URL por agente", mas o formulário já aceita várias (ok). Escopos continuam **imutáveis** depois de ativo | Errar o escopo obriga a recriar o agente e a passar de novo pela homologação | Permitir editar escopos com nova revisão; atualizar o vídeo |
| 17/10 noite | Doc de contas de teste | O link "criação de conta" aponta para `mcp-developer.ifood-sandbox.com.br/pt-BR/sign-up`, domínio que não respondeu no nosso teste; o portal real é `mcp-developer.ifood.com.br` (botão "Faça login") | Equipe aprovada não achava onde entrar no portal | Corrigir o link e pôr um botão "Meus agentes" visível na doc |
| 17/10 ~22h | `list_tools` no MCP real (conta de teste) | O servidor expõe **23 tools**; a doc lista 24 — `listItemTaxonomy` não existe | Quem planeja pela doc conta com uma tool que não há | Atualizar a lista da doc ou publicar a tool |
| 17/10 ~22h | `searchOffers` e `getRecommendations` com `latitude`/`longitude` soltos (como os exemplos da doc) | Erro: "`userLocation` is required and must be a JSON object with numeric `latitude` and `longitude`" — 0 resultados | Nenhuma busca funcionou no 1º teste; o agente não encontra lojas | Citar `userLocation` (objeto) na doc e nos exemplos; a mensagem de erro é boa e deveria ser o padrão das outras tools |
| 17/10 ~22h | `listAddresses` no MCP real | Formato diferente do exemplo da doc (nosso leitor não achou a lista e a sala dizia "nenhum endereço salvo") | Integração quebra em silêncio | Publicar o `outputSchema` das tools (o `list_tools` já tem o campo) e manter a doc igual ao real |

| 18/10 00h48 | `createCart` com `merchantId` + `addressId` (o schema não marca nada como obrigatório) | Volta `MISSING_REQUIRED_FIELDS`: "addressId, merchantId, and items are required when orderId is absent". O `input_schema` tem `required: []` | Sequência natural "criar carrinho → adicionar itens" (a da doc) falha; o schema não avisa | Marcar no schema (ou num `oneOf` com/sem `orderId`) os campos realmente exigidos, ou aceitar carrinho vazio |
| 18/10 00h48 | Erro de negócio do `createCart` | Vem como **resposta normal** (`{"error": {"code", "message", "userFriendlyMessage"}}`, sem `isError`) | Cliente MCP genérico (e o nosso diagnóstico) trata como sucesso e segue sem `cartId` | Devolver `isError: true` em todo erro de tool (como o `getRecommendations` já faz) |
| 18/10 00h58 | Erro do `createAddress` | Outro formato: `{"success": false, "errors": {"mcpCode", "code"}}` (ex.: `ADDRESS_CREATION_FAILED` / `ADR-2001`, "unexpected status: 400 Bad Request", `retryable: true`); o `getRecommendations` usa um 3º (`isError` + texto JSON `{"error": "..."}`) | 3 formatos de erro em 23 tools: cada cliente precisa de 3 leitores | Um envelope de erro único (`isError` + `{code, message, userFriendlyMessage, retryable}`) |
| 18/10 01h22 | `createAddress` em 3 contas de teste | `ADR-2001` também em `safe-` e `fair-thales`, repetindo o exemplo exato da doc e com `listAddresses` antes na mesma sessão; `retryable: true` que nunca passa | Bloqueia carrinho e pedido no MCP real (P1/P3/P4 parados) | Documentar o `ADR-2001` (causa e correção); `retryable` só quando repetir resolve; contas de teste com endereço salvo |
| 18/10 00h58 | `createAddress` na conta de teste (`unique-thales`) | Geocodifica (`SINGLE`), mas salvar falha sempre com `ADR-2001`, com 2 endereços diferentes, em 1 e 2 passos | Conta de teste sem endereço = nenhum carrinho possível (o `createCart` exige `addressId`) | Contas de teste já com 1 endereço salvo, ou detalhar o ADR-2001 |
| 18/10 00h48 | `listPaymentMethods` | O schema pede só `merchantId` (obrigatório), não `cartId` — a doc o põe depois do `setCartDelivery`, no fluxo do carrinho | Quem passa o `cartId` (natural no fluxo) leva erro; não fica claro se a lista depende do carrinho/endereço | Aceitar `cartId` também ou explicar na descrição que a lista é por loja |
| 18/10 00h48 | `getRecommendations` | `contentMode` é obrigatório (enum `RECOMMENDED`, `RECENT_ORDERS`, …), mas sem `default`; sem ele: "the value provided for `contentMode` (\"\") is not valid" | Erro em toda chamada "simples" | Default `RECOMMENDED` |
| 18/10 madrugada | `searchOffers`/`browseOffers`/`getMerchant` | Nomes diferentes entre tools para o mesmo dado: item `itemName` (busca) × `name` (doc); preço `unitPrice`/`promotionalUnitPrice`; loja aninhada em `merchant{}` no ITEM e na raiz no MERCHANT; o `getMerchant` não traz cardápio, só `featuredItems` (5) e manda usar `browseOffers` com `refinements.merchantId` | Parser escrito pela doc lê vazio (0 candidatos) | Publicar `outputSchema` e manter um formato só de item/loja |
| 18/10 madrugada | `browseOffers` | `merchantType` obrigatório e a descrição diz "se o usuário não disse a vertical, pergunte" | Agente de pedido em grupo não tem a quem perguntar no meio da busca; usamos `RESTAURANT` | Permitir omitir (todas as verticais), como no `searchOffers` |
| 18/10 madrugada | `getItem` (amostra "Pizzas Doces Grandes") | Item com `optionGroups` de `minSelections: 1` (sabor obrigatório) e `additionalPrice` igual ao `unitPrice` — não dá para saber se o preço final é 75,99 ou 151,98, nem se o `createCart` sem `options` falha | Preço mostrado na busca pode não ser o do carrinho | Dizer na busca se o item tem opção obrigatória (`hasRequiredOptions`) e documentar como `additionalPrice` soma |
| 18/10 01h57–02h01 | `searchOffers` → `createCart` (Pastelaria Brasil Bebidas, Tropical Lanches, Max Burguer) | Lojas que a busca mostra e que o `getMerchant` dá como abertas (`isOpen: true`) falham no `createCart` com `MERCH-007` "Could not retrieve merchant" | Só dá para saber no carrinho: o grupo vê a loja na combinação e ela some no fim. Contornamos pulando a loja e avisando (`lojas_fora`, `match/checkout.py`) | Não devolver na busca loja que o carrinho não aceita, ou expor um campo "aceita pedido pelo MCP" |
| 18/10 01h54–02h01 | `listAddresses`, `setCartDelivery`, `getItem`, `createCart`, `getCart` | `INTERNAL` ("upstream service") intermitente: o mesmo carrinho (BK) passou inteiro e minutos depois falhou em passos diferentes; `listAddresses` ficou ~4 min fora | Pedido em várias lojas raramente fecha inteiro nesses minutos. Contornamos com 1 nova tentativa e endereço de teste quando `listAddresses` falha | Página de status / `retryAfter` no erro; separar falha do iFood de falha do pedido |
