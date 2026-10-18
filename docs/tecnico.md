# Match — desenho de solução e documentação técnica

> Entregáveis 2 (desenho de solução) e 5 (documentação técnica) do Hackathon SEMCOMP 29 × iFood.
> Protótipo de hackathon, não afiliado ao iFood. Como rodar: [`README.md`](../README.md).
> Estado do código em 18/10/2026 (madrugada). O que ainda depende de dado externo vem marcado **[pendente]**.

## 1. Visão geral

O Match transforma frases livres de 1 ou N pessoas em um pedido viável no iFood: itens reais, preço real, loja(s)
real(is), custo total e motivo de cada escolha. Só o organizador entra no iFood; os convidados entram por link/QR,
sem login.

Divisão de trabalho entre IA e código (decisão central do projeto):

| Quem | Faz |
|---|---|
| IA (LLM, saída JSON) | entende a frase (slots, restrições, orçamento, perfil); dá nota 0–1 e motivo a cada item; o agente de cada loja escolhe o que oferecer a quem e escreve a fala |
| Código determinístico | filtra restrições e orçamento; valida cada oferta e cada fala dos agentes (fallback por template); decide o agrupamento por loja; enumera e pontua combinações; divide a conta em centavos; gera o Pix; segue a ordem do checkout; exige consentimento |
| MCP do iFood | **única fonte** de preço, taxa, prazo, disponibilidade, carrinho e pedido |

Toda chamada de IA tem um caminho determinístico de reserva. Com `LLM_PROVIDER=mock` a demo inteira roda sem chave
e sem internet.

## 2. Componentes

```mermaid
flowchart LR
  subgraph Navegador
    ORG[Organizador<br/>PC]
    CONV[Convidados<br/>celular, sem login]
  end
  subgraph App["App FastAPI :8000 (um processo)"]
    FRONT[Frontend React/Vite<br/>compilado em frontend/dist]
    API[rotas_match.py<br/>API da sala]
    OAUTH[rotas_oauth.py + oauth.py<br/>PKCE S256]
    SALA[(SQLite<br/>salas_match)]
    MOTOR[match/motor.py<br/>interprete · busca · juiz]
    LEILAO[match/leilao.py<br/>agentes por loja<br/>+ validação das falas]
    OTIM[otimizador.py]
    CHK[checkout.py]
    ACERTO[acerto.py + pix.py]
    LLM[llm.py<br/>provedor do .env]
    CLI[ifood_mcp/cliente.py<br/>ClienteIFood + rastro]
    DEMO[demo_server.py<br/>MCP de demonstração]
  end
  IFOOD[(MCP do iFood<br/>consumer-mcp.ifood.com.br/marketplace)]
  ID[(id.ifood.com.br<br/>OAuth)]

  ORG & CONV -->|HTTP, polling 2 s| FRONT --> API
  API --> SALA
  API --> MOTOR --> LEILAO --> OTIM
  MOTOR --> LLM
  LEILAO -.-> LLM
  API --> CHK
  API --> ACERTO
  MOTOR --> CLI
  CHK --> CLI
  CLI -->|IFOOD_MCP_MODO=demo<br/>em processo| DEMO
  CLI -->|IFOOD_MCP_MODO=real<br/>Streamable HTTP + Bearer| IFOOD
  OAUTH --> ID
  CLI -.token.-> OAUTH
```

