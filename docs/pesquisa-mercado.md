# Pesquisa de mercado: anúncios, comércio entre agentes e números do iFood (T5, etapa 04)

Pesquisador, 17/10/2026. **Acesso de todas as fontes: 17/10/2026** (salvo indicação).
Complementa (não repete) `docs/planos/etapa-01b-match-estrategia.md` §10–11 e `docs/design-ifood.md` §3–4.

**Confiança:**
- **primária** = li a página da própria empresa/órgão (release, blog oficial, documento à SEC, PDF de resultados).
- **secundária** = li a matéria de um veículo conhecido.
- **resumo de busca** = só vi o resumo do buscador; a página não abriu (403/503) ou não li o trecho. Não usar como número de destaque.

---

## 1. Anúncios patrocinados em marketplaces de delivery (base do lance "Patrocinado")

| Afirmação | Número | Fonte | Data da fonte | Confiança |
|---|---|---|---|---|
| iFood Ads para restaurantes funciona por **leilão**: a loja define um **lance por visita** ao cardápio; só paga quando há visita | orçamento diário R$ 25 a R$ 400 (opções R$ 50/100/150) | [Blog iFood Parceiros: iFood Ads, como funciona](https://blog-parceiros.ifood.com.br/como-usar-ifood-ads-para-crescer-na-plataforma/) | 18/09/2026 | primária |
| No iFood Ads, a posição depende do lance **e** de avaliação e indicadores operacionais (tempo de entrega, cancelamento). Frase literal: "Dinheiro sozinho não compra posição." | — | mesma página acima | 18/09/2026 | primária |
| Resultado médio declarado pelo iFood para quem anuncia (o próprio texto diz que não é garantia) | até +40% visitas ao cardápio; até +20% vendas | mesma página acima | 18/09/2026 | primária (autodeclarado) |
| Anúncio aparece em resultados de busca e áreas de descoberta; acesso pelo Portal do Parceiro > Central de Crescimento | — | mesma página; [Central de Crescimento](https://blog-parceiros.ifood.com.br/central-de-crescimento/) | 18/09/2026; data da 2ª NÃO VERIFICADO | primária / resumo de busca |
| iFood comprou a Advolve e quer **multiplicar por 5** a frente de Ads até 2030; Ads existe desde 2021; restaurantes são a frente "mais madura" | meta 5x até 2030 | [Startups](https://startups.com.br/negocios/ifood-compra-a-advolve-e-mira-crescimento-de-5x-em-ads-ate-2030/) · [Meio & Mensagem](https://www.meioemensagem.com.br/marketing/ifood-adquire-advolve-mirando-crescimento-em-ads-ate-2030) | 12/11/2025 | secundária |
| iFood Ads tem mais de 230 anunciantes "em verticais de restaurantes" (marcas) | 230+ | [Meio & Mensagem](https://www.meioemensagem.com.br/marketing/ifood-adquire-advolve-mirando-crescimento-em-ads-ate-2030) | 12/11/2025 | secundária |
| Receita do iFood Ads em R$ | **não divulgada** (nenhuma fonte achada) | — | — | — |
| Uber Eats "Sponsored listings": lojas dão **lances** para subir no app; o anúncio é igual a uma loja comum com a etiqueta **"sponsored"** abaixo do nome | — | [Uber Help: What are sponsored listings?](https://help.uber.com/en/ubereats/restaurants/article/what-are-sponsored-listings?nodeId=e4222375-edec-4323-99f8-172ed6c4e532) | sem data na página | primária |
| Termos da Uber: lance entra em leilão; cobrança por clique | — | [Uber Eats Merchant Advertising Terms (SE)](https://www.uber.com/se/en/legal/uber-eats-merchant-advertising-terms/) | sem data | resumo de busca |
| Anúncios da Uber: **US$ 1,5 bi** de receita anualizada, +60% a/a (1º tri 2025) | US$ 1,5 bi | [Digiday](https://digiday.com/media/qa-uber-ads-hits-1-5-billion-run-rate-as-it-hires-first-head-of-measurement/) | 08/05/2025 | secundária (o release da SEC não traz o número; veio da fala de resultados) |
| Anúncios da Uber passaram de **US$ 2 bi** anualizados, +50% a/a (4º tri 2025) | US$ 2 bi | [TI Inside](https://tiinside.com.br/en/06/02/2026/uber-advertising-ultrapassa-us-2-bi-em-receita-anualizada/) | 06/02/2026 | resumo de busca (página deu 403) |
| DoorDash: negócio de anúncios passou de **US$ 1 bi** anualizado (2º tri 2025) | US$ 1 bi | fala de resultados de 06/08/2025, via [MarketBeat (transcrição)](https://www.marketbeat.com/earnings/reports/2025-8-6-doordash-inc-stock); o [release oficial na SEC](https://www.sec.gov/Archives/edgar/data/1792789/000179278925000011/q22025dashex991-pressrelea.htm) só diz "increasing contribution from advertising revenue" | 06/08/2025 | secundária (número) / primária (frase qualitativa) |
| Instacart: receita de "advertising and other" ≈ US$ 1,065 bi em 2025 | ≈ US$ 1,07 bi | [Sacra](https://sacra.com/research/instacart) (cita o 10-K) | 2026 | resumo de busca |

**Leitura:** anúncio pago por loja dentro do app de delivery é modelo **comprovado** (Uber, DoorDash, Instacart passam de US$ 1 bi/ano cada) e o iFood **já tem** (iFood Ads, por leilão de lance por visita). O "Patrocinado" do Match é a mesma lógica levada para o momento em que um **agente** compra. Diferença nossa (D10): no Match o pagamento compra só a **ordem de exibição do lance**, nunca a escolha do otimizador.

---

## 2. Comércio entre agentes ("agentic commerce")

| Afirmação | Data | Fonte | Confiança |
|---|---|---|---|
| Anthropic abre o **Model Context Protocol (MCP)**, padrão para ligar assistentes de IA a dados e serviços | 25/11/2024 | [Anthropic](https://www.anthropic.com/news/model-context-protocol) | primária |
| Visa lança **Visa Intelligent Commerce** ("enables AI to find and buy") | 30/04/2025 | [Visa (release)](https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.21361.html) | primária |
| Mastercard **Agent Pay**: amplia com serviços de confiança (pontuação de probabilidade de a transação ter sido iniciada por agente) | 09/2026 | [Mastercard (release)](https://www.mastercard.com/us/en/news-and-trends/press/2026/september/new-trust-and-intelligence-services.html) | resumo de busca (data do lançamento original do Agent Pay: NÃO VERIFICADO) |
| Google anuncia o **Agent Payments Protocol (AP2)**, protocolo aberto para pagamentos iniciados por agentes; funciona como extensão do A2A **e do MCP**; 60+ organizações | 16/09/2025 | [Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol) | primária |
| AP2 doado à FIDO Alliance | NÃO VERIFICADO (data) | [Google blog](https://blog.google/products-and-platforms/platforms/google-pay/agent-payments-protocol-fido-alliance/) | resumo de busca |
| Stripe + OpenAI: **Agentic Commerce Protocol (ACP)** e Instant Checkout no ChatGPT; OpenAI diz que itens com Instant Checkout não ganham preferência no ranking | 29/09/2025 | [OpenAI](https://openai.com/index/buy-it-in-chatgpt/) · [Stripe](https://stripe.com/newsroom/news/stripe-openai-instant-checkout) | resumo de busca (datas batem nas duas) |
| OpenAI reduz o Instant Checkout e deixa lojistas usarem o próprio checkout | 03/2026 | [OpenAI release notes](https://help.openai.com/en/articles/6825453-chatgpt-release-notes) | resumo de busca |
| McKinsey: agentes podem intermediar **US$ 3 a 5 tri** do comércio global até 2030 (só bens; ~US$ 1 tri nos EUA) | 10/2025 | [McKinsey](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-agentic-commerce-opportunity-how-ai-agents-are-ushering-in-a-new-era-for-consumers-and-merchants) | resumo de busca (página deu 503) |
| **Swiggy** (Índia, delivery) lança MCP: pedir comida, mercado (Instamart) e reservas (Dineout) dentro de ChatGPT, Claude e Gemini | 27/01/2026 | [Swiggy (release)](https://www.swiggy.com/corporate/press-release/swiggy-now-lets-you-order-food-dineout-and-shop-on-instamart-directly-inside-chatgpt-and-claude/) | primária |
| Swiggy: pagamento **UPI dentro do chat** via MCP; "Until now, MCP orders settled on Cash." | 10/07/2026 | [Swiggy Builders blog](https://mcp.swiggy.com/builders/blog/2026-07-10-mcp-payments-upi/) | primária |
| Swiggy Builders Club: acesso de desenvolvedores e empresas ao MCP (nº de tools varia entre páginas: 18+ a 66) | 2026 | [Swiggy (release)](https://www.swiggy.com/corporate/press-release/swiggy-to-launch-builders-club-giving-developers-and-enterprises-access-to-its-ai-commerce-stack/) · [docs](https://mcp.swiggy.com/builders/docs/) | resumo de busca |
| **iFood: pagamento agêntico no Ailo** (WhatsApp e app): o agente usa o cartão já salvo e o cliente confirma com um botão no chat; feito pela Zoop (empresa do grupo), protocolo próprio sobre código aberto; liberação gradual até 100% da base do Ailo em 1 mês | 28/08/2026 | [Mobile Time](https://www.mobiletime.com.br/noticias/28/08/2026/ifood-pagamento-agentico/) | secundária |
| iFood **One-Click Buy** no Ailo (WhatsApp): monta carrinho, aplica cupom, paga com Pix sem abrir o app; "fechar um pedido, se já sabe o que quer, em 30 segundos" (diretora Isabella Piratininga) | 16/07/2026 | [Canaltech](https://canaltech.com.br/apps/nova-ia-do-i-food-deixa-voce-fazer-pedidos-no-whats-app-com-apenas-um-clique) | secundária |
| Prosus: plataforma agêntica **ToqanClaw** "already available to our 5M+ restaurant partners" (grupo inteiro, não só iFood) | 29/06/2026 | [Prosus FY2026 media release (PDF)](https://www.prosus.com/~/media/Files/P/prosus-corp-v2/results-reports-and-events-archive/annual-report/2026/fy2026-media-release.pdf) | primária |
| iFood: meta de 1 agente de IA interno por funcionário (8 mil) até 03/2026; ~3,5 mil já existiam; agente de atendimento Rosie com 70% dos chamados automatizados | 09/10/2025 | [Mobile Time](https://www.mobiletime.com.br/noticias/09/10/2025/ifood-8-mil-agentes-ia/) | secundária |
| MCP do iFood para consumidor (o do hackathon) | — | doc oficial em `docs/mcp-ifood.md` ([llms-full.txt](https://mcp-developer.ifood.com.br/llms-full.txt)); **anúncio público em imprensa: não encontrado** | — |

**Leitura:** o padrão "agente compra em nome do usuário, com confirmação explícita" já está em produção nos grandes (Visa, Google AP2, OpenAI/Stripe) e em delivery (Swiggy via MCP; iFood via Ailo). **Agente do lado do restaurante negociando com agente do comprador** (o nosso leilão): **nenhuma iniciativa pública encontrada** em delivery. Isso é o espaço original do Match; não afirmar que "ninguém faz", e sim "não encontramos ninguém fazendo".

---

## 3. Números do iFood para o pitch

| Afirmação | Número | Fonte | Data da fonte | Confiança |
|---|---|---|---|---|
| Pedidos por mês | **mais de 180 milhões** | [Portal de Dados iFood](https://institucional.ifood.com.br/portal-de-dados-ifood/) | 2026 (página sem data por indicador) | primária |
| Clientes ativos ("pessoas conectadas") | **65 milhões** | mesma | 2026 | primária |
| Estabelecimentos parceiros | **mais de 500 mil** | mesma | 2026 | primária |
| Cidades atendidas | 2.000+ | mesma | sem data | primária |
| Entregadores | 600 mil+ cadastrados; 460 mil ativos em 2025 | mesma | 2026 | primária |
| Movimentou na economia | R$ 166,9 bi em 2025 = 0,70% do PIB (estudo FIPE) | mesma | 2025 | primária |
| Recorde de fim de semana | 22,2 milhões de pedidos (6–8/03/2026); ~5,1 mil transações/minuto; 200 mil+ entregadores ativos no sábado | [iFood: recorde](https://institucional.ifood.com.br/noticias/ifood-bateu-recorde-de-vendas/) | 27/03/2026 | primária |
| Pedidos **com apoio do LCM** em fev/2026 (não é o total do iFood!) | 12 milhões | [iFood: 12 milhões de pedidos](https://institucional.ifood.com.br/releases/ifood-12-milhoes-pedidos/) | 20/03/2026 | primária |
| LCM: 90% das interações de IA generativa; custo 60x menor que referências; 3 bi de interações de IA em jan–fev/2026; push com LCM +50% pedidos | — | mesma | 20/03/2026 | primária |
| Ailo: 48% mais chance de a busca virar pedido e 33% mais rápido que o fluxo do app; teste com ~70 mil pessoas desde 06/2025. **Não cita pedido em grupo** | — | [iFood: Ailo](https://institucional.ifood.com.br/inovacao/ailo-assistente-de-ia-pedidos/) | 10/10/2025 | primária |
| iFood (Prosus FY26, ano até 31/03/2026): receita +40% (28% em moeda local); pedidos de delivery de comida +8%; GMV +17% (12%); Clube = 45% do volume; iFood Pago US$ 463 mi (~25% da receita) | — | [Prosus FY2026 media release](https://www.prosus.com/~/media/Files/P/prosus-corp-v2/results-reports-and-events-archive/annual-report/2026/fy2026-media-release.pdf) | 29/06/2026 | primária |
| Ticket médio do iFood | **não divulgado** pelo iFood (não encontrado) | — | — | — |
| Custo médio de um pedido de delivery no Brasil (não é do iFood) | R$ 66,21 (12,5% acima de comer no restaurante) | levantamento da Ticket, via [Olhar Digital](https://olhardigital.com.br/2024/07/23/pro/pedir-comida-em-delivery-e-mais-caro-do-que-ir-a-um-restaurante-revela-pesquisa/) | 23/07/2024 | secundária (sem amostra/metodologia) |

**Conferência das fontes da 01b §10:** LCM (10/10/2025), Ailo (10/10/2025), "LCM = 90%" (20/03/2026) e Prosus FY2026 (29/06/2026, "powered by the LCM", 21% da receita B2C da Despegar no Brasil vem de clientes iFood) **confirmados**. O "Ailo agêntico / One-Click Buy (16/07/2026)" que estava NV na 01b agora tem fonte: [Canaltech](https://canaltech.com.br/apps/nova-ia-do-i-food-deixa-voce-fazer-pedidos-no-whats-app-com-apenas-um-clique) (secundária).

---

## 4. Pedido em grupo / comer em grupo

| Afirmação | Número | Fonte | Data | Confiança |
|---|---|---|---|---|
| Dado brasileiro sobre % de pedidos de delivery feitos em grupo, frequência, ticket de pedido em grupo ou desistência | **não encontrado** | — | — | — |
| Tempo que brasileiros levam para decidir o pedido | **não encontrado** | — | — | — |
| Reino Unido: quase metade dos entrevistados diz que escolher onde comer **em grupo** leva em média **25 minutos** (OnePoll para Meerkat Meals; amostra não informada) | 25 min | [Public Sector Catering](https://publicsectorcatering.co.uk/news/guess-how-long-brits-spend-deciding-where-eat-out) | 01/10/2018 | secundária (antiga, encomendada, sobre restaurante e não delivery) |
| Emirados: 43% dizem gastar perto de 20 minutos decidindo o que pedir online (YouGov para Deliveroo; amostra não informada) | ~20 min | [Deliveroo UAE](https://deliveroo.ae/more/news-articles/indecisive-on-what-to-order-try-deliveroo-s-spin-the-meal) | 12/09/2022 | primária (da Deliveroo, encomendada) |
| Na estreia do Brasil na Copa 2026, pedidos de bebida por delivery subiram 60%+ (dados iFood e 99Food via PEGN) | +60% | [Portal Tela](https://www.portaltela.com/noticias/2026/06/16/pedidos-de-bebidas-em-delivery-sobem-mais-de-60-na-estreia-do-brasil-na-copa/) | 16/06/2026 | resumo de busca (agregador; original da PEGN não lido) |
| iFood testa "Combinar pagamentos" (2 formas no mesmo pedido); pedido em grupo no iFood não foi anunciado | — | [Tecnoblog](https://tecnoblog.net/noticias/ifood-testa-opcao-de-dividir-pagamento-com-outra-pessoa/) (já na 01b) | ~06/2026 | secundária |

**Conclusão:** não existe número público brasileiro sobre pedido em grupo. Por isso a **pesquisa da equipe** (`docs/pesquisa-usuarios.md`) é a única fonte do problema no Brasil. Os dados de fora (25 min no Reino Unido, 20 min nos Emirados) só como apoio, citando país, ano e quem encomendou.

---

## Como usar no pitch (frases prontas, cada uma com fonte)

1. "O iFood já processa **mais de 180 milhões de pedidos por mês**, de **65 milhões de clientes**, em **mais de 500 mil lojas**." ([Portal de Dados iFood](https://institucional.ifood.com.br/portal-de-dados-ifood/))
2. "Anúncio de loja no app de delivery já é um negócio de bilhões: a Uber passou de **US$ 1,5 bilhão por ano** em anúncios no início de 2025, e o iFood quer **multiplicar por 5** o iFood Ads até 2030." ([Digiday, 08/05/2025](https://digiday.com/media/qa-uber-ads-hits-1-5-billion-run-rate-as-it-hires-first-head-of-measurement/); [Startups, 12/11/2025](https://startups.com.br/negocios/ifood-compra-a-advolve-e-mira-crescimento-de-5x-em-ads-ate-2030/))
3. "O próprio iFood diz que no iFood Ads 'dinheiro sozinho não compra posição'. O Match leva isso ao extremo: o lance **Patrocinado** aparece primeiro, mas **nunca** muda a escolha da IA." ([Blog iFood Parceiros, 18/09/2026](https://blog-parceiros.ifood.com.br/como-usar-ifood-ads-para-crescer-na-plataforma/))
4. "Agentes que compram já são realidade: Google (AP2, que roda sobre MCP), Visa e OpenAI/Stripe lançaram protocolos em 2025, e a Swiggy, na Índia, já recebe pedidos de comida pelo MCP desde janeiro." ([Google, 16/09/2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol); [Swiggy, 27/01/2026](https://www.swiggy.com/corporate/press-release/swiggy-now-lets-you-order-food-dineout-and-shop-on-instamart-directly-inside-chatgpt-and-claude/))
5. "O Ailo já fecha **um** pedido em 30 segundos. O Match faz o que falta: o pedido da **turma**, com um agente por restaurante disputando e um agente comprador do grupo." ([Canaltech, 16/07/2026](https://canaltech.com.br/apps/nova-ia-do-i-food-deixa-voce-fazer-pedidos-no-whats-app-com-apenas-um-clique)) + "Na nossa pesquisa no evento, n = X, …" (`docs/pesquisa-usuarios.md`).

## O que NÃO dizer (sem fonte ou fonte errada)

- "O iFood faz 12 milhões de pedidos por mês." **Errado**: 12 milhões são os pedidos **com apoio do LCM** em fev/2026; o total é 180 milhões+.
- Qualquer **receita do iFood Ads** em reais, ou "% da receita do iFood que vem de anúncio": não divulgado.
- "O iFood Ads custa R$ X por clique": a página oficial fala em lance por **visita** e diz que o formato deve ser confirmado no Portal; não há tabela de preço por clique.
- **Ticket médio do iFood**: não divulgado. Os R$ 66,21 são de um levantamento da Ticket sobre delivery em geral, sem metodologia publicada.
- "X% dos brasileiros pedem delivery em grupo", "grupos levam N minutos para decidir no Brasil", "N% desistem": **não existe dado público**. Usar só a pesquisa da equipe (com n) ou os dados de fora, com país e ano.
- "Ninguém no mundo faz leilão entre agentes de restaurante": dizer "não encontramos iniciativa pública".
- "O iFood vai lançar pedido em grupo" ou "o Ailo faz pedido em grupo": nenhuma fonte.
- "A Uber faz US$ 2 bi em anúncios": só vimos resumo de busca (403). Preferir o US$ 1,5 bi (Digiday) ou dizer "mais de US$ 1,5 bi".
- "Agentic commerce vai movimentar US$ 5 trilhões": a página da McKinsey não abriu; se usar, dizer "estimativa da McKinsey, de 3 a 5 trilhões no mundo até 2030" e avisar que é projeção.
- "O MCP do iFood foi lançado em [data]": não achamos anúncio público com data.
