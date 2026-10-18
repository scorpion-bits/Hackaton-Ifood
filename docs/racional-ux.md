# Racional de UX — Match

> Entregável 3 do hackathon SEMCOMP × iFood. Leitura de 3 minutos.
> Protótipo de hackathon, não afiliado ao iFood. Dados da demo são simulados e levam o selo DEMONSTRAÇÃO.

## 1. O problema, em uma frase

**Todo pedido começa com alguém traduzindo a necessidade em produto, loja e carrinho, na mão.** Sozinho já dá
trabalho ("dor de cabeça às 23h: qual remédio, qual farmácia está aberta?"). Em grupo é o caso mais difícil: alguém
vira o "gerente do pedido", pergunta o que cada um quer, acha lojas que agradem todo mundo, cabe no bolso de cada um,
monta o carrinho e depois cobra a vaquinha.

| Quem | O que sente hoje | O que o Match entrega |
|---|---|---|
| **Quem pede sozinho** ("Só eu") | Busca nome por nome, loja por loja | Escreve a necessidade, marca "Comida" ou "Compras" e recebe o carrinho com o motivo |
| **Organizador** (o único com conta no iFood) | Trabalho de logística e de cobrança, sozinho | Cria a sala, toca em "Rodar Match", confere e dá o ok |
| **Convidados** (sem login) | Fila de mensagens, "tanto faz", ficam sem o que queriam | Escrevem uma frase (meta de ≤ 30 s, não medida) e recebem o prato com o motivo |

**Insight central:** ninguém quer ser o gerente do pedido. Então o trabalho chato vai para a IA e para os agentes das
lojas, e as pessoas só fazem o que só elas podem fazer: dizer o que querem e dar o ok final.

## 2. Princípios de design

1. **Dentro do app do iFood.** O Match é uma entrada na home ("Pedir em grupo? Dê um Match"), não um app novo.
   Familiaridade reduz o que a pessoa precisa aprender.
2. **Um só login.** Só o organizador entra no iFood. Convidado entra por link ou QR, sem cadastro.
3. **30 segundos para o convidado (meta, não medida).** Nome, uma frase livre e chips opcionais (sem glúten, sem lactose...). Nada mais.
4. **Escreva do seu jeito.** Frase livre ("japonês e um sorvete, até 45") em vez de formulário. A IA entende preço,
   pressa, restrição e vontade.
5. **Todo número é explicado e vem do iFood.** Preço, taxa e prazo vêm das tools do MCP. A IA nunca escreve um número
   que não veio de uma tool; se tentar, a fala é trocada por um texto pronto.
6. **Nada sai sem o seu ok.** O pedido só é enviado depois de uma confirmação humana explícita.
7. **Honestidade.** O que é simulado tem selo. O que o cardápio não garante (alergia) é dito com todas as letras.
   O que é anúncio tem rótulo.
8. **Sem taxa escondida.** Se o grupo ficar em 3 lojas, a tela diz: 3 pedidos, 3 taxas, 3 entregas.
9. **Facilitar o pedido, não complicar.** Quando a IA teria de adivinhar algo que a pessoa sabe em 1 toque (comida
   ou compras?), a tela pergunta. Quando a regra é óbvia (os itens de uma pessoa na mesma loja), o Match aplica
   sozinho (ver §4).

## 3. Jornadas

### Organizador