| Componente | Arquivo | Papel |
|---|---|---|
| Frontend | `frontend/src/` | React 19 + TypeScript (Vite). Rotas por hash: `#/` (início estilo app), `#/s/{id}` (convidado), `#/s/{id}/org` (organizador), `#/conectado` (volta do login). Polling de 2 s em `GET /api/salas/{id}`. Compilado e servido pelo próprio FastAPI (uma URL na demo). Telas do Match: `telas/Leilao.tsx` (disputa) e `telas/Deck.tsx` (o pedido escolhido pelo IBits), com peças em `componentes/leilao/` (seção 5). |
| API da sala | `backend/app/rotas_match.py` | Criar sala, entrar, desejo, rodar, escolher, pagar, enviar, acompanhar. Ações do organizador exigem o header `X-Organizador`. |
| Sala | `backend/app/match/salas.py` | Estado inteiro da sala em JSON numa tabela SQLite própria. Escrita atômica (trava + transação). Chamadas ao MCP ficam fora da trava de gravação e o estado é revalidado depois. |
| Motor | `match/motor.py` | `listAddresses` → interpretar (+ quantidades) → buscar → julgar → leilão → otimizar → fechar o leilão → avisos. `MATCH_LEILAO=off` no `.env` pula o leilão (o otimizador volta a ver todos os candidatos). |
| Intérprete | `match/interprete.py` | Frase → 1 ou mais **slots** ("japonês e um sorvete" = 2 slots). IA com validação; reserva por palavras-chave + chips. **Consulta livre sem IA:** item fora das categorias conhecidas ("coxinha", "feijoada completa") vira consulta pelo próprio texto (até 4 palavras, sem orçamento, restrição nem palavras genéricas; "coxinha ou esfiha" = alternativas do mesmo slot). **Quantidades:** "2 sorvetes"/"duas coxinhas" viram slots iguais (até 3 iguais e 4 slots por pessoa; "pizza 4 queijos" não é quantidade); o que não couber vira aviso, nunca some calado. |
| Busca | `match/busca.py` | Único arquivo que lê campos das tools de descoberta. Preço só da tool; item sem preço é descartado. ≤ 8 candidatos por slot, diversificados por loja. **Leitura robusta de endereço:** acha a lista do `listAddresses` em formatos variados (raiz lista, `addresses`, `data.addresses`…), prefere o último usado/padrão e lê coordenadas com nomes alternativos (`lat`/`lng`/`lon`). |
| Juiz | `match/juiz.py` | Nota 0–1 + motivo curto. Restrição sem tag no item não elimina: o motivo avisa "confirme com a loja". |
| Leilão | `match/leilao.py` + `match/politica_lojas.json` | 1 agente vendedor por loja, validação dura das ofertas e falas, fallback por template, medições (seção 5). |
| Otimizador | `match/otimizador.py` | Código puro, sem I/O nem IA (seção 6). |
| Checkout | `match/checkout.py` | Único arquivo que lê campos de carrinho/pedido. 1 carrinho por loja, envio com consentimento, `trackOrder`. |
| Acerto e Pix | `match/acerto.py`, `match/pix.py` | Partes por pessoa em centavos; Pix copia e cola (BR Code estático). |
| Cliente MCP | `ifood_mcp/cliente.py` | Mesma interface nos dois modos; registra cada chamada no **rastro** (tool, resumo sem dados sensíveis, ms, ok/erro). No modo real lê o `input_schema` de cada tool (1 `list_tools` por sessão) e adapta os argumentos: `latitude`/`longitude` viram `userLocation: {latitude, longitude}` quando a tool declara esse campo, `query` vira o campo de texto declarado (`term`, `q`…) e argumentos não declarados são descartados; o rastro mostra o que foi descartado ("descartados: latitude, longitude"). **Trava de envio:** no modo real, `submitOrder` só é chamado com `IFOOD_MCP_PERMITIR_ENVIO=true` (seção 9). |
| MCP de demonstração | `ifood_mcp/demo_server.py` | Servidor MCP (SDK `mcp` 2.x) com 17 tools de **mesmo nome e campos** da doc oficial; lojas fictícias; todo payload com `"demonstracao": true`. |
| OAuth | `ifood_mcp/oauth.py`, `rotas_oauth.py` | Authorization Code + PKCE S256 + client secret; tokens em arquivo fora do git; renovação automática. |
| Diagnóstico | `ifood_mcp/diagnostico.py` | Roda no PC da equipe: `list_tools` + chamadas de leitura → amostras **sanitizadas** em `docs/mcp-real/`. Nunca chama `submitOrder`. |

## 3. Sequência completa de um Match em grupo

Ordem obrigatória da documentação do MCP: `listAddresses` → `searchOffers` → `getMerchant` → `getItem` →
`createCart` → `addItemToCart` → `getCartDeliveryMethods` → `setCartDelivery` → `listPaymentMethods` →
`setCartPayment` → `getCart` → `submitOrder({cartId, userConsent: true})` → `trackOrder`.

