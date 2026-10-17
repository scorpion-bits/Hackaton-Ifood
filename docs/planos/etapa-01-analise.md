# Etapa 01 — Análise do tema

- **Status da etapa:** concluída a análise · **aguardando aprovação da ideia** (`/executar <ideia>`)
- **Fontes:** página oficial "Entregas e instruções" (enviada pela equipe), transcrição do vídeo "MCP Portal —
  cadastrar agente" (https://youtu.be/o8uafjBqYRk), transcrição "Config opencode" (https://youtu.be/0C3PYyIjhTM),
  e testes ao vivo no endpoint do MCP em 17/10 (sem credenciais).

## 0. Código feito antes do evento
O enunciado **não traz regra** sobre código prévio (só diz que uso de IA é permitido). 👥 Confirmar com um mentor.
Consequência para o esqueleto (que era genérico, focado em APIs de **lojista**):
- **Reaproveitar:** FastAPI + SQLite, laço do agente com provedores plugáveis, tela de chat mobile com cartões de
  confirmação, scripts Windows/Linux, pasta do pitch.
- **Descartar/substituir:** cliente da Merchant API (`backend/app/ifood/real.py`) e ferramentas de vendedor.
- **Reaproveitar com outra função:** nosso `mcp_server.py` vira um **simulador offline** com as mesmas tools do MCP
  real (plano B da demo sem internet), depois que soubermos os nomes reais das tools.

## 1. O desafio (oficial)
- **Missão:** "construir um agente de IA capaz de operar o MCP do iFood para realizar pedidos — da escolha do
  restaurante ao fechamento do carrinho", juntando "agentes conversacionais e ferramentas determinísticas".
- **Horários (mudou!):** desenvolvimento **sáb 13h → dom 12h30** (submissão às 12h30), pitches **dom 13h–16h**,
  resultado 17h. São ~23h30 de desenvolvimento, não 29h.
- **Critérios (5 pilares, sem pesos publicados):** Visão & Originalidade · Arquitetura & Engenharia (qualidade do
  código, **uso correto do MCP**, robustez) · Design & Experiência · Impacto · Comunicação & Pitch.
- **6 entregáveis obrigatórios:** 1) Proposta de negócio · 2) Desenho de solução · 3) Racional da experiência (UX) ·
  4) Interface visual · 5) Documento técnico resumido · 6) **Feedback sobre os MCPs** (dores reais de uso).
- Prêmios: R$ 4.000 / 2.000 / 1.000. ~10 mentores do iFood.

## 2. Quem é o cliente e qual a dor
O **consumidor** que pede comida. O iFood quer saber se agentes conseguem levar alguém "da escolha ao pedido
fechado". A dor real é a **decisão**, mais do que o clique: rolar o app, comparar taxa e tempo, conciliar gosto,
restrição e orçamento, e pedir em grupo. O tema "Vendendo com Agentes" é o ponto de vista do iFood: vender **por
meio** de agentes de compra.