| Passo | Objetivo | Decisão de design | Por quê |
|---|---|---|---|
| Home → banner "Dê um Match" | Começar sem procurar | Banner na home e atalho na barra inferior (selo "protótipo"), no visual do app | Quem já usa o iFood acha sem aprender nada |
| "Quem vai comer?" (só eu / em grupo) | Mesmo fluxo para 1 ou N | O individual é o grupo de 1, sem sala | Um fluxo só para aprender e manter |
| Sala com QR e link | Chamar a turma | QR grande no projetor/tela, link para WhatsApp, lista "quem entrou" e "respondeu" | Padrão já conhecido de Uber Eats e DoorDash (ver `design-ifood.md` §4) |
| "Rodar Match" | Sair da espera | Liberado com pelo menos 1 resposta; mensagem "A IA está lendo os desejos e consultando as lojas" | Espera com explicação parece trabalho, não travamento |
| Leilão ao vivo | Ver como a escolha foi feita | Lojas disputam, falam e mostram preço e afinidade; botão **Pular** | Transparência (ver §4) |
| "O pedido do grupo" | Ver e confirmar o pedido que o Match montou | Um cartão só, com a melhor combinação; mudar = "Ajustar com o Match"; "Confirmar pedido" fixo no rodapé | O Match já escolhe: o grupo não precisa comparar opções (ver §4) |
| Junto ou separado | Definir quem paga | Duas opções com a consequência escrita ("na fatura aparecem N cobranças") | A pessoa escolhe sabendo o efeito |
| Vaquinha | Receber de todos | Barra "x de N pagos", contador de prazo, botão "Recebi" para Pix e dinheiro | O organizador vê quem falta sem cobrar no grupo |
| "Confira antes do ok" | Conferir tudo | Subtotal por loja, taxa do carrinho, total geral, aviso de N entregas | O último momento de corrigir |
| "Deslize para enviar" | Dar o consentimento | Gesto deliberado (ou botão "Enviar sem deslizar"), que abre o resumo final com "Confirmo enviar N pedidos ao iFood" | Evita envio por toque acidental |
| Pedidos | Acompanhar | 1 cartão por pedido, status individual e rastro das tools MCP | Cada loja entrega no seu tempo |

### Convidado

| Passo | Objetivo | Decisão de design | Por quê |
|---|---|---|---|
| Lê o QR | Entrar | Abre no navegador, sem app e sem login | Barreira zero |
| "O que você quer?" | Dizer a vontade | Nome + frase livre + orçamento opcional + "É comida ou compras?" (Comida já vem marcado) + chips de 1 toque; "Lembrar de mim neste aparelho" | Meta de caber em 30 s (não medida); a preferência fica no celular dele; a escolha comida/compras vale só para este pedido |
| Espera | Saber o que acontece | "Aguarde o organizador rodar o Match"; pode mudar o desejo | Sem ansiedade, sem refazer |
| Leilão e pedido | Ver o seu prato e o motivo | Mesmo leilão do organizador; no pedido, só a própria parte, em leitura, e a faixa "O organizador ajustou o pedido" quando ele muda algo | Todos veem a mesma coisa; só um decide |
| Sua parte | Pagar a sua parte | Valor por pessoa (itens + rateio da taxa só das lojas dele); Pix, cartão ou dinheiro | Cada um paga só o que consumiu |

### Só eu

| Passo | Objetivo | Decisão de design | Por quê |
|---|---|---|---|
| "Quem vai comer?" → só eu | Pedir para si | Sem convite (QR/link) e sem vaquinha | O individual é o grupo de 1 |
| A frase | Dizer a necessidade | Frase livre + exemplos de 1 toque ("uma pizza e uma coca", "dipirona e protetor solar", "ração de cachorro e um petisco"…); tocar num exemplo de farmácia, mercado ou pet já marca "Compras" | A pessoa sabe o que precisa, não o que buscar ("um remédio para dor de cabeça") |
| "Seu pedido" | Conferir | O mesmo cartão do grupo, com 1 pessoa; "Confirmar pedido" vai direto ao carrinho | Menos passos quando não há ninguém para dividir |

## 4. Por que o leilão, um pedido só e as regras do pedido

### Leilão ao vivo
- **Torna visível o trabalho da IA.** Cada restaurante tem um agente vendedor que só enxerga o próprio cardápio (vindo
  do MCP) e oferece itens a cada pessoa. O Match, agente comprador do grupo, escolhe entre os lances. Sem o leilão,
  isso seria uma caixa-preta de alguns segundos.
- **Confiança por transparência.** Cada lance mostra preço e afinidade. Loja que não atende diz "Passo". O fechamento
  explica quem venceu e avisa que as taxas aparecem no carrinho, antes do ok.
