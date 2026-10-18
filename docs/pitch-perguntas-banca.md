# Perguntas difíceis da banca — respostas preparadas

Só para o Q&A do pitch. Resposta em até 20 s; se não souber, dizer "não medimos" e o que faríamos.
Frase que guia: *"pedido em grupo sem dor: cada um fala o que quer, o IBits monta, divide a conta e pede pelo iFood"*.
Nunca dizer que os restaurantes têm agentes no iFood. Patrocinado: só se perguntarem, resposta curta (fim do arquivo).

## As duas que mais importam

### "É um agente de verdade?"
- Sim, e dá para ver na demo: o **Ajustar com o IBits**. Depois do resultado, o organizador escreve "troca o sorvete do
  Milan e do Zenon por açaí"; o IBits entende **quem** e **o quê**, muda só o pedido dessas pessoas e refaz o Match
  pelo MCP. Se não entende ("bom dia"), responde "Não entendi quem ou o quê" com um exemplo, em vez de chutar.
- É o que o regulamento pede: **agente conversacional + ferramentas determinísticas**. A conversa e a leitura das
  frases ficam com o agente; busca no MCP, combinação, preço, divisão da conta e carrinho são código.
- Nunca inventa pessoa nem número: se o LLM devolver alguém que não está na sala ou um valor que não está na frase, a
  resposta é descartada inteira (`backend/app/match/ajuste.py`).
> ⚠️ confirmar no PC do Thales: com chave de IA no `.env`, quem entende a frase é o LLM (saída JSON validada); sem
> chave, é o intérprete determinístico. Dizer qual estava ligado na demo.

### "O pedido é real?"
- O que já verificamos no MCP real: agente **IBits aprovado** no portal, **conta de teste**, login **OAuth** e
  `list_tools` com **23 tools**.
- O caminho é o do pedido real: busca → `createCart`/`addItemToCart` → entrega e pagamento → `getCart` com a taxa e o
  total do iFood → `submitOrder` só com o ok na tela.
- O envio fica **travado de propósito**: só sai com `IFOOD_MCP_PERMITIR_ENVIO=true`. No real, o app **nunca escolhe
  Pix nem cartão online**, só forma sem cobrança no app (ex.: dinheiro na entrega); sem ela, para no carrinho. Pedido
  de teste não vai ao restaurante, mas um Pix pago não tem reembolso.
> ⚠️ confirmar no PC do Thales (tarefa A1): se o Match real chegou ao carrinho com taxa do `getCart` (e se algum
> pedido foi enviado na conta de teste). Até confirmar, dizer: "rodamos a demo no modo demonstração; o mesmo código
> fala com o MCP real, e o login e a lista de tools já foram verificados no real".

## Produto

