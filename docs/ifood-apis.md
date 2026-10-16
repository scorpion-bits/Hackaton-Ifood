# APIs do iFood — o que sabemos (Fase 0, 16/10/2026)

> **Como esta pesquisa foi feita:** o portal oficial `developer.ifood.com.br` devolveu **HTTP 403** para leitura
> automática (curl e WebFetch). Tudo abaixo vem de **trechos indexados das páginas oficiais** (via busca), com o link
> da página. Isso é mais fraco que ler a página inteira.
> - **VERIFICADO (trecho oficial)** = o trecho da página oficial diz isso.
> - **NÃO VERIFICADO** = memória/terceiros/inferência. Conferir no portal antes de usar na demo.
> - 👥 Na abertura (17/10), alguém abre o portal no navegador e confirma os itens marcados.

## 1. Acesso e conta

| Afirmação | Status | Fonte |
|---|---|---|
| Ao criar conta no portal, você ganha **uma loja e um aplicativo de teste**; as credenciais são geradas ao registrar o app | VERIFICADO (trecho) | [Criar conta](https://developer.ifood.com.br/pt-BR/docs/getting-started/first-steps/create-account/), [Criar app](https://developer.ifood.com.br/en-US/docs/getting-started/first-steps/create-app/) |
| O e-mail do cadastro não pode estar ligado a uma conta existente do Portal do Parceiro | VERIFICADO (trecho) | [Criar conta](https://developer.ifood.com.br/pt-BR/docs/getting-started/first-steps/create-account/) |
| Homologação exige conta profissional (CNPJ); CPF/estudante não é aceito | VERIFICADO (trecho) | [Financial — homologação](https://developer.ifood.com.br/en-US/docs/guides/modules/financial/homologation) |
| Lojas **reais** só depois da homologação, e a permissão precisa ser aceita no Portal do Parceiro | VERIFICADO (trecho) | [Solicitar acesso](https://developer.ifood.com.br/pt-BR/docs/getting-started/first-steps/request-access) |
| `clientId`/`clientSecret` ficam em "Meus Apps" | VERIFICADO (trecho) | [Autenticação](https://developer.ifood.com.br/en-US/docs/guides/authentication/) |

**Consequência para o hackathon:** sem CNPJ e homologação, o realista é usar **app + loja de teste** (se o iFood
liberar no evento) ou o **modo demonstração** deste repositório. Não existe "sandbox" com outro host documentado
nos trechos encontrados. NÃO VERIFICADO se o iFood vai fornecer credenciais no evento.

## 2. Autenticação

| Afirmação | Status | Fonte |
|---|---|---|
| `POST https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token` | VERIFICADO (trecho) | [Autenticação centralizada](https://developer.ifood.com.br/en-US/docs/guides/modules/authentication/centralized/) |
| Campos `grantType=client_credentials`, `clientId`, `clientSecret`, em **form-urlencoded** (JSON dá 415) | VERIFICADO (trecho) | [Autenticação centralizada](https://developer.ifood.com.br/en-US/docs/guides/modules/authentication/centralized/), [Intro](https://developer.ifood.com.br/pt-BR/docs/guides/modules/authentication/intro/) |
| Token vale 6 h (21600 s); app centralizado **não** recebe refresh token | VERIFICADO (trecho) | idem |
| Uso: `Authorization: Bearer <token>`; só HTTPS/TLS 1.2+ | VERIFICADO (trecho) | [Autenticação](https://developer.ifood.com.br/en-US/docs/guides/authentication/) |
| Nome dos campos da resposta (`accessToken`, `expiresIn`) | NÃO VERIFICADO | o código aceita as duas grafias |

## 3. Módulos e endpoints

| Módulo | O que faz | Endpoints citados | Status |
|---|---|---|---|
| **Merchant** | lojas do token, status, interrupções, horário | `GET /merchants/{merchantId}/status` (20000 req/min); interrupção máx. 7 dias; `PUT` de horário substitui tudo | VERIFICADO (trecho): [Merchant endpoints](https://developer.ifood.com.br/pt-BR/docs/guides/modules/merchant/endpoints), [Boas práticas](https://developer.ifood.com.br/en-US/docs/food/guides/modules/merchant/best-practices-troubleshooting). Prefixo `/merchant/v1.0` e listagem `GET /merchant/v1.0/merchants`: **NÃO VERIFICADO** |
| **Catalog v2** | cardápio: catálogos, categorias, itens, preço, status | `GET /merchants/{merchantId}/catalogs/{catalogId}/categories` (itens dentro de cada categoria; `status` AVAILABLE/UNAVAILABLE; `price.value`, `price.originalValue`); `POST /merchants/{id}/categories`; `PUT /merchants/{id}/items`; `PATCH .../items/price` e `.../items/status` (a página de rate limit escreve `item` no singular — **divergência**) | VERIFICADO (trecho): [Catalog v2](https://developer.ifood.com.br/en-US/docs/guides/catalog/v2/), [Fundamentos](https://developer.ifood.com.br/en-US/docs/food/guides/modules/catalog/fundamentals). Prefixo `/catalog/v2.0`: **NÃO VERIFICADO** |
| **Order** | ciclo do pedido do lado da loja | `GET /orders/{id}`; `POST /orders/{id}/confirm` (até 8 min); `readyToPickup` antes de `dispatch`; `POST /orders/{id}/dispatch` com `deliveredBy: "MERCHANT"` (202) | VERIFICADO (trecho): [Workflow](https://developer.ifood.com.br/en-US/docs/guides/modules/order/workflow/), [Endpoints](https://developer.ifood.com.br/en-US/docs/food/guides/modules/order/endpoints), [Changelog](https://developer.ifood.com.br/en-US/docs/changelog/) |
| **Events** | eventos de pedido por polling ou webhook | polling a cada 30 s; ack só do que foi processado; eventos fora de ordem (ordenar por `createdAt`); retenção até 8 h após a entrega; 6000 req/min. Caminho: a doc fala em `orders:polling`/`orders:acknowledgment`; um terceiro usa `events:polling` — **divergência** | VERIFICADO (trecho): [Polling](https://developer.ifood.com.br/pt-BR/docs/guides/modules/events/polling-overview/), [Webhook](https://developer.ifood.com.br/en-US/docs/guides/modules/events/webhook-overview) |
| **Promotion** | promoções | `POST /merchants/{merchantId}/promotions` (1000 req/min); desconto máx. **70%**; **restrito a parceiros de mercado (grocery)** | VERIFICADO (trecho): [Promotion](https://developer.ifood.com.br/en-US/docs/guides/promotion/) |
| **Review** | avaliações: listar, detalhar, responder, resumo | limites divergentes (2000 req/min × 10 req/s) | VERIFICADO (trecho): [Review](https://developer.ifood.com.br/pt-BR/docs/guides/review/) |
| **Financial** | vendas, pagamentos, taxas, recebíveis | 1000 req/min cada; homologação só CNPJ | VERIFICADO (trecho): [Financial](https://developer.ifood.com.br/en-US/docs/guides/modules/financial/homologation) |
| **Logistics / Shipping** | entregador próprio: assignDriver → goingToOrigin → arrivedAtOrigin → dispatch → arrivedAtDestination → verifyDeliveryCode (fora de ordem = 409) | base URL aparece de formas diferentes na doc | VERIFICADO (trecho): [Logistics](https://developer.ifood.com.br/en-US/docs/food/guides/modules/logistics/introduction) |
| **Item** | envio de itens | máx. 25% do catálogo a cada 30 min | VERIFICADO (trecho): [Item](https://developer.ifood.com.br/en-US/docs/guides/modules/item/general) |

## 4. Limites gerais

- Limite por endpoint **e por aplicativo**; estourou → **HTTP 429**. VERIFICADO (trecho):
  [Rate limit](https://developer.ifood.com.br/en-US/docs/getting-started/documentation/rate-limit/)
- Uso indevido tem página própria: [Improper use](https://developer.ifood.com.br/en-US/docs/getting-started/documentation/improper-use/)

## 5. O que NÃO existe (até onde achamos)

- **API pública para o CONSUMIDOR** buscar restaurantes ou fazer pedidos: não encontrada. Todas as APIs acima são do
  lado **loja/parceiro**. Os servidores MCP de "pedido como consumidor" encontrados são **não oficiais** (terceiros,
  scraping): [Glama](https://glama.ai/mcp/servers/davidmosiah/ifood-mcp), [mcpmarket](https://mcpmarket.com/server/ifood-1).
  **Não usar** sem aval do iFood.
- **MCP oficial do iFood**: não encontrado.
- **Contexto:** o iFood tem uma "Agent Platform" (bug bounty privado ligado à SEMCOMP, 16–23/10) e já falou
  publicamente em um "exército de agentes de IA" no atendimento
  ([Gizmodo](https://www.gizmodo.com.br/ifood-aposta-em-exercito-de-agentes-de-ia-para-transformar-o-atendimento-na-plataforma-18794)).
  Pode ser o que vão oferecer no evento. NÃO VERIFICADO.

## 6. Como isso está no código

- `backend/app/ifood/real.py`: dicionário `ENDPOINTS` com o status de cada caminho. Implementa token, lojas e
  cardápio (leitura). Escrita (status de item, promoção, pedido) levanta `NaoSuportado` com o motivo.
- `python -m app.ifood.testar_real` (em `backend/`): testa as credenciais reais sem alterar nada.
- `backend/app/ifood/mock.py`: loja de demonstração local, mesma interface, sempre com `fonte: "demonstração"`.

## 7. Evento

- Hackathon "Vendendo com Agentes", iFood + SEMCOMP 29, 17–18/10/2026, ONOVOLAB, equipes de até 4:
  [USP São Carlos](https://saocarlos.usp.br/semcomp-2026-tera-palestras-sobre-inteligencia-artificial-minicursos-feira-de-oportunidades-e-desafios-de-programacao/).
- O ICMC fala em **27 horas** ininterruptas; nosso cálculo pelo horário (12h30 → 18h00) dá 29h30:
  [ICMC](https://icmc.usp.br/noticias/7684-semcomp-2026-abre-inscricoes-para-semana-de-palestras-minicursos-hackathon-e-oportunidades-no-icmc).
  👥 Confirmar o horário de entrega na abertura.