- **Números honestos.** A fala da loja só pode citar números do próprio lance (preço, prazo, avaliação, contagens).
  Fala com número inventado (também por extenso), contagem errada, "todo mundo" sem atender todos, restrição que a
  tag do item não confirma, promessa (frete, cupom…) ou superlativo cai no texto pronto, e a tela mostra a origem
  ("agente da loja (IA)" ou "texto conferido").
- **Patrocinado rotulado e sem poder de compra (desligado hoje).** O mecanismo existe e é testado: a loja patrocinada
  aparece primeiro e com selo "Patrocinado", mas nunca muda nota, filtro ou escolha, e não garante vaga entre as lojas
  consultadas. Hoje nenhuma loja é patrocinada, nem na demo nem no modo real.
- **Respeita o tempo.** Uma fala por vez (~0,8 s), botão **Pular** sempre visível, e o aparelho só vê o leilão uma vez
  por sala.

### Um pedido só (sem deck)
- **O Match já decide.** O otimizador calcula as melhores combinações, mas a tela mostra só a melhor. Uma versão
  anterior tinha um deck para deslizar entre 3 opções e um "É um Match!"; saiu porque devolvia a escolha ao grupo e
  lembrava app de namoro, quando a promessa é justamente tirar esse trabalho.
- **Um cartão com tudo.** Afinidade %, "N de M bem atendidos", lojas e, por pessoa, item · loja · preço · motivo, mais
  os avisos honestos (item que ficou de fora, entregas em horários diferentes). Sem gesto: nada se perde por um toque.
- **Mudar = conversar.** "Ajustar com o Match" fica logo abaixo ("troca o sorvete do Milan por açaí"): o Match roda de
  novo só com a mudança, o cartão ganha "Atualizado" e o item novo, "Novo".
- **Confirmar sempre à mão.** "Confirmar pedido" fica fixo no rodapé e leva a "junto ou separado" (com 1 pessoa, direto
  ao carrinho). Nada vai ao iFood nesse passo.

### Comida ou compras: a pessoa diz, a IA não adivinha
- **O problema.** "Arroz, feijão e bife" pode ser um prato feito ou uma lista de mercado. Num teste no MCP real, a
  pessoa queria uma marmita e recebeu uma compra de supermercado (bug 40). Adivinhar errado faz a pessoa refazer o
  pedido.
- **A decisão.** Uma fileira de escolha única, "É comida ou compras?", com **Comida** já marcado e **Compras (mercado,
  farmácia, pet)**. Sem "Compras", tudo vai para restaurante e refeição vira prato feito ou marmita. Com "Compras",
  cada produto vai para a loja da categoria (farmácia, mercado, pet shop).
- **Por quê.** Facilitar o pedido, não complicar: 1 toque que a pessoa sabe responder custa menos do que um erro que
  ela só descobre no carrinho. A regra fica num arquivo (`regras_pedido.json`), fácil de ajustar.
- **Sem o botão, nada some calado.** Se a pessoa pede algo que só existe em farmácia ou mercado e não marcou
  "Compras", o item sai do pedido com o aviso: "Dipirona para Ana é de farmácia: ligue "Compras" para pedir em
  mercado, farmácia ou pet shop."

### Mesma loja para os itens de cada pessoa
- **A decisão.** Quem pede "um hambúrguer e uma batata" recebe os dois do mesmo restaurante sempre que der. O
  otimizador perde pontos por loja a mais nos itens de uma mesma pessoa, e o 2º item é procurado também dentro das
  lojas do 1º (inclusive as mais baratas).
- **Por quê.** Cada loja a mais é mais uma entrega e mais uma taxa para a mesma pessoa, e itens que chegam em
  horários diferentes. Num teste no MCP real, o Big Mac vinha do McDonald's e a batata de outra loja; agora vêm juntos.

### Loja que não aceita pedido
- **O problema.** No MCP real, lojas que aparecem na busca, e até como abertas, recusam o carrinho. Antes, o Match
  escolhia a mesma loja de novo e o "Confirmar pedido" falhava sempre, sem saída (bug 36).
