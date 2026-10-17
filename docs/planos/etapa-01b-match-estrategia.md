# Etapa 01b — Match: análise estratégica (prompt mestre da equipe, 17/10 18h40)

Status: **análise feita · aguardando decisão da equipe**. Nada de código antes da aprovação.
Fontes do MCP: `llms-full.txt` da doc oficial (https://mcp-developer.ifood.com.br/llms-full.txt), lida em 17/10.
Tudo marcado **NV** = NÃO VERIFICADO (está na doc, mas não testamos com credencial) ou não existe na doc.

## 1. Resumo executivo
- **Tese:** o Match é uma camada que transforma **necessidade em linguagem natural (de 1 ou N pessoas) em uma cesta
  viável** — itens reais, preço real, loja(s) real(is), custo total e motivo — e executa o pedido pelo MCP com
  consentimento. Não é "achar o restaurante ideal", nem chatbot.
- **Por que IA:** traduzir desejo vago/conflitante em restrições e pontuar aderência de itens de cardápio a desejos
  ("algo mais leve", "parecido com o do mês passado, mais barato") não cabe em filtro. Conta, orçamento, taxa e
  ordem do checkout ficam em código.
- **Escopo vencedor para 18h de hackathon:** um núcleo só ("intenção → cesta viável") com o **Match em grupo** como
  demo principal (o individual é o grupo de 1), checkout consolidado com **1 pagador** e transparência total sobre
  "N pedidos, N taxas, N entregas". Descoberta contextual (cold start) e expansão internacional entram no **pitch**
  como visão, com fatos pesquisados; multi-categoria entra como 1 cenário se o catálogo de mercado responder bem.

## 2. Análise crítica (premissas da equipe)
| Premissa | Problema | Ajuste proposto |
|---|---|---|
| "Pedir de vários restaurantes sem taxa extra" | 1 carrinho = 1 loja (doc). Cada pedido tem taxa e entrega próprias; o MCP não junta pedidos | "Sem taxa escondida": só divide quando compensa e mostra o custo antes |
| "Checkout unificado" | Não existe tool de checkout multi-loja nem de pagamento dividido. `submitOrder` é por carrinho e **cobra** | Tela de revisão consolidada + N `submitOrder` sequenciais, cada um com consentimento |
| Convidados sem login + pagamento individual (modelo B) | Pagamento só existe na conta de quem está logado (token OAuth). Convidado pagar = convidado logado = **pedido próprio** (não dá para dividir uma transação) | MVP: **modelo A** (organizador paga) + "acerto de contas" calculado (quem deve quanto), sem mover dinheiro |
| Pagamento na entrega | A doc de `listPaymentMethods` cita crédito, débito, Pix, vale-refeição; "na entrega" **não aparece** (NV). Com 2 lojas = 2 entregadores cobrando separado | Não oferecer no MVP; se existir, mostrar "R$ X ao entregador da loja Y" por pedido |
| Sorvete + hambúrguer de lojas diferentes | Entregas independentes; não controlamos entregador | Regra de perecível: evitar dividir; se dividir, usar `scheduledTime` (existe na doc de `setCartDelivery`, NV na prática) para alinhar chegada, ou avisar |
| Consistência entre pedidos | **Não há tool de cancelamento** nas 24. Se o pedido 2 falhar depois do 1 enviado, não dá para desfazer pelo MCP | Validar todos os carrinhos (`getCart`) antes do 1º envio; enviar primeiro o mais arriscado; falhou → propor loja substituta para aquela parte |
| Muitas features (grupo, individual, multi-categoria, dados externos, internacional, cold start) | Escopo de 3 produtos em 18h | 1 núcleo + 1 demo forte; o resto é narrativa com fonte |
| Dados externos (viagem, ocasião) | Sem acesso a parceiros; LGPD; custo de integração | Ocasião **declarada** pelo usuário no prompt já dá o mesmo efeito na demo |

## 3. Três abordagens comparadas (1–5)
| | Impacto | Diferenciação | Viabilidade técnica | Risco operacional (5 = baixo) | Demo | Total |
|---|---|---|---|---|---|---|
| **A. Match em grupo** (multi-loja, organizador paga) | 4 | 5 | 3 | 3 | 5 | **20** |
| **B. Match individual "cesta"** (1 loja, inclui mercado: "jantar p/ 4 até R$ 100") | 4 | 3 | 4 | 4 | 4 | 19 |
| **C. Descoberta contextual / cold start** | 5 | 3 | 2 | 4 | 2 | 16 |
- A ganha na demo e na originalidade; seu risco (2 carrinhos NV) tem plano B: enviar os pedidos em sequência.
- B é o mais seguro; vira o "modo individual" do mesmo núcleo, e um cenário de mercado mostra multi-categoria.
- C é a melhor tese de negócio mas é difícil de provar em 18h sem dados internos → vira argumento de impacto no pitch
  (o Match coleta intenção explícita, que não depende de frequência de pedidos).

## 4. Como definir o "melhor Match" (função de pontuação)
**Restrições duras (código, eliminam a combinação):** restrição alimentar/alergia declarada; orçamento individual;
item e loja disponíveis agora; máx. 2 lojas (3 com confirmação); farmácia sem medicamento de prescrição.

**Pontuação de uma combinação C:**
`S(C) = média_i(sat_i) + α·min_i(sat_i) − β·custo_total/orçamento_total − γ·atraso_max/tempo_alvo − δ·(lojas−1) − ε·risco_perecível`
- `sat_i` (0–1) = aderência do item ao desejo da pessoa i → **LLM** dá nota numa lista curta (≤ 8 itens por pessoa,
  com motivo); ajustado por histórico/persona quando houver (`getRecommendations`, `getUser` tier 3).
- `min_i(sat_i)` = justiça (ninguém fica sem opção boa).
- custo = itens + taxas reais (taxa só aparece com carrinho → NV na busca) − cupons.
- `δ` = custo de dividir (taxa extra, 2 entregas). `ε` = perecível (sorvete/açaí) vindo de loja diferente com ETA
  muito diferente.
- Pesos vêm do **critério dito no prompt** ("barato" ↑β, "rápido" ↑γ) → o LLM só escolhe o perfil; a conta é código.
- Busca: ≤ 3 candidatos por pessoa × lojas → enumeração exaustiva (poucas centenas de combinações), sem solver.

| Decisão | Quem |
|---|---|
| Entender o pedido, separar regra × vontade, perfil de pesos | LLM (saída estruturada) |
| Gerar consultas de busca, ler cardápio/descrição/alérgenos, dar nota de aderência com motivo | LLM |
| Filtrar restrições, somar, aplicar orçamento, enumerar e pontuar combinações, rateio | Código |
| Mediar quando ninguém atende a todos ("Bia, topa poke? todos economizam R$ X") | LLM (texto) + código (números) |
| Ordem do checkout, consentimento, envio, acompanhamento | Código seguindo o MCP |
| Preço, disponibilidade, ETA, taxa, histórico | **Só MCP** (nunca o LLM) |

## 5. O que o MCP permite (tabela investigativa)
| Tool | Para quê | Entradas → saídas relevantes | Limites | Etapa do Match | Afirmar com segurança |
|---|---|---|---|---|---|
| `getUser` | perfil | → nome; tier 2 `paymentMethods`; **tier 3 `userBehaviorDescription` (persona em texto)** | depende do escopo; conta de teste nova (NV) | personalização | só o que vier |
| `listAddresses` | endereço + padrões | → `coordinates`, `topMerchantTypes`, `ordersByDay`/turno | — | início de todo fluxo | região e hábitos |
| `searchOffers` | busca por termo | `query`, lat/long, `refinements`, `resultKind` MERCHANT/ITEM → lojas/itens | query só descritivo; taxa na resposta NV | candidatos | o que retornou |
| `browseOffers` | explorar vertical | `merchantType` (RESTAURANT, GROCERIES, LIQUORSTORE, DRUGSTORE, PETSTORE, SHOPPING) → `rating`, `distance`, `deliveryTime` | — | descoberta | ETA e distância estimados |
| `getRecommendations` | listas personalizadas | `contentMode` → favoritos, recentes, "para você" | conta nova pode vir vazia (NV) | histórico | — |
| `listItemTaxonomy` | categorias | vertical → taxonomia | sem geo | refinar busca | — |
| `getMerchant` | loja | → cardápio, preços, horários, entrega, pagamentos aceitos | tamanho do cardápio de mercado NV | candidatos | preço e itens |
| `getItem` | item | → `optionGroups`, preço promo, **alérgenos, nutrição** (doc; NV) | — | aderência/restrição | — |
| `createCart` | carrinho | merchant + endereço → `cartId` | **não idempotente**; 2 simultâneos NV | montagem | — |
| `addItemToCart` / `updateCartItem` / `removeItemFromCart` | itens | → `cartItemId` | — | montagem | — |
| `getCartDeliveryMethods` | entrega | → `cost`, `estimatedTime`, `availableWindows` | só com carrinho | custo real | taxa e prazo reais |
| `setCartDelivery` | entrega | método + **`scheduledTime`** | agendamento por loja NV | alinhar chegada | — |
| `listPaymentMethods` / `setCartPayment` | pagamento | → crédito, débito, Pix, VR (doc) | **sem split**; "na entrega" NV | checkout | — |
| `listVouchers` / `setVoucher` / `removeVoucher` | cupom | → cupons | — | custo | — |
| `getCart` | conferência | → subtotal, taxas, desconto, total, avisos | — | revisão | **total real** |
| `submitOrder` | envia e **cobra** | `cartId`, `userConsent: true` → `orderId` | **sem cancelamento** no MCP | checkout | pedido criado |
| `trackOrder` / `getOrder` | acompanhar | → status, histórico, `agentHints` | — | pós-venda | status real |
**Lacunas:** pedido multi-loja, pagamento dividido, pagamento por convidado sem login, cancelamento, coordenação de
entregador, taxa antes do carrinho. **Protótipo:** compor N pedidos reais; dividir a conta só como cálculo; o resto
fica explícito como "precisa do iFood".

## 6. Perguntas que a doc/teste precisam responder (em ordem de impacto)
1. Dá para ter 2+ carrinhos abertos e enviar 2 pedidos seguidos? (decide multi-loja)
2. A taxa aparece antes de criar carrinho? Carrinho abandonado expira? (decide custo de comparar)
3. `scheduledTime` funciona em loja comum? (decide sorvete + hambúrguer)
4. `getMerchant` de mercado (GROCERIES) traz o catálogo com preço? `searchOffers` ITEM compara o mesmo produto entre lojas?
5. `getItem` traz alérgenos de verdade? (decide restrição confiável × "segundo a descrição")
6. `getUser` tier 3 e `getRecommendations` funcionam com nossos escopos e com conta de teste?
7. Quais pagamentos a conta de teste aceita? Existe "na entrega"? Rate limit?

## 7. Recomendação de escopo (hackathon)
**Fazer:** núcleo "intenção → cesta viável" · sala do grupo por link/QR (convidado sem login, só texto + orçamento +
restrição) · painel do organizador (quem já respondeu) · botão **Rodar Match** · quadro do resultado (item, loja,
preço, motivo, nota de cada pessoa) · revisão consolidada (subtotais por loja, taxas reais, total, ETA por pedido,
"são 2 pedidos e 2 entregas") · envio sequencial com 1 consentimento por pedido · acerto de contas · trace das tools
MCP visível · modo demonstração com dados gravados (selo) para não depender da internet.
**Adiar:** pagamento individual/split real, pagamento na entrega, dados externos, farmácia, internacional (só pitch),
memória do grupo, agentes por participante.

## 8. Mais agentes?
**No produto:** não criar "um agente por pessoa" nem enxame — custa tokens, latência e rate limit e não melhora a
resposta. Arquitetura: **1 agente** que usa as tools do MCP para descobrir (busca flexível) + chamadas de LLM com
papel fixo (intérprete, juiz de aderência, mediador/explicador) + otimizador e checkout em código. No pitch:
"Entende → Busca → Decide → Fecha".
**No time de desenvolvimento:** os 7 subagentes cobrem o trabalho. Única adição útil: **`jurado`** (Opus, esforço
alto) — avalia pitch e entregáveis contra os 5 critérios da banca antes da submissão (perdemos por 1 ponto).

## 9. Plano de execução (sáb 18h40 → dom 12h30)
| Bloco | Entregável | Pronto quando |
|---|---|---|
| até 19h30 👥 | decisão de escopo + `/executar` | equipe aprovou |
| 19h30–23h 🤖 | fatia vertical **em modo demonstração**: sala/QR, 3 participantes, Rodar Match, quadro, revisão | demo roda de ponta a ponta com dados gravados |
| em paralelo 👥 | acesso ao MCP + contas de teste + respostas das perguntas 1–3 | `list_tools` funciona |
| 23h–03h 🤖 | cliente MCP real (OAuth, sequência do checkout), otimizador com taxa real, trace | 1 pedido real em conta de teste |
| 03h–08h 🤖 | multi-loja real (ou sequencial), mediação, acerto de contas, testes | cenário sorvete+hambúrguer coerente |
| 08h–10h30 | polimento, vídeo plano B, entregáveis 1–6, `jurado` | congelamento 10h30 |
| 10h30–12h30 👥 | ensaio no PC do Thales, submissão | enviado |

## 10. Pesquisa: Large Commerce Model e IA do iFood (pesquisador, 17/10)
**Confirmado (fonte primária):**
- 10/10/2025: iFood + Prosus anunciam o LCM, modelo proprietário (base Qwen 32B + RL) para busca, recomendação e
  jornada de compra ("personal shopper que explica a sugestão"). Sinais: cliques, buscas, compras, cancelamentos,
  avaliações; 14 anos de histórico; base global de transações da Prosus. Também sustenta o **Ailo**.
  https://institucional.ifood.com.br/inovacao/ifood-anuncia-large-commerce-model/
- **Ailo** (assistente de pedidos no WhatsApp e no app, 10/10/2025): https://institucional.ifood.com.br/inovacao/ailo-assistente-de-ia-pedidos/
- **Compr.AI** (compra de mercado pelo WhatsApp): https://institucional.ifood.com.br/inovacao/compr-ai-compra-de-mercado-pelo-whatsapp/
- 20/03/2026: LCM = 90% das interações de IA generativa do iFood (notificações, home, categorias).
  https://institucional.ifood.com.br/releases/ifood-12-milhoes-pedidos/
- 29/06/2026 (Prosus FY2026): sinergias iFood / iFood Pago / Despegar "powered by the LCM"; 21% da receita B2C da
  Despegar no Brasil vem de clientes iFood. https://www.prosus.com/~/media/Files/P/prosus-corp-v2/results-reports-and-events-archive/annual-report/2026/fy2026-media-release.pdf
- OLX, Decolar, Sympla: citadas como empresas do grupo que **poderiam** usar o LCM.
**Não encontrado:** dados de OLX/Decolar/Sympla no treino; parceiro externo ao grupo Prosus. Números de ganho
(66%, 4x, 60x) são do iFood, sem metodologia → citar "segundo o iFood".
**NV:** Ailo "agêntico" com One-Click Buy (16/07/2026), só imprensa.

**Consequência para o Match:** o iFood **já tem** assistente conversacional de pedido (Ailo) e de mercado (Compr.AI).
"IA que pede comida por chat" não é original. O diferencial do Match tem de ser o que eles não mostram publicamente:
**composição para grupo** (N pessoas, orçamentos e restrições diferentes, justiça), **multi-loja com custo
explícito** e **explicação numérica** da escolha. No pitch: "o Match é uma capacidade que o Ailo poderia usar"
(complementa, não concorre). Contexto externo (ex.: viagem via Despegar) = visão, com o caveat de consentimento.

## 11. Pesquisa: internacional e concorrentes (pesquisador, 17/10; "(resumo)" = só li resumo de busca)
**iFood fora do Brasil:** hoje só Brasil. Argentina vendida à PedidosYa (08/2018, https://infonegocios.info/y-ademas/juntos-somos-mas-pedidosya-anuncio-la-adquisicion-de-su-competidor-en-argentina-ifood);
México encerrado em 2020 (fonte secundária); Colômbia encerrada em 11/2022 (https://www.baguete.com.br/noticias/ifood-encerra-operacao-na-colombia).
Grupo: Prosus comprou a Just Eat Takeaway (concluído 10/2025, https://www.retaildetail.eu/news/food/acquisition-of-just-eat-takeaway-completed-the-hard-work-is-just-beginning/)
e vai vender sua fatia na Delivery Hero para a Uber (oferta de 16/07/2026, pendente). No Brasil: Keeta (Meituan) e 99Food.
**Recursos que já existem (fato):**
| Quem | Recurso | Fonte |
|---|---|---|
| Uber Eats (EUA) | 2 lojas próximas, **uma taxa de entrega** (out/2023) | https://techcrunch.com/2023/10/11/uber-eats-now-lets-you-order-from-two-nearby-stores-at-the-same-time |
| Uber Eats | pedido em grupo + split, **1 restaurante** (mar/2022) | https://techcrunch.com/2022/03/09/uber-eats-now-lets-you-split-the-bill |
| DoorDash (EUA/CA) | DoubleDash: 2ª loja após checkout sem taxa extra (2021); grupo com rateio de taxas | https://about.doordash.com/en-us/news/introducing-doubledash-a-new-way-to-shop-multiple-stores-in-one-order · https://help.doordash.com/en-us/business/article/guide-to-group-orders |
| Rappi (inclui BR) | pedido em grupo por link, criador paga (11/2023, resumo) | https://www.supervarejo.com.br/varejo/rappi-lanca-recurso-que-permite-fazer-pedidos-em-grupo |
| Grab (SE Asiático) | grupo com split debitado na carteira de cada um (2020) | https://www.grab.com/inside-grab/stories/grabfood-delivery-group-order/ |
| Swiggy (Índia) | MCP para agentes (Food, Instamart, Dineout), jan/2026 (resumo) | https://www.exchange4media.com/industry-briefing-news/swiggy-launches-model-context-protocol-to-enable-orders-via-chatgpt-and-other-ai-tools-151410.html |
| iFood | testa "combinar pagamentos" (~06/2026, resumo); pedido em grupo: não achado | https://tecnoblog.net/noticias/ifood-testa-opcao-de-dividir-pagamento-com-outra-pessoa/ |
**Consequências:** (1) "pedido em grupo" e "2 lojas com 1 taxa" **já existem lá fora** → não vender como inédito;
a 1 taxa da Uber/DoorDash é logística interna (não alcançável pelo MCP). (2) O inédito é a **composição por IA**:
N pessoas × N lojas × restrições × justiça, com explicação. (3) Pitch internacional: "o Match é a camada que o iFood
leva para qualquer marketplace do grupo Prosus (JET na Europa) sem depender de hábito local: entra texto em qualquer
idioma, sai cesta com pagamento local plugável". Hipótese; teste = mesma engine com cardápio simulado em ES/EN.
Sem dado público de ganho de conversão de pedido em grupo → não citar número.