```mermaid
sequenceDiagram
  autonumber
  actor O as Organizador
  actor C as Convidados
  participant API as API da sala
  participant M as Motor (IBits)
  participant L as Agentes das lojas
  participant MCP as MCP do iFood

  O->>API: POST /api/salas (nome, chave Pix)
  API-->>O: sala_id, token do organizador, link/QR
  C->>API: POST /participantes + PUT /desejo (frase, orçamento, chips)
  O->>API: POST /rodar
  API->>M: rodar_match(desejos)
  M->>MCP: listAddresses
  Note over M: IA interpreta cada frase em slots
  loop cada slot
    M->>MCP: searchOffers(query, resultKind=ITEM)
    opt poucos resultados
      M->>MCP: searchOffers(resultKind=MERCHANT) + getMerchant(merchantId)
    end
  end
  Note over M,MCP: getItem ainda não é chamado — o preço vem do searchOffers/getMerchant.
  Note over M: IA dá nota 0–1 e motivo a cada item
  M->>L: itens de cada loja (só os dela) + desejos, em paralelo
  L-->>M: ofertas validadas + falas (ou fallback por template)
  Note over M: otimizador: top 3 combinações (até 3 lojas)
  API-->>O: quadro por pessoa + avisos + rastro
  O->>API: POST /escolher (combinação, junto|separado)
  loop 1 carrinho por loja
    API->>MCP: createCart(merchantId, addressId)
    API->>MCP: addItemToCart(cartId, itemId) para cada item
    API->>MCP: getCartDeliveryMethods(cartId)
    API->>MCP: setCartDelivery(cartId, deliveryMethodId)
    API->>MCP: listPaymentMethods(cartId)
    API->>MCP: setCartPayment(cartId, paymentMethodId)
    API->>MCP: getCart(cartId)
  end
  Note over API: subtotal, taxa, desconto e total vêm do getCart. Separado: partes em centavos + prazo
  C->>API: POST /pagamentos/{pid} (pix | cartão simulado | dinheiro)
  O->>API: POST /pagamentos/{pid}/recebi
  O->>API: POST /enviar {confirmo: true} (só com 100% pago)
  loop cada carrinho, em sequência
    API->>MCP: getCart(cartId) para conferir o total
    alt total mudou
      API-->>O: 409, remonta o carrinho e pede nova confirmação
    else total igual
      API->>MCP: submitOrder(cartId, userConsent=true)
      Note over API,MCP: modo real: travado salvo IFOOD_MCP_PERMITIR_ENVIO=true (409 legível)
    end
  end
  O->>API: POST /pedidos/{orderId}/atualizar
  API->>MCP: trackOrder(orderId)
  API-->>O: status, histórico, retryMessage, pollingStop
```

Cada seta para o MCP vira uma linha do rastro na tela, com o nome da tool da documentação. O resumo do rastro não
mostra latitude, longitude, endereço, e-mail, telefone nem CPF.

## 4. Fluxo do motor

```mermaid
flowchart TD
  A[listAddresses] -->|sem endereço| X1[aviso: cadastre um endereço]
  A --> B[interpretar cada desejo em slots<br/>IA ou regras + quantidades]
  B --> C[buscar candidatos por slot<br/>searchOffers / getMerchant / browseOffers]
  C --> D[juiz: nota 0–1 + motivo<br/>IA ou regras]
  D --> E{melhor nota do slot ≥ 0,5?}
  E -->|não| F[opção aproximada + aviso<br/>bebida nunca substitui comida]
  E -->|sim| G
  F --> G[leilão por loja<br/>MATCH_LEILAO=off pula]
  G --> H[otimizar: top 3, até 3 lojas<br/>só itens ofertados]
  H --> J[fechar leilão: vencedoras,<br/>réplica, fechamento do IBits]
  J --> I
  I[avisos: N lojas = N pedidos, N taxas, N entregas<br/>taxa só aparece no carrinho]
```

Regras de relevância já no código: item com nota < 0,25 sai se houver opção melhor; slot cujo melhor item fica
abaixo de 0,5 vira "Opção aproximada: …" com aviso "Não achei X; a opção mais próxima é Y"; se ninguém tem item
relevante, não há combinação e a API devolve 409 com a pergunta "Quer mudar o pedido?".

## 5. Leilão de agentes por loja

Contratos C11 e C12 de [`docs/planos/etapa-04-leilao-e-entrega.md`](planos/etapa-04-leilao-e-entrega.md).
Decisões 9 e 10 de [`docs/decisions.md`](decisions.md). Código: `match/leilao.py` (chamado pelo `motor.py`).