- **A decisão.** O Match tira a loja e monta a próxima combinação sozinho (até 2 trocas), com o aviso "X não está
  aceitando pedidos pelo iFood agora; montei a próxima opção do Match." A loja fica de fora nos próximos "Rodar" e
  "Ajustar" da sala ("Deixei de fora X: não está aceitando pedidos pelo iFood agora."). Se todas as opções usam essa
  loja, a tela diz para ajustar o pedido ou rodar de novo.
- **Por quê.** A pessoa não precisa entender o erro do iFood (que vinha em inglês, com o id da loja); ela precisa de
  um pedido que feche.

## 5. Confiança e segurança

| Risco | Decisão de design |
|---|---|
| Pedido enviado sem querer | `submitOrder` só com `userConsent: true`, depois de "Deslize para enviar" (ou "Enviar sem deslizar") e de "Confirmo enviar N pedidos ao iFood" no resumo final |
| Total diferente do mostrado | Antes de enviar, o carrinho é lido de novo (`getCart`). Se o total mudou, as partes são recalculadas e o app pede novo ok |
| Confundir demo com pedido real | Selo DEMONSTRAÇÃO fixo no topo; cartão simulado com selo; "Simulado: nenhuma cobrança real" |
| Alergia | O cardápio nem sempre informa. Restrição vira "segundo a descrição" e aparece o aviso "pode não estar informado, confirme com a loja" |
| Dinheiro de terceiros | O app não guarda dinheiro. Pix vai direto para a chave do organizador; a chave fica só no aparelho dele |
| Vaquinha sem fim | Prazo de 10 min + 2 min por pessoa acima de 2, com contador visível. O pedido só sai com 100% pago |
| Falha no meio do envio | O envio para na primeira falha; o pedido que já saiu continua valendo e a tela diz o que fazer |

## 6. Identidade visual

- **Alinhada ao app do iFood**, para o Match parecer uma função do app e não um corpo estranho: vermelho `#EA1D2C`
  (o único hex confirmado em fonte do iFood), fundo claro, cartões brancos com cantos arredondados, home com
  "Entregar em", verticais e cards de loja. Tokens e fontes estão em `docs/design-ifood.md` §5.
- **Sem logo do iFood e sem fonte proprietária.** Usamos Inter, a logo do próprio Match e o nome "Match". Por quê:
  não temos licença para os ativos da marca, e um protótipo não deve se passar pelo app oficial.
- **Fotos e logos só do MCP.** A foto do item e a logo da loja aparecem quando vêm na resposta do MCP e só se o
  endereço for do próprio iFood (`https://static.ifood-static.com.br/`); sem foto, fica o emoji neutro da categoria.
  Rodapé fixo: "Protótipo de hackathon · não afiliado ao iFood".
- O resto da paleta (vermelho escuro, cinzas, verde) é escolha nossa e está marcado como não oficial no `design-ifood.md`.

## 7. Acessibilidade

- **Contraste (calculado pela fórmula da WCAG 2.x com os tokens do `estilo.css`):** texto `#1A1A1A` no branco = 17,4:1;
  texto suave `#6F6F6F` no branco = 5,0:1; aviso `#6B4E00` no fundo `#FFF4D6` = 7,1:1. O vermelho `#EA1D2C` no branco
  dá 4,46:1 (um pouco abaixo de 4,5:1 para texto pequeno) → **regra:** texto pequeno em vermelho usa
  `--marca-escura` `#C8101E` (5,9:1), como já fazem erros, chips ativos e o botão do banner; o vermelho puro fica
  em fundos de botão e texto grande em negrito. Pendente: links (`a`) ainda usam o vermelho puro. O verde `--ok`
  `#2F8A55` dá 4,3:1 → sempre em negrito e junto de palavra ou ícone ("pago", "respondeu"), nunca como única pista.
- **Cor nunca é a única pista.** Status tem palavra ("⏳ aguardando", "pago"); o selo Patrocinado, quando ligado, é
  texto, não só cor.
- **Alvos de toque grandes** nos botões principais e chips; botões ocupam a largura no celular.
- **Alternativa a todo gesto.** O resultado não tem gesto, só botões. Envio: botão "Enviar sem deslizar" além do
  deslize.