### "O iFood já tem o Ailo. Qual a diferença?"
- O Ailo fecha o pedido de **1 pessoa** ([iFood, 10/10/2025](https://institucional.ifood.com.br/inovacao/ailo-assistente-de-ia-pedidos/)).
  O Match monta o pedido de **N pessoas**, com orçamentos e restrições diferentes, de até 3 lojas, e divide a conta.
  É uma capacidade que o Ailo poderia usar. Para 1 pessoa, o Match também tem o "Só eu".

### "A Rappi já faz pedido em grupo."
- Faz, e está no nosso comparativo ([Supervarejo, 11/2023](https://www.supervarejo.com.br/varejo/rappi-lanca-recurso-que-permite-fazer-pedidos-em-grupo)).
  Lá cada pessoa escolhe à mão, numa loja. No Match, o **agente monta** o pedido do grupo a partir de frases, junta
  **até 3 lojas**, você **ajusta conversando**, e a vaquinha trava o envio até 100% pago.

### "Por que não é só um chatbot?"
- Um chatbot conversa com 1 pessoa. O Match junta **N pessoas** e escolhe a combinação de itens e lojas que atende
  todo mundo (ninguém fica sem opção boa), com a conta pronta. A decisão numérica é código.

### "O que é essa disputa entre lojas? Os restaurantes têm agentes?"
- Não. A disputa é a **forma visual** de mostrar como o IBits avalia cada loja: para cada loja, um avaliador que só lê
  o cardápio **daquela** loja, vindo do MCP, e diz o que ela atende. É simulado por nós; as lojas não rodam nada nem
  sabem do Match. Por isso as lojas da demo são fictícias e o rótulo de cada fala diz se é texto conferido.

### "E se o grupo quiser pagar na entrega?"
- No modo real o app **prefere** pagamento sem cobrança no app (dinheiro / na entrega), quando a conta oferece.
- Com 2 ou 3 lojas são **2 ou 3 entregadores e cobranças**: a tela já separa o total por loja, então quem recebe sabe
  quanto pagar a cada um.

### "Por que não junta tudo numa entrega só, como a Uber Eats?"
- No MCP, 1 carrinho = 1 loja. O Match mostra o custo real de dividir (N pedidos, N taxas) e avisa antes. Se o iFood
  abrir várias lojas numa entrega, o otimizador já pondera o número de lojas. Está no nosso feedback do MCP.

### "Escala para 15 pessoas?"
- Hoje não: até **6 pessoas por sala** (limite do otimizador, que testa as combinações). Para 15+: poda por loja e
  votação no deck. Dizemos o limite, não escondemos.

## Confiança

### "E se o LLM errar o preço?"
- O LLM nunca dá preço. Preço, taxa, prazo e disponibilidade só vêm das tools do MCP (`searchOffers`, `getMerchant`,
  `getCart`). Fala com número que não veio de lá é trocada por texto conferido. Antes de enviar, `getCart` de novo; se o
  total mudou, para e pede novo ok.

### "Como evitam pedido sem consentimento?"
- `submitOrder` só com `userConsent: true` depois que o organizador confirma na tela ("Deslize para enviar"), vendo
  cada carrinho, loja e total. Na vaquinha, só com 100% pago. O rastro mostra cada tool chamada.

### "E se um pagamento falhar ou alguém não pagar?"
- O pedido não sai enquanto não estiver 100% pago. Prazo: 10 min + 2 min por pessoa acima de 2. Acabou o prazo: o
  organizador cobre a parte, tira os itens dessa pessoa (as partes são recalculadas) ou cancela.
- Se um pedido falhar **depois** de outro ter saído: o app para e mostra qual loja falhou. O MCP não tem cancelamento;
  por isso validamos todos os carrinhos antes do 1º envio.

### "O que é esse 82% de afinidade?"
- Média, por pessoa, da nota que a IA deu para quanto cada prato combina com o que a pessoa escreveu (0 a 100). A
  legenda está no cartão. **Não é satisfação medida**; serve para comparar as opções entre si.
- "Bem atendidos" = pessoas com nota média ≥ 0,5.

### "E alergia?"
- A restrição só é afirmada se o item tem a etiqueta no MCP; senão aparece "segundo a descrição" e "confirme com a
  loja". Para alergia grave: confirme com a loja. Não prometemos segurança alimentar.

### "E a privacidade (LGPD) do convidado sem login?"
- O convidado informa só um nome (pode ser apelido), a frase e o orçamento. Nada de CPF, e-mail ou telefone.
  A conta do iFood e o pagamento ao iFood são só do organizador. A chave Pix fica no banco local, nunca no git.

## Engenharia

### "É agente ou workflow fixo?"
- As duas coisas, de propósito. A **ordem das tools** e **tudo que envolve dinheiro** ficam em código: é o que a doc
  do MCP pede (endereço antes da busca, `getCart` antes de enviar, consentimento) e é o que dá confiança.
- O agente decide o que não dá para fixar: o que buscar a partir da frase de cada pessoa, quanto cada prato combina
  com ela, e o que mudar quando o organizador pede um ajuste. Juntar itens da mesma loja num pedido é regra nossa.

### "Quanto custa o LLM? E o rate limit?"
- Até 8 lojas avaliadas, **uma chamada por loja, em paralelo**, com tempo máximo de ~6 s cada; mais o intérprete e o
  juiz. A conta, a escolha e o carrinho são código, sem LLM.
- Custo por Match com IA real: **não medimos**.
- Erro 429, timeout ou resposta inválida → **fallback determinístico**. A demo inteira roda sem chave nenhuma.

### "E a latência no MCP real?"
- Cada chamada aparece no rastro ("Como a IA chegou aqui"). Não medimos o fluxo inteiro no real; o rastro mostra cada chamada.
> ⚠️ confirmar no PC do Thales: se houver medição no real, trocar pela medida (com a data).

### "Por que a doc diz 24 tools e vocês falam em 23?"
- Porque o `list_tools` real devolveu 23 (falta `listItemTaxonomy`). Está no feedback do MCP, com o `userLocation`
  que a doc não cita e é obrigatório no `searchOffers`.

## Só se perguntarem: "O que é esse 'Patrocinado' na tela?"
- Resposta curta e honesta: "É um experimento do modo demonstração: uma loja fictícia marcada como patrocinada só
  aparece antes na animação, com rótulo. Não muda nota, filtro nem escolha. Não é o foco do produto e não existe no
  modo real." Não aprofundar modelo de negócio.