Ideia: o tema é "Vendendo com Agentes". Cada restaurante tem um **agente vendedor** que só enxerga o próprio
cardápio (vindo do MCP) e disputa o pedido; o **IBits**, agente comprador do grupo, decide entre os lances.

```mermaid
flowchart LR
  subgraph Lojas["Agentes vendedores (em paralelo, até 6 s cada)"]
    A1[Loja A<br/>só itens da A]
    A2[Loja B<br/>só itens da B]
    A3[Loja C<br/>só itens da C]
  end
  D[desejos da turma +<br/>candidatos com nota do juiz] --> A1 & A2 & A3
  A1 & A2 & A3 --> V{validação dura<br/>ofertas e falas}
  V -->|ok| OF[ofertas + fala do LLM<br/>fonte_fala: llm]
  V -->|inválido, erro, timeout ou mock| FB[fallback determinístico<br/>top 2 por nota + fala por template]
  OF & FB --> AG[agrupamento por loja<br/>regra do Match]
  AG --> O[otimizador<br/>só considera itens ofertados]
  O --> R[resultado.leilao: lojas, falas,<br/>vencedoras, medicoes]
```

Quem decide o quê:
- **Agente da loja (LLM):** o que oferecer a quem (até 2 itens por slot, entre os candidatos válidos da própria
  loja), se passa a vez, e **como dizer** (fala e réplica). Saída JSON:
  `{"ofertas": [{"slot_id", "item_id", "motivo"}], "passo": bool, "fala": str, "replica": str}`.