- **Movimento reduzido.** Com `prefers-reduced-motion`, o leilão mostra as falas sem animação e o cartão do pedido
  aparece sem transição (as telas do app seguem a mesma regra). **Pular** existe para todos.
- **Leitores de tela.** Chips com `aria-pressed` e grupo rotulado (já no app); "É comida ou compras?" é um grupo de
  escolha única (`radiogroup`, `aria-checked`); linha do tempo do pedido rotulada,
  ícones decorativos com `aria-hidden`; no leilão, o feed de falas é região viva (`aria-live`), como no protótipo.
- **Linguagem simples.** Frases curtas, voz ativa, sem jargão: "Nada é enviado ao iFood ainda: você revisa antes."

## 8. Erros e estados

| Situação | O que a pessoa vê |
|---|---|
| Não achei o que a pessoa pediu | Opção aproximada com o motivo ("É o mais perto do que você pediu agora") em vez de vazio |
| Nenhuma combinação coube | "As restrições e orçamentos deste grupo não encontraram opções" + "Ajuste o orçamento ou o que cada um quer e rode de novo" |
| Loja não atende ninguém | No leilão, a loja diz "Passo"; ela some da escolha sem erro |
| Loja não aceita pedido pelo iFood | "X não está aceitando pedidos pelo iFood agora; montei a próxima opção do Match." Se não há outra opção sem ela: ajustar o pedido ou rodar de novo |
| Item de farmácia/mercado sem "Compras" | O item sai com o aviso "… é de farmácia: ligue "Compras" para pedir em mercado, farmácia ou pet shop."; o resto do pedido segue |
| IA lenta ou fora | Fallback determinístico em poucos segundos; o leilão toca com falas prontas |
| Prazo da vaquinha acabou | "O prazo acabou e Fulano não pagou" → **Organizador cobre** (assume a parte) ou **Tirar os itens dessa pessoa** (recalcula) |
| Total mudou no carrinho | O app para, mostra o novo total e as novas partes e pede novo ok |
| Loja recusou o pedido | "O iFood recusou este pedido" → o Match para, mostra o que saiu e o que não saiu e avisa quem já pagou; o acerto da devolução ainda é feito pelo organizador (no protótipo não há recálculo automático) |
| Carregando | Mensagem do que está acontecendo ("Montando carrinhos…"), nunca tela parada |

## 9. O que mediríamos em produção

Ainda **não temos dados de uso**. Não citamos números de pesquisa. Estas são as métricas e o teste que faríamos.

| Métrica | Pergunta que responde |
|---|---|
| Tempo da sala criada até o pedido enviado | O Match tira mesmo o trabalho do organizador? |
| Tempo do convidado até enviar o desejo | A promessa de 30 s se cumpre? |
| % de salas que viram pedido | Onde o grupo desiste (espera, resultado, vaquinha, envio)? |
| % de grupos que confirmam sem usar o "Ajustar" | A primeira combinação é boa o bastante? |
| % de "Pular" no leilão | O leilão ajuda ou atrapalha? |
| % de vaquinhas que fecham no prazo, e quantas vezes o organizador cobre | O prazo e a cobrança funcionam? |
| NPS do organizador e do convidado, em separado | Os dois lados saem satisfeitos? |

**Teste com usuários (proposta):**
1. Grupos reais de amigos (3 a 4 pessoas), cada um no próprio celular, com a tarefa "peçam o jantar de hoje".
2. Comparar com o jeito atual (grupo de WhatsApp + um app de entrega): tempo total, mensagens trocadas e quem ficou
   satisfeito.
3. Observar em silêncio e perguntar no fim: "Em que momento você ficou em dúvida?" e "Você confiou no total?".
4. Variantes A/B: leilão ligado × direto ao pedido; um pedido só × as 3 melhores combinações para escolher.

No evento, a equipe aplica um formulário curto com participantes; o resultado, se coletado, fica em
`docs/pesquisa-usuarios.md`, com o número de respostas.