## 3. O que o MCP do iFood permite (verificado)
| Fato | Fonte |
|---|---|
| Endpoint MCP remoto `https://consumer-mcp.ifood.com.br/marketplace` (Streamable HTTP: `POST`; `GET` = 405) | vídeo opencode + teste ao vivo |
| Sem token → **401** com `resource_metadata` → servidor de autorização `https://id.ifood.com.br` | teste ao vivo |
| OAuth 2.0: `authorize`/`token` em `id.ifood.com.br`, grant **authorization_code + refresh_token**, **PKCE S256**, client secret (basic/post). **Sem registro dinâmico** → usar `client_id`/`secret` do Portal | teste ao vivo (`/.well-known/openid-configuration`) |
| **4 MCPs, 24 tools** — User: `getUser`, `listAddresses`, `createAddress` · Offer Discovery: `searchOffers`, `browseOffers`, `getRecommendations`, `listItemTaxonomy`, `getMerchant`, `getItem` · Cart (13): `createCart`, `addItemToCart`, `updateCartItem`, `removeItemFromCart`, `getCart`, `getCartDeliveryMethods`, `setCartDelivery`, `listPaymentMethods`, `setCartPayment`, `listVouchers`, `setVoucher`, `removeVoucher`, `submitOrder` · Order: `trackOrder`, `getOrder` | [docs](https://mcp-developer.ifood.com.br/pt-BR/docs/guides) / [llms-full.txt](https://mcp-developer.ifood.com.br/llms-full.txt) — resumo em `docs/mcp-ifood.md` |
| Carrinho = **1 restaurante + 1 endereço**; ordem obrigatória `createCart → addItemToCart → getCartDeliveryMethods → setCartDelivery → listPaymentMethods → setCartPayment → submitOrder` | docs |
| `submitOrder` exige **`userConsent: true`** (consentimento explícito) — casa com a nossa regra de confirmação humana | docs |
| `listAddresses` traz dados comportamentais (`topMerchantTypes`, pedidos por dia/turno); `getRecommendations` dá favoritos e pedidos recentes; há **cupons** (`listVouchers`/`setVoucher`) | docs |
| `trackOrder`: o servidor diz quando consultar de novo (`agentHints.retryMessage`) e quando parar (`pollingStop`) | docs |
| A doc cita `auth.ifood.com`, `api-mcp.ifood.com/v3/*`, `mcp.ifood.dev` e o pacote npm `@ifood/mcp-sdk` → **nenhum existe** (DNS falha / 404 no npm). O real é `id.ifood.com.br` + `consumer-mcp.ifood.com.br/marketplace` | testes ao vivo 17/10 |
| Login por QR code ("Pending Action", `/device`) está na doc, mas **não aparece** nos metadados OAuth reais → **NÃO VERIFICADO** | teste ao vivo |
| Escopos podem dar acesso a nome, e-mail, telefone, CPF, endereços salvos, **dados comportamentais**, criação de pedido | vídeo portal |
| Fluxo provado pelo iFood: cadastrar endereço → buscar "pizza de muçarela" → adicionar ao carrinho → finalizar com **Pix** (gera código) → acompanhar status | vídeo opencode |
| **Contas de teste:** até 10 por conta do Portal; pedido percorre todos os status mas **não vai ao restaurante**; códigos de login (e-mail/SMS/WhatsApp) são gerados no Portal, uso único | vídeo portal |
| Contas de teste: só depois do agente aprovado; **apagadas 15 dias após a criação**; Pix de teste pago **não é reembolsado** | [doc](https://mcp-developer.ifood.com.br/pt-BR/docs/guides/first-steps/test-account) |
| Nomes e parâmetros das tools: documentados, mas a doc tem erros (ver linha das URLs) → confirmar com `list_tools` no primeiro acesso | docs + bom senso |
| Dica do iFood: modelos fracos se confundem com os **muitos IDs** das tools | vídeo opencode |

**Como pedir o acesso (passo a passo, 👥 hoje cedo):**
1. Pegar com o time do iFood o link do **MCP Developer Portal** e criar conta.
2. Menu no seu nome → gerenciamento de agentes → **Criar agente**: logo (pode ser gerada por IA; só há limite de
   tamanho), nome, descrição curta, **Redirect URL**, termos de uso e privacidade (pode ser genérico).
3. **Escopos: marcar TODOS.** Depois de ativo não dá para mudar (teria que criar outro agente).
4. Finalizar → o agente entra em **homologação** (alguém do iFood aprova). **Fazer isso primeiro: é a fila.**
5. Aprovado: copiar o `client_id` e **gerar o `client_secret` (aparece uma vez só)**. Guardar só no `.env` ou num
   gerenciador de senhas; nunca no git nem em mensagem de grupo.
6. Criar **usuários de teste**. No login do iFood use o e-mail ou telefone do usuário de teste e o código gerado no
   Portal ("gerar código"; o de telefone serve para SMS ou WhatsApp conforme a tela pedir).
7. Explorar as tools com o **opencode** (como no vídeo): `opencode mcp add` → remoto → URL acima → OAuth com
   client id/secret → na config, `redirect` igual ao do Portal → `opencode mcp auth <nome>`.

**Atualização 17/10:** o formulário real aceita **várias Redirect URLs** → um agente só ("IBits") com o callback do app e o do opencode. O texto abaixo ficou como histórico.

**Redirect URL (decisão importante, não dá para mudar):** hoje é **uma por agente**. Sugestão: cada membro cria a
própria conta e agente. O agente do **Milan** fica com `http://localhost:8000/oauth/callback` (o nosso app) e o do
**Thales** com o redirect do opencode (exploração). 👥 Confirmar com um mentor se pode ter mais de um agente por
equipe.

**Papel do MCP no nosso produto:** o backend vira **cliente MCP** do iFood (OAuth com PKCE). O LLM escolhe e explica;
o **código determinístico** garante as regras: orçamento, divisão da conta, confirmação humana antes do checkout.
É a frase do enunciado: "agentes conversacionais e ferramentas determinísticas trabalhando juntos".

## 4. Ideias
O enunciado favorece **COMPRA**: o único MCP oferecido é o do consumidor. Ideias de VENDA não têm MCP para usar.

### A) "Racha Aí" — pedido em grupo · **COMPRA**
- **Problema:** pedir para 3–8 pessoas (república, time, escritório) é caótico. Cada um quer uma coisa, tem
  restrição e orçamento diferentes, e alguém paga e cobra depois.
- **Usuário:** quem organiza o pedido do grupo.
- **O agente:** abre uma "mesa" (link/QR); cada pessoa diz em linguagem natural o que quer e quanto pode gastar. O
  agente busca restaurantes que atendem **todos**, monta **um carrinho só**, mostra quanto cada um paga (com taxa
  rateada), explica a escolha, pede **confirmação do organizador** e fecha com Pix. Depois acompanha o pedido.
- **MCP:** `listAddresses`, `searchOffers`/`getMerchant`/`getItem`, `createCart`/`addItemToCart`, entrega, pagamento,
  `listVouchers`, `submitOrder(userConsent)`, `trackOrder`. **Determinístico:** divisão, limites de orçamento,
  regra "todos atendidos".
- **Sinal do iFood:** a home do portal cita "Automação corporativa — *'Alexa, pede almoço para a equipe de
  engenharia'*" como caso de uso. Aderência máxima; o diferencial vem da mesa com QR e da divisão justa.
- **Demo de 2 min / momento uau:** 3 pessoas da plateia escaneiam o QR e mandam pedidos pelo celular ("sem carne",
  "até R$ 30", "quero algo doce"). Em ~30 s aparece um restaurante que atende todo mundo, o carrinho pronto e a
  divisão por pessoa. Confirma → Pix → status do pedido ao vivo (conta de teste).
- **Risco técnico:** carrinho é de um restaurante só (achar um que agrade a todos pode falhar → explicar e oferecer
  o "melhor possível"); várias pessoas ao mesmo tempo na tela; nomes de tools ainda desconhecidos.

### B) "Pede pra mim" — pedido por voz/foto, acessível · **COMPRA**
- **Problema:** idosos, pessoas com deficiência visual ou motora e quem está com as mãos ocupadas têm dificuldade
  com o app.
- **O agente:** recebe voz ("o de sempre, mas sem cebola") ou **foto de um prato** e acha o item. Usa
  `getRecommendations` (pedidos recentes e favoritos) para "o de sempre", lê as opções em voz alta e confirma
  por voz. A home do portal também cita "Acessibilidade por voz".
- **MCP:** `getRecommendations`, `searchOffers`, `getItem`, carrinho, `submitOrder`, `trackOrder`.
- **Uau:** foto de um prato → em segundos o pedido montado no restaurante mais próximo.
- **Risco:** reconhecer a imagem com modelo gratuito, a qualidade da voz no ambiente do evento e o escopo de
  histórico funcionar com conta de teste.

### C) "Cabe no bolso" — pedido com orçamento real · **COMPRA**
- **Problema:** o preço do item engana; taxa, entrega e mínimo mudam tudo.
- **O agente:** "tenho R$ 35, tô com fome de algo quente" → compara o **custo total** de várias lojas (taxa via
  `getCartDeliveryMethods`, cupons via `listVouchers`), escolhe e explica a conta.
- **Uau:** tabela "preço anunciado × preço real" e o agente trocando de loja para caber no orçamento.
- **Risco:** baixo; menos original (parece filtro).

### D) "Sem medo" — restrição alimentar e alergia · **COMPRA**
- **Problema:** celíacos, alérgicos e veganos gastam muito tempo lendo descrições e erram.
- **O agente:** filtra pelas descrições do catálogo, marca o grau de certeza ("a descrição não fala de glúten → não
  sei") e nunca afirma o que não está escrito.
- **Uau:** "sou celíaca, quero pizza" → 3 opções com o motivo de cada uma e um aviso honesto.
- **Risco:** o catálogo pode não ter ingredientes. A demo fica fraca se os dados forem pobres.

### E) Agente comprador × agente vendedor · **OS DOIS**
- **Ideia:** o agente do cliente negocia com um agente do restaurante (combo ou desconto) via MCP.
- **Risco:** **não existe MCP de lojista no evento** → o lado vendedor seria todo simulado. A banca avalia "uso
  correto do MCP do iFood" → baixa aderência.

## 5. Notas (1–5)
Pesos: aderência ×1 · uso real de IA+MCP ×2 (pilar Arquitetura) · impacto ×2 · viabilidade em ~23h ×2 ·
força da demo ×2 (pilares Design + Pitch) · diferencial ×2 (pilar Visão). Máximo 55.

| Ideia | Aderência | IA+MCP | Impacto | Viabilidade | Demo | Diferencial | **Total** |
|---|---|---|---|---|---|---|---|
| A) Racha Aí (grupo) | 5 | 5 | 4 | 3 | 5 | 4 | **47** |
| B) Pede pra mim (voz/foto) | 5 | 4 | 4 | 3 | 5 | 4 | **45** |
| C) Cabe no bolso | 5 | 4 | 4 | 4 | 3 | 2 | **39** |
| D) Sem medo | 5 | 4 | 4 | 3 | 3 | 3 | **39** |
| E) Comprador × vendedor | 2 | 2 | 3 | 2 | 3 | 4 | **30** |