- **Regra do Match (código):** agrupar no mesmo pedido os itens de uma loja que atende 2 ou mais pessoas ("1
  entrega em vez de 2"). A decisão é do código; só o texto da réplica pode vir do agente, se passar na validação.
- **IBits (código):** abertura, fechamento, vencedoras (lojas da 1ª combinação do otimizador) e a frase "a melhor
  da sala", calculada só quando uma loja tem a maior avaliação sem empate.

Como funciona:
- Entram no leilão até 8 lojas que aparecem nos candidatos: a melhor loja de cada slot (ninguém perde a única opção)
  e o resto por melhor nota do juiz. Um agente por loja com algo válido, em paralelo (`asyncio.gather`), com tempo
  máximo de 6 s cada; loja sem item válido passa sem gastar chamada.
- Entrada do agente: só os itens daquela loja por slot (nome, descrição, categoria, tags, preço do MCP, preço "de"
  se houver promoção, nota do juiz), o texto de cada pessoa, ETA e avaliação da loja. Os textos são tratados como
  dados (o prompt manda ignorar instruções dentro deles).
- **Validação das ofertas:** `slot_id` existe; `item_id` é candidato válido daquela loja naquele slot (sem violar
  restrição nem orçamento); no máximo 2 por slot; motivo ≤ 90 caracteres, sem número e honesto (senão fica o motivo
  do juiz). Oferta inválida é descartada.
- **Validação das falas e da réplica** (≤ 200 caracteres). A fala do LLM é trocada pelo template
  (`fonte_fala: "modelo"`) se tiver:
  - **número** (em algarismo ou **por extenso**, como "dezoito e noventa") fora do conjunto permitido: preços
    ofertados, preço "de" da promoção, ETA, avaliação, contagens, afinidade e números do nome/descrição do item;
  - **contagem** que não bate ("fecho 3 sorvetes" só com 3 sorvetes ofertados; "atendo 3 pessoas" só se atende 3);
  - **"todo mundo"/"todos"** sem atender todas as pessoas;
  - **restrição ou alegação de saúde** (vegano, vegetariano, sem lactose, sem glúten, light, fit, orgânico,
    saudável…) que nenhuma **tag** dos itens ofertados confirma (o nome do próprio item conta como dado do MCP);
  - **promessa** (grátis, frete, taxa, cupom, brinde, cashback; "promoção"/"desconto" só se o item tiver preço "de");
  - **superlativo ou comparativo** ("o melhor", "o mais barato"): o agente não vê as outras lojas.
- **Fallback** (`LLM_PROVIDER=mock`, erro, timeout, JSON inválido ou nenhuma oferta válida sem "passo"): top 2 por
  nota do juiz em cada slot da loja; fala por template a partir dos números. Rede de segurança: um slot que tinha
  opção válida nunca fica sem oferta (se todos os agentes o esqueceram, entra o top 2 por template).
- **Garantia:** com `LLM_PROVIDER=mock` o resultado do roteiro da demo não muda (`test_leilao.py`).
- **Roteiro exibido:** abertura do IBits, até 2 passes, até 5 lances (o Patrocinado primeiro, o mais forte por
  último; toda vencedora tem o lance mostrado), a réplica da vencedora que agrupa mais pessoas e o fechamento do
  IBits ("N de M bem atendidos"; com mais de 1 loja, "São N pedidos, e as taxas aparecem no carrinho antes do seu
  ok"). A taxa de entrega **não** aparece nas falas: ela só existe no carrinho.
- **Medições** no bloco `leilao.medicoes`: `ms_total`, `ms_por_loja` e `chamadas_llm` (só conta resposta JSON
  válida). `leilao.llm` só é `true` se ao menos uma resposta do LLM foi usada. Na tela, cada fala diz a origem:
  "agente da loja (IA)" ou "texto conferido".
- **Desligar:** `MATCH_LEILAO=off` no `.env` volta ao motor sem leilão.

**Patrocinado = só visibilidade.** A loja patrocinada tem o lance **mostrado primeiro** entre os lances e o rótulo
"Patrocinado" (em texto). Não garante vaga entre as lojas consultadas no leilão e **nunca** muda nota, filtro ou
escolha do otimizador. No demo, 1 loja patrocinada (`loja-demo-poke`) que não vence: mostra que pagar não compra o
pedido. No modo real nenhuma loja é patrocinada. Configuração em `match/politica_lojas.json`.

No front:
- `telas/Leilao.tsx` — "A disputa pelo seu pedido": falas uma a uma (~0,8 s cada, até 6 na tela; se o roteiro for
  maior, ficam abertura, vencedoras e patrocinada, 1 réplica e o fechamento, sem mudar texto nem número), botão
  **Pular** sempre visível, legenda do Patrocinado, origem de cada fala e o tempo da disputa (`medicoes`). No aparelho
  do organizador a tela não avança sozinha (ele narra); no do convidado avança cerca de 4 s depois do fechamento.
- `telas/Deck.tsx` (o nome ficou da versão com deck) — "O pedido do grupo": só a melhor combinação, num cartão sem gesto:
  afinidade, "N de M bem atendidos", lojas e, por pessoa, item · loja · preço · motivo. "Ajustar com o IBits" logo
  abaixo; "Confirmar pedido" fixo no rodapé leva a "Como pagar?" (`Resultado.tsx`; com 1 pessoa, monta o carrinho
  direto). O `escolher` continua recebendo o índice da combinação, sempre 0. Convidado vê só a própria parte, em leitura.

## 6. Otimizador

Código puro em `match/otimizador.py`. A IA só fornece a nota de cada item e o perfil de cada pessoa.

```
S(C) = média_p(sat_p) + α·mín_p(sat_p) − β·(custo_total / orçamento_ref) − γ·(atraso_max / 60)
       − δ·(lojas − 1) − ε·penal_perecível − penal_slots_fora
```

- `sat_p` = média das notas dos slots escolhidos da pessoa `p` (0 se ela ficou de fora).
- **Justiça:** o termo `α·mín` puxa para cima quem ficou pior; ninguém fica com nota baixa para os outros ganharem.
- **Pesos por perfil** (`barato`, `rapido`, `qualidade`, `equilibrado`); com vários perfis no grupo, média campo a
  campo. Padrão: α 0,5 · β 0,3 · γ 0,2 · δ 0,15 · ε 0,3. "Barato" sobe β para 0,9; "rápido" sobe γ para 0,6.
- **Restrições duras:** item que viola restrição sai; o orçamento da pessoa vale para a **soma** dos slots dela.
- **Slots por pessoa:** o 2º item em diante é opcional (penalidade 0,35 se ficar de fora); o principal paga 1,0.
- **Até 3 lojas** (`MAX_LOJAS = 3` no motor). Se algo ficou de fora, o motor testa 4 lojas e avisa o que entraria
  ("+1 pedido, +1 taxa, +1 entrega"); a escolha continua com o organizador.
- **Perecível:** ε só se um sorvete/açaí de restaurante vier de loja com ETA diferente em mais de 15 min.
- **Enumeração exaustiva** por conjunto de lojas, com ≤ 8 candidatos por slot, poda acima de 50 mil combinações por
  conjunto e 120 mil no total. Desempate determinístico (score, depois custo, depois chave estável).
- Taxa de entrega: a busca não traz taxa; o otimizador roda "sem taxa" (`taxa_conhecida: false`) e a tela avisa que a
  taxa aparece no carrinho, antes do "ok".
- Cada combinação traz os componentes do score e uma explicação curta ("3 lojas · todos com nota ≥ 0,7 · R$ … sem
  taxa · chega em até … min").

## 7. Acerto em centavos e vaquinha

`match/acerto.py` (modo "separado"):
- Cada pessoa paga os próprios itens.
- A **taxa de entrega de uma loja é dividida igualmente entre quem pediu daquela loja**.
- Desconto de uma loja é proporcional ao valor dos itens de cada um nela.
- Tudo em centavos inteiros (`Decimal`, arredondamento meio para cima). A sobra vai pelo método do maior resto, então
  **a soma das partes é exatamente o total dos carrinhos**. Valores de entrada vêm do `getCart`.
- Prazo para todos pagarem: **10 min + 2 min por pessoa acima de 2**.

Formas de pagamento da vaquinha (o app nunca guarda nem movimenta dinheiro):
- **Pix:** `match/pix.py` gera o "copia e cola" estático do Banco Central (EMV): campos 00, 26 (`br.gov.bcb.pix` +
  chave), 52, 53 (986), 54 (valor), 58 (BR), 59 (nome ≤ 25), 60 (cidade ≤ 15), 62 (txid) e 63 (CRC16-CCITT-FALSE). A
  chave é normalizada (CPF/CNPJ só dígitos, telefone +55, e-mail minúsculo, aleatória intacta). O dinheiro vai direto
  para a chave do organizador; ele marca "recebi".
- **Cartão simulado:** só no modo `demo`, com selo. No modo real a API recusa (409).
- **Dinheiro:** o organizador marca "recebi".
- Pendências: o organizador pode cobrir a parte de alguém ou remover os itens dessa pessoa (recalcula carrinho e
  partes).

No modo "junto" não há partes: a sala vai direto para "pronto para enviar".

## 8. Máquina de estados da sala

```mermaid
stateDiagram-v2
  [*] --> coletando: POST /api/salas
  coletando --> coletando: convidados entram e respondem
  coletando --> match_pronto: POST /rodar (com combinação)
  match_pronto --> match_pronto: rodar de novo
  match_pronto --> aguardando_pagamentos: escolher "separado"
  match_pronto --> pronto_para_enviar: escolher "junto"
  aguardando_pagamentos --> pronto_para_enviar: 100% pago
  pronto_para_enviar --> aguardando_pagamentos: valor mudou (ajuste)
  pronto_para_enviar --> enviado: POST /enviar {confirmo: true}
  enviado --> [*]
```

Regras: rodar sem nenhuma combinação devolve 409 e a sala fica em `coletando`. Transição fora da tabela é recusada.
Máximo de 6 participantes (limite do otimizador). Envio parcial (falha no 2º pedido) guarda os já enviados em
`ja_enviados` e nunca os reenvia; tentar de novo continua de onde parou.

## 9. Segurança e confiança

- **Consentimento:** `submitOrder` só é chamado por `checkout.enviar_pedidos(..., consentimento=True)`, que a API
  só passa com `{"confirmo": true}` do organizador (token no header), no estado `pronto_para_enviar` (100% pago no
  modo separado). O servidor de demonstração também recusa `submitOrder` sem `userConsent: true`.
- **Preço só de tool:** preço, taxa, prazo e disponibilidade vêm da resposta do MCP. Antes de cada envio o `getCart`
  é chamado de novo; se o total mudou, nada é enviado, o carrinho é remontado e o organizador confirma de novo.
  Preço de item diferente entre a busca e o carrinho gera aviso.
- **IA sem números:** o LLM interpreta e dá nota; a conta é código. No leilão, fala com número fora do lance
  (algarismo ou por extenso), contagem errada, restrição sem tag, promessa ou superlativo é trocada pelo template
  (seção 5).
- **Tokens e segredos fora do git:** client id/secret só no `.env`; tokens em `backend/.tokens_ifood.json` (ambos no
  `.gitignore`), gravados com troca atômica. Segredos com `repr=False` na configuração. Token, refresh, secret e
  code nunca vão para log, exceção nem resposta HTTP. Os testes zeram as credenciais e isolam o arquivo de tokens.
- **OAuth:** PKCE S256, `state` válido por 10 min, `resource=` (RFC 8707). Erros de login viram 401 com mensagem
  legível.
- **Sanitização:** o diagnóstico mascara nome, e-mail, telefone, CPF, meios de pagamento, endereço textual
  (coordenadas arredondadas) e qualquer campo com "token" antes de gravar; erro sem traceback cru. O rastro omite
  localização e dados pessoais. O `GET` da sala não devolve o token do organizador, a chave Pix inteira (só
  mascarada), o texto do desejo dos outros nem o endereço completo.
- **Trava de envio real:** no modo real, `ClienteIFood.chamar("submitOrder")` recusa a chamada antes de ir à rede,
  salvo `IFOOD_MCP_PERMITIR_ENVIO=true` no `.env` (padrão `false`). A recusa entra no rastro como erro e a API
  devolve **409** legível ("Conta de teste: o envio real está desligado (IFOOD_MCP_PERMITIR_ENVIO). Os carrinhos
  ficaram prontos no iFood."). `GET /api/saude` expõe `envio_real_permitido` (sempre `true` no modo demo) e
  `ip_local` (IP da rede local para o QR dos convidados). No modo demo o envio segue liberado, com
  `userConsent: true` exigido pelo servidor de demonstração.
- **Nunca pagar teste:** o Pix de um pedido da conta de teste não tem reembolso. O diagnóstico nunca chama
  `submitOrder`; a demo real para no `getCart` por causa da trava acima.
- **Selo:** todo dado simulado aparece com o selo DEMONSTRAÇÃO; no modo real, "iFood real · conta de teste".

## 10. Uso correto do MCP

| O que a documentação pede | Como cumprimos |
|---|---|
| `listAddresses` primeiro | O motor chama `listAddresses` antes de qualquer busca; sem endereço, para com aviso. |
| `query` só descritivo; preço/distância em `refinements` | A busca manda o termo descritivo ("sushi", "sorvete"), `resultKind`, `limit` e as coordenadas do endereço; orçamento e restrições são filtrados no nosso código, não na `query`. |
| 1 carrinho = 1 restaurante + 1 endereço | `checkout.py` agrupa a combinação por loja e monta 1 carrinho por loja. |
| `createCart` não é idempotente | Uma trava por sala serializa as ações do organizador que falam com o MCP; a máquina de estados só aceita "escolher" em `match_pronto`, então clique duplo não cria carrinho em dobro. |
| Não confundir `itemId`, `cartItemId`, `cartId` | O checkout guarda o dono de cada `cartItemId` e confere o `getCart` contra o que foi adicionado. |
| Método de entrega e pagamento vêm das tools | Usa o `recommendedMethodId` de `agentHints` se estiver na lista; senão o 1º. Pagamento: o id pedido, senão o 1º crédito, senão o 1º (com aviso). Nunca inventa id. |
| `getCart` para conferir o total | Valores da tela vêm do `getCart`; ele é chamado de novo antes de cada `submitOrder`. |
| `submitOrder` com `userConsent: true` só após confirmação humana | Seção 9. |
| `trackOrder`: seguir `agentHints.retryMessage` e parar em `pollingStop` | `checkout.acompanhar` devolve `proxima_consulta` (retryMessage) e `encerrado` (pollingStop). A consulta é sob demanda (botão "Atualizar"), sem polling automático. |
| Nomes das tools | O demo usa os nomes da doc; o diagnóstico grava o `list_tools` real para confirmar. Diferenças entre doc e real vão para [`docs/feedback-mcp.md`](feedback-mcp.md). |

| (não está na doc) O MCP real exige `userLocation` (objeto) na busca | O cliente lê o `input_schema` de cada tool e converte `latitude`/`longitude` em `userLocation`; argumentos que a tool não declara são descartados e aparecem no rastro. |

Formato real das respostas: só `busca.py` e `checkout.py` leem campos das tools. A leitura de endereço já aceita
formatos variados; o ajuste fino dos demais campos ao MCP real **[pendente]** depende das amostras do diagnóstico
(`docs/mcp-real/`), gravadas no PC da equipe.

## 11. Limites conhecidos e próximos passos

Limites hoje:
- Busca e checkout seguem o formato da documentação (com endereço e `userLocation` já adaptados ao real); o ajuste
  dos demais campos depende das amostras do diagnóstico rodado no PC da equipe. `getItem` (opções e preço
  promocional) ainda não é chamado pelo motor.
- No modo real, `submitOrder` fica travado por padrão (`IFOOD_MCP_PERMITIR_ENVIO=false`): a demo real termina com os
  carrinhos prontos, sem pedido enviado.
- Com `LLM_PROVIDER=mock` as falas das lojas são sempre por template; o tempo do leilão com IA real ainda não foi
  medido (o `medicoes` existe para isso).
- Não há tool de cancelamento no MCP: se o 2º pedido falhar depois do 1º enviado, o 1º fica. O app envia em
  sequência, para no 1º problema e mostra o que saiu.
- O MCP não junta pedidos de lojas diferentes: N lojas = N pedidos, N taxas, N entregas (o app avisa antes).
- Vouchers (`listVouchers`/`setVoucher`), `scheduledTime` e endereço novo (`createAddress`) não são usados.
- Até 6 pessoas por sala; o login OAuth só volta para o `localhost` do PC que roda o app.

Próximos passos:
- Ajustar `busca.py`/`checkout.py` às amostras reais; rodar o Match real até o `getCart` com taxa real.
- Ajustar prompts com IA real e medir o tempo do leilão com `medicoes` (meta ≤ 8 s).
- Depois do hackathon: `getItem` para opções do item, vouchers por loja, `scheduledTime` para alinhar perecíveis,
  memória do grupo e histórico (`getRecommendations`).

## 12. Testes

- **306 testes** no backend (pytest), todos passando em 18/10/2026 (contagem desta versão; `./iniciar.sh --testes`
  mostra o número exato): `cd backend && .venv/bin/python -m pytest -q`. Typecheck do frontend:
  `cd frontend && npm run typecheck`. Tudo junto: `./iniciar.sh --testes` (Windows: `iniciar.ps1 -Testes`).
- O que cobrem (arquivos em `backend/tests/`):
  - `test_ifood_mcp.py`: a sequência obrigatória inteira via cliente MCP; `submitOrder` sem consentimento falha;
    rastro de cada tool.
  - `test_otimizador.py`, `test_acerto_pix.py`: restrição elimina; justiça; perfil muda o vencedor; partes somam o
    total ao centavo; prazo; CRC e campos do Pix; normalização da chave.
  - `test_motor.py`: roteiro da demo com `LLM_PROVIDER=mock` trava o top 1; caminho com LLM falso; opção aproximada;
    "Não achei X" para pedido fora do cardápio.
  - `test_leilao.py`: roteiro mock inalterado com o leilão; agente só enxerga os próprios itens; item de outra loja ou
    slot é rejeitado; mais de 2 por slot é cortado; fala com número inventado, por extenso, contagem errada, promessa,
    restrição sem tag ou superlativo cai no template; preço "de" da promoção pode ser citado; agrupamento vira
    réplica; passe do agente e rede de segurança; agente lento usa o fallback sem derrubar o leilão; `chamadas_llm`
    só conta JSON válido; item cortado conta 0 na afinidade; "a melhor da sala" só sem empate; Patrocinado não muda a
    combinação; `MATCH_LEILAO=off`.
  - `test_interprete.py`: consulta livre sem IA ("coxinha", "feijoada completa"), alternativas, restrição fora da
    consulta, quantidade repete o slot.
  - `test_checkout.py`: sem consentimento não envia; total mudou para; falha no 2º pedido mantém o 1º.
  - `test_salas.py`: fluxo inteiro da API; sem token → 403; enviar antes de 100% pago → 409; envio real desligado →
    409 legível.
  - `test_oauth.py`, `test_diagnostico.py`: PKCE S256, `state` inválido, troca e renovação, token nunca em resposta
    ou log, 401 → renova 1 vez; sanitização com payloads cheios de dados pessoais.
  - `test_endereco_localizacao.py`: endereço em formatos variados e preferência pelo último usado; `userLocation`
    pelo `input_schema`; argumentos descartados no rastro; `submitOrder` real travado por padrão.
  - `test_saude.py`: `/api/saude` com `ip_local` para o QR e `envio_real_permitido`.
