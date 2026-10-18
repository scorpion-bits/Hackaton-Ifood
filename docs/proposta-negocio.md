# Match — proposta de negócio

> Entregável 1 do Hackathon SEMCOMP × iFood "Vendendo com Agentes". Leitura de 5 minutos.
> Protótipo de hackathon, não afiliado ao iFood. Todo número tem fonte com link (acesso em 17/10/2026, salvo
> indicação). O que é **hipótese** está escrito assim e diz como validar. Fontes detalhadas: `docs/pesquisa-mercado.md`.

## 1. Resumo

1. **Problema:** pedir comida em grupo exige que alguém vire o "gerente do pedido": pergunta o que cada um quer, acha
   lojas que agradem todo mundo, cabe no bolso de cada um, monta o carrinho e depois cobra a vaquinha.
2. **Solução:** no **Match**, cada pessoa escreve uma frase ("japonês até R$ 45", "sem carne"); um **agente vendedor
   por restaurante**, que só enxerga o próprio cardápio, disputa o pedido; o **IBits**, agente comprador da turma,
   escolhe a melhor combinação (1 ou mais lojas) com justiça entre as pessoas, tudo sobre o **MCP do iFood**. Nada sai
   sem o ok do organizador.
3. **Por que agora:** comércio feito por agentes já está em produção. O Google lançou o protocolo de pagamentos para
   agentes AP2, que funciona sobre o MCP ([Google, 16/09/2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol));
   a Visa lançou o Intelligent Commerce ([Visa, 30/04/2025](https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.21361.html));
   a Swiggy, na Índia, recebe pedidos de comida por MCP desde janeiro ([Swiggy, 27/01/2026](https://www.swiggy.com/corporate/press-release/swiggy-now-lets-you-order-food-dineout-and-shop-on-instamart-directly-inside-chatgpt-and-claude/));
   e o próprio iFood fecha **um** pedido em cerca de 30 segundos no Ailo com o One-Click Buy ([Canaltech, 16/07/2026](https://canaltech.com.br/apps/nova-ia-do-i-food-deixa-voce-fazer-pedidos-no-whats-app-com-apenas-um-clique)).
   Falta o pedido **da turma**.

## 2. Problema e público

**Ocasiões:** turma da faculdade depois da aula, república na sexta à noite, almoço do time no trabalho, jantar de
família no domingo, jogo do Brasil com os amigos.

| Quem | Dor hoje |
|---|---|
| **Organizador** (quem tem o app e o cartão) | Faz a logística sozinho no grupo de WhatsApp, adianta o dinheiro e depois cobra Pix de cada um |
| **Convidados** | Fila de mensagens, "tanto faz", alguém cede o restaurante que queria ou fica com o que não queria; quem tem restrição (vegetariano, sem lactose) sobra |

**Não existe número público brasileiro** sobre pedido de delivery em grupo (frequência, tempo para decidir,
desistência). Procuramos e não achamos (ver `docs/pesquisa-mercado.md` §4). Por isso fizemos nossa própria pesquisa.

> **Pesquisa da equipe, SEMCOMP São Carlos, 17–18/10/2026, n = [preencher], n que já pediu em grupo = [preencher].**
> Amostra de conveniência (participantes de um evento de computação), anônima, não representativa.
> - Pediram delivery em grupo no último mês: [preencher]%
> - Levaram **mais de 15 min** para decidir: [preencher]%
> - **Cada um pediu separado** no próprio app: [preencher]%
> - Tiveram **atrito** (alguém desistiu, ficou com o que não queria ou o grupo desistiu): [preencher]%
> - Alguém **queria outro restaurante**: [preencher]%
> - Alguém **adiantou e cobrou Pix depois** (ou ficou faltando dinheiro): [preencher]%
> - Intenção de uso do Match: média [preencher] de 5; notas 4 ou 5: [preencher]%
> - Principais objeções: [preencher]
>
> (Se n < 20, trocar porcentagens por "X de Y pessoas".)

**Apoio de fora (outros países, encomendados, não são do Brasil):** no Reino Unido, quase metade dos entrevistados diz
que escolher onde comer em grupo leva em média 25 minutos (OnePoll para Meerkat Meals, 2018, amostra não informada;
[Public Sector Catering](https://publicsectorcatering.co.uk/news/guess-how-long-brits-spend-deciding-where-eat-out)).
Nos Emirados, 43% dizem gastar perto de 20 minutos decidindo o que pedir online (YouGov para Deliveroo, 2022;
[Deliveroo UAE](https://deliveroo.ae/more/news-articles/indecisive-on-what-to-order-try-deliveroo-s-spin-the-meal)).

## 3. Solução e diferenciais

Como funciona em 5 passos: (1) o organizador cria a sala no iFood e mostra o QR; (2) cada convidado entra **sem
login** e escreve uma frase em até 30 s; (3) os agentes das lojas fazem seus lances, com preço e prazo **vindos do
MCP**; (4) o IBits monta até 3 combinações e o grupo dá "Match"; (5) pagamento **junto** ou **separado** (vaquinha:
Pix direto para a chave do organizador; o pedido só sai com **100% pago**), conferência do carrinho real e "deslize
para enviar".

**Pedido em grupo já existe lá fora e no Brasil.** Não vendemos isso como inédito. O que é novo é a **composição por
IA** para N pessoas em N lojas.

| | Rappi (inclui Brasil) | Uber Eats | DoorDash | Ailo (iFood) | **Match** |
|---|---|---|---|---|---|
| Pedido em grupo por link | sim, criador paga ([Supervarejo, 11/2023](https://www.supervarejo.com.br/varejo/rappi-lanca-recurso-que-permite-fazer-pedidos-em-grupo); só vimos o resumo da matéria) | sim, 1 restaurante, com divisão da conta ([TechCrunch, 03/2022](https://techcrunch.com/2022/03/09/uber-eats-now-lets-you-split-the-bill)) | sim, com rateio de taxas ([DoorDash](https://help.doordash.com/en-us/business/article/guide-to-group-orders)) | não citado pelo iFood ([iFood](https://institucional.ifood.com.br/inovacao/ailo-assistente-de-ia-pedidos/)) | sim, convidado sem login |
| Mais de 1 loja | não encontrado | 2 lojas próximas, 1 taxa ([TechCrunch, 10/2023](https://techcrunch.com/2023/10/11/uber-eats-now-lets-you-order-from-two-nearby-stores-at-the-same-time)) | DoubleDash, 2ª loja após o checkout ([DoorDash](https://about.doordash.com/en-us/news/introducing-doubledash-a-new-way-to-shop-multiple-stores-in-one-order)) | não | sim, até 3 lojas (N pedidos, N taxas, avisado antes) |
| Quem escolhe os itens | cada pessoa, à mão | cada pessoa, à mão | cada pessoa, à mão | IA, para **1 pessoa** | IA, para **o grupo**, com justiça |
| Frase livre ("algo leve até R$ 30") | não | não | não | sim (1 pessoa) | sim, por pessoa |
| Lojas disputando o pedido | não | não | não | não | sim, um agente por loja |
| Trava "só sai com 100% pago" | não encontrado | não encontrado | não encontrado | — | sim |

Diferenciais em uma linha cada:
- **Composição por IA:** N pessoas × N lojas × orçamentos e restrições diferentes. O otimizador puxa para cima quem
  ficou pior (ninguém fica mal atendido para os outros ganharem).
- **Lojas disputando:** cada restaurante tem um agente vendedor. Não encontramos iniciativa pública de agente de
  restaurante negociando com agente do comprador em delivery (não dizemos "ninguém faz").
- **Vaquinha com trava:** o pedido só é enviado quando todos pagaram; prazo de 10 min + 2 min por pessoa acima de 2.
- **Números só do iFood:** preço, taxa e prazo vêm das tools do MCP. Fala de agente com número inventado é trocada
  por texto pronto.
- **Nada sai sem ok:** `submitOrder` só depois de confirmação humana explícita.

## 4. Valor para o iFood

**(a) Pedido de grupo que hoje não acontece ou vira pedidos picados.** *Hipótese a validar:* quando o grupo não se
entende, ou ninguém pede, ou cada um pede separado (com N taxas e N entregas), ou o grupo vai comer fora. O Match
transforma isso em um pedido organizado. Validação: indicadores de atrito e "cada um pediu separado" da nossa
pesquisa (§2) e o piloto (§5).

**(b) Mais lojas por sessão.** Um grupo com vontades diferentes pode fechar em 2 ou 3 lojas em vez de alguém ceder.
*Hipótese:* mais lojas atendidas por ocasião, sobretudo lojas de nicho (vegana, sem glúten, sobremesa).

**(c) Nova linha de receita: "Patrocinado" no canal de agentes.** O modelo é comprovado: anúncio de loja dentro do
app de delivery passa de US$ 1 bilhão por ano na Uber ([Digiday, 08/05/2025](https://digiday.com/media/qa-uber-ads-hits-1-5-billion-run-rate-as-it-hires-first-head-of-measurement/))
e na DoorDash ([transcrição da fala de resultados, 06/08/2025](https://www.marketbeat.com/earnings/reports/2025-8-6-doordash-inc-stock)).
O iFood já tem o **iFood Ads**: leilão em que a loja define um lance **por visita** ao cardápio, e a posição depende
também de avaliação e indicadores operacionais. Frase do próprio iFood: **"Dinheiro sozinho não compra posição."**
([Blog iFood Parceiros, 18/09/2026](https://blog-parceiros.ifood.com.br/como-usar-ifood-ads-para-crescer-na-plataforma/)).
E o iFood quer **multiplicar por 5** a frente de Ads até 2030 ([Startups, 12/11/2025](https://startups.com.br/negocios/ifood-compra-a-advolve-e-mira-crescimento-de-5x-em-ads-ate-2030/)).

O Patrocinado leva essa regra ao extremo, no momento em que um **agente** compra:
- A loja patrocinada tem o lance **mostrado primeiro**, com o rótulo "Patrocinado".
- O pagamento **nunca** muda nota, filtro ou escolha do IBits. Na demo, a patrocinada fala primeiro e **perde**.
- **O iFood vende atenção, não a decisão.** O agente comprador trabalha para o grupo; se ele pudesse ser comprado,
  ninguém confiaria nele, e o canal inteiro perderia valor.
- Rótulo sempre visível, em texto (não só cor), cumprindo o princípio da identificação da publicidade do CDC
  ([Lei 8.078/1990, art. 36](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm): "A publicidade deve ser
  veiculada de tal forma que o consumidor, fácil e imediatamente, a identifique como tal"; site do Planalto fora do ar
  em 18/10, texto conferido em [Meu Site Jurídico](https://meusitejuridico.editorajuspodivm.com.br/2018/10/09/art-36-cdc-violacao-principio-da-identificacao-da-publicidade/)).
- No protótipo, o Patrocinado é **demonstração**; no modo real nenhuma loja é patrocinada.

**(d) Uma capacidade que o Ailo pode usar.** O Ailo já entende pedido por conversa e tem 48% mais chance de a busca
virar pedido, segundo o iFood ([iFood, 10/10/2025](https://institucional.ifood.com.br/inovacao/ailo-assistente-de-ia-pedidos/)).
O Match não concorre com ele: é a peça de **grupo** (vários desejos, várias lojas, justiça, vaquinha) que pode
entrar no Ailo e no app, ao lado do pagamento agêntico que o iFood já lançou ([Mobile Time, 28/08/2026](https://www.mobiletime.com.br/noticias/28/08/2026/ifood-pagamento-agentico/)).

**(e) Dados de preferência de grupo, com consentimento.** Que combinações de lojas os grupos aceitam, que restrições
aparecem juntas, quanto cada perfil aceita gastar. Só agregado e com consentimento explícito; o convidado sem login
guarda as próprias preferências no aparelho dele.

**Escala do iFood** (para dimensionar, não é projeção nossa): mais de 180 milhões de pedidos por mês, 65 milhões de
clientes e mais de 500 mil estabelecimentos ([Portal de Dados iFood](https://institucional.ifood.com.br/portal-de-dados-ifood/)).
Não temos dado de quantos desses pedidos são de grupo; não estimamos.

## 5. Modelo de negócio e métricas

**Como o Patrocinado cobraria (proposta, sem preço):**
- Mesma lógica do iFood Ads: a loja define orçamento diário e um **lance por aparição no leilão** do Match (equivalente
  ao lance por visita de hoje). Paga só quando o lance dela é mostrado a um grupo.
- Ordem de exibição entre patrocinadas = lance × qualidade (avaliação, cancelamento, tempo de entrega), como no iFood
  Ads.
- Entra na **Central de Crescimento** do Portal do Parceiro, junto do iFood Ads de hoje.
- Preço: definido pelo iFood. **Não temos e não inventamos** valor; o iFood também não divulga receita de Ads.

**Receita principal continua a mesma:** comissão e taxa de cada pedido. Um Match com 3 lojas gera 3 pedidos.

**Métricas de sucesso**

| Métrica | O que mostra |
|---|---|
| % de salas que viram pedido | o Match tira o grupo da indecisão? |
| Tempo da sala criada até o pedido enviado | o organizador economiza trabalho? |
| Itens por pedido de grupo e pessoas por sala | o pedido de grupo é maior que a soma dos picados? |
| Lojas por sessão | mais lojas atendidas por ocasião? |
| % de vaquinhas que fecham no prazo | a trava de 100% funciona sem irritar? |
| CTR do Patrocinado (abriu a loja depois de ver o lance) | a atenção vendida tem valor para a loja? |
| % de grupos que dão match no 1º cartão | a IA acerta? |
| NPS do organizador e do convidado, separados | os dois lados saem satisfeitos? |

**Piloto proposto:** 4 semanas numa cidade universitária como São Carlos (muitas repúblicas e turmas).
- Grupo A: entrada "Pedir em grupo? Dê um Match" na home. Grupo B: app como hoje.
- Semana 1–2 sem Patrocinado; semana 3–4 com Patrocinado para lojas voluntárias, para medir se o rótulo muda a
  confiança (NPS e % de salas que viram pedido não podem cair).
- Critério de sucesso: definido com o iFood antes de começar (não chutamos número).

## 6. Viabilidade

**O que já funciona (protótipo):** o fluxo inteiro em modo demonstração (sala, frases livres, leilão, deck, vaquinha
com Pix "copia e cola" real, conferência e envio com consentimento); cliente do MCP real com OAuth PKCE seguindo a
sequência da documentação (`listAddresses` → busca → carrinho → `getCart`); [preencher: até onde o MCP real rodou no
PC da equipe e latência medida no rastro]. Detalhes em `docs/tecnico.md`.

**O que falta para produção**

| Falta | Caminho |
|---|---|
| Agente da loja feito pelo próprio restaurante | Hoje simulamos o agente com o cardápio público do MCP. Em produção, a loja pluga a própria política (promoção, combo) pelo Portal do Parceiro / Merchant API; o iFood controla as regras (validação, rótulo, sem número inventado) |
| Vaquinha sem Pix manual | **iFood Pago** recebendo cada parte (nosso app não pode guardar dinheiro de terceiros; intermediar pagamento exige instituição autorizada). O iFood Pago já existe ([Prosus FY2026](https://www.prosus.com/~/media/Files/P/prosus-corp-v2/results-reports-and-events-archive/annual-report/2026/fy2026-media-release.pdf)) e o iFood testa dividir o pagamento ([Tecnoblog](https://tecnoblog.net/noticias/ifood-testa-opcao-de-dividir-pagamento-com-outra-pessoa/)) |
| 1 entrega para lojas próximas | Logística interna, como Uber Eats e DoorDash já fazem (§3). Pelo MCP não dá: hoje N lojas = N entregas, e o app avisa |
| Antifraude da vaquinha | Confirmação automática do pagamento (no lugar do "recebi" do organizador), limite por sala, detecção de salas falsas |
| Grupos grandes | Hoje até 6 pessoas por sala (limite do otimizador); para 15+, poda por loja e votação no deck |

**Riscos e mitigação**

| Risco | Mitigação |
|---|---|
| Alergia: o cardápio nem sempre informa | Restrição vira "segundo a descrição" + aviso "pode não estar informado, confirme com a loja" |
| Patrocinado minar a confiança | Só ordem de exibição, nunca a escolha; rótulo em texto; teste no piloto (semana 3–4) |
| Custo de LLM com vários agentes por Match | Um agente por loja, em paralelo, com tempo máximo; **fallback determinístico** sem LLM (a demo inteira roda sem chave); custo medido: [preencher, se medido no ensaio] |
| Limite de chamadas (rate limit, erro 429) | Fallback cobre o erro; produção: cache de cardápio por loja e lote de chamadas |
| IA inventar preço | A IA não escreve número que não veio de uma tool; fala com número fora do lance cai no texto pronto |
| Pedido enviado sem querer | Só com confirmação humana; `getCart` de novo antes de enviar; se o total mudou, pede novo ok |

## 7. Visão

**Além do Brasil.** O iFood hoje opera só no Brasil (saiu da Colômbia em 11/2022, [Baguete](https://www.baguete.com.br/noticias/ifood-encerra-operacao-na-colombia)), mas o grupo Prosus concluiu a compra da Just Eat Takeaway em
10/2025 ([RetailDetail](https://www.retaildetail.eu/news/food/acquisition-of-just-eat-takeaway-completed-the-hard-work-is-just-beginning/)).
*Hipótese:* o Match é uma camada que funciona em qualquer marketplace do grupo, porque entra texto em qualquer idioma
e sai uma cesta com pagamento local plugável. Validação: a mesma engine com cardápio simulado em inglês e espanhol.

**Além de comida.** O iFood já vende mercado, farmácia, pet e bebidas ([iFood, 04/06/2026](https://institucional.ifood.com.br/clientes/ifood-e-mais-que-comida/)),
e os mentores do evento confirmaram que o catálogo de mercado vem com preço no MCP (`docs/planos/etapa-01b-match-estrategia.md` §12).
A mesma lógica serve para a compra do mês da república (cada um diz o que precisa, a IA divide em lojas e a vaquinha
fecha) ou a farmácia da família.

**A frase:** no canal de agentes, o iFood pode vender **atenção** para as lojas sem nunca vender **a decisão** do
cliente. O Match mostra que dá para ter as duas coisas no mesmo pedido.