## 6. Recomendação
**A) Racha Aí.** Toda universidade e escritório vive esse problema (a banca inclusive). A ideia usa o fluxo inteiro
do MCP e tem a demo mais forte: a plateia participa. Se sobrar tempo, pegamos de B a **entrada por voz** no celular
(Web Speech API do navegador, sem custo).

**MVP — entra:**
- login do organizador com conta de teste (OAuth) e endereço;
- "mesa" com link/QR; cada pessoa manda o pedido em texto;
- busca e escolha de **um** restaurante, com explicação;
- carrinho único e divisão por pessoa com a taxa rateada;
- cartão de confirmação → checkout Pix → acompanhar pedido;
- botão "Recarregar demo";
- `docs/feedback-mcp.md` alimentado desde a primeira hora.

**MVP — fica fora:** cobrança automática de cada pessoa (só mostra quanto cada um deve), vários restaurantes,
pagamento com cartão, voz (opcional), app nativo.

**Plano por horas (sáb 13h → dom 12h30):**
| Quando | Marco |
|---|---|
| Sáb 13h–14h | 👥 Criar contas + agentes no Portal (homologação!) · aprovar a ideia · Claude escreve o plano da etapa 02 |
| 14h–17h | Explorar as tools no opencode (Thales/Zenon) → anotar nomes e erros · backend cliente MCP + OAuth (Milan + agentes) |
| 17h–21h | **Fatia vertical:** 1 pessoa → busca → carrinho → Pix de teste → status, na nossa tela |
| 21h–01h | Mesa em grupo + divisão + explicação · pitch v1 · simulador offline (plano B) |
| 01h–07h | Revezamento de sono · polimento só do fluxo da demo |
| Dom 07h–10h30 | Gravar o vídeo plano B · 6 entregáveis escritos · ensaio |
| **10h30** | 🧊 Congelamento de código |
| 12h30 | **Submissão** · 13h pitches |

**Quem faz o quê:**
- **Milan:** cliente MCP + OAuth e prompt do agente.
- **Thales:** telas e pitch, e cria o 2º agente para o opencode.
- **Zenon:** explora as tools e escreve o feedback do MCP e o roteiro.
- **Antonio:** testes no Windows e na rede do evento, contas de teste.

**Subagentes em paralelo:**
- `dev-backend` + `dev-mcp-ifood` (opus/high): cliente MCP, OAuth e simulador;
- `dev-frontend` (sonnet/medium): mesa, QR e divisão;
- `pitch-demo` (opus/medium): proposta de negócio, racional de UX e slides;
- `pesquisador` (sonnet/medium): números do problema "pedido em grupo", com fonte;
- `qa-testador` a cada entrega.

## Perguntas para a equipe (máx. 3)
1. Aprovam a ideia **A** (ou outra, ou uma combinação)?
2. 👥 Perguntar aos mentores: (a) pode cada membro criar o próprio agente/redirect? (b) quanto tempo dura o pitch e
   onde se submete? (c) quanto tempo leva a homologação do agente?
3. Alguém consegue uma chave de IA paga (Claude/OpenAI)? O próprio iFood avisa que modelo fraco se perde nos IDs. Se
   não, usamos Gemini gratuito e compensamos com mais lógica determinística.

## 7. Discussão da equipe (17/10) — pendente de aprovação
- **IA × algoritmo (Milan):** o algoritmo faz conta e regra (filtro, soma, rateio, orçamento, ordem do checkout); a IA
  faz o que é texto livre ou ambíguo (desejo vago → `query`, ler descrição do cardápio, separar regra de vontade,
  mediar o grupo, recuperar de erro). Teste: "dá para escrever um `if`?" → código. Ideia C descartada (só conta).
- **Medo de "mais um chatbot":** formato proposto **"Mesa"** — várias pessoas, 1 frase cada via QR (sem login delas;
  só o organizador entra no iFood), quadro visual ao vivo (cartões, ✓ por restrição, rateio), agente que só pede o
  "ok"; memória do grupo ("o de sempre") como extra.
- **Limite de 1 restaurante por pedido (confirmado na doc):** (a) achar UM restaurante — a IA lê cardápios para
  achar os generalistas; (b) extra: dividir em 2 pedidos mostrando o custo (+taxa, horários diferentes) — **NÃO
  VERIFICADO** se o MCP permite 2 carrinhos abertos ao mesmo tempo; (c) negociar antes de dividir.
- **Pedidos discrepantes:** IA separa **regra** (alergia, restrição, orçamento) de **vontade** (sabor) → algoritmo
  pontua restaurantes (regras obrigatórias; justiça: ninguém sem opção) → se nenhum atende todos, a IA **media**:
  pergunta só a quem trava ("Bia, topa poke em vez de sushi? todos economizam R$ X") → se ninguém ceder, mostra
  "1 pedido, 4/5 felizes" × "2 pedidos, todos felizes, +taxa". Momento uau da demo: negociação ao vivo.
- **Primeiros testes com acesso:** 2 carrinhos simultâneos? `getMerchant` traz cardápio completo com descrições?
  Onde e quanto varia a taxa (`getCartDeliveryMethods`)?
