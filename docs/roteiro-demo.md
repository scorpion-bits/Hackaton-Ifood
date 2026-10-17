# Roteiro da demo ao vivo — Match (2 minutos)

Slide 4 do pitch ("Demo ao vivo"). Apresentador: **Thales** (organizador, PC no projetor).
Convidados nos celulares: **Milan**, **Zenon**, **Antonio**. Tudo em modo demonstração (selo visível).

Regra: ninguém lê número de cabeça. Valores, lojas e taxas são os que aparecem na tela.
Os campos `[preencher]` restantes são completados depois do primeiro ensaio com o build final. As frases, orçamentos,
lojas e preços do quadro abaixo vêm da execução real do motor com `LLM_PROVIDER=mock` e o MCP de demonstração
(`backend/tests/test_motor.py` trava esse resultado).

## Falas e cliques

| Tempo | Quem | Faz (clique) | Fala |
|---|---|---|---|
| 0:00–0:10 | Thales | Tela Início (estilo app) → banner "Pedir em grupo? Dê um Match" | "Sexta à noite, quatro amigos, cada um quer uma coisa. Em vez de discutir no WhatsApp, eu abro o Match." |
| 0:10–0:20 | Thales | Cria a sala → QR e link aparecem no projetor | "Eu sou o único que entra no iFood. Os outros só leem o QR, sem login." |
| 0:20–0:45 | Milan, Zenon, Antonio | Leem o QR, digitam nome e a frase, tocam em Enviar | Milan (em voz alta): "Japonês e um sorvete, até 45." · Zenon: "Hambúrguer e sorvete, até 50." · Antonio: "Algo barato e vegetariano, até 25." |
| 0:45–0:50 | Thales | Aponta a lista: os 3 com "respondeu" | "Todo mundo respondeu em segundos. Agora: Rodar Match." |
| 0:50–1:10 | Thales | **Rodar Match** → quadro por pessoa | **Momento uau:** "Cada um tem o seu prato, dentro do seu orçamento, com o motivo. Repare: o sorvete do Milan e o do Zenon vêm da **mesma sorveteria**, então é um pedido só para os dois. A IA entendeu 'barato e vegetariano'; o preço veio do iFood, não da IA. São 3 lojas, e o Match avisa: 3 pedidos, 3 taxas, 3 entregas." Resultado esperado (1ª combinação, ver quadro abaixo) |
| 1:10–1:20 | Thales | Escolhe a 1ª combinação → **Separado** | "Cada um paga a sua parte. A taxa de cada loja é dividida só entre quem pediu dela, e as partes fecham o total no centavo." |
| 1:20–1:40 | Milan, Zenon, Antonio, Thales | Milan: **Pix** (QR aparece). Zenon: **cartão** (selo demonstração). Antonio: **dinheiro**. Thales marca **Recebi** no Pix e no dinheiro | Thales: "O Pix vai para a minha chave. O pedido só sai quando 100% estiver pago, e o contador mostra o prazo." |
| 1:40–1:50 | Thales | **Enviar pedidos** → confirma | "Nada sai sem o meu ok. O app confere o total de novo antes de enviar." |
| 1:50–2:00 | Thales | Cartões de pedido com status; abre o **rastro** do MCP | **Fechamento:** "Três pedidos, um grupo, ninguém virou gerente do pedido. E cada linha aqui embaixo é uma tool do MCP do iFood, com os mesmos nomes da documentação." (Se a demo estiver no MCP real, dizer: "é uma chamada real ao MCP do iFood". No modo demonstração, **não** dizer "real".) |

Se sobrar tempo: tocar em "Atualizar" num cartão de pedido para o status avançar.

## Resultado esperado do quadro (1ª combinação, modo demonstração)

| Pessoa (orçamento) | Item | Loja | Preço | Nota |
|---|---|---|---|---|
| Milan (até R$ 45) | Guioza de legumes (6 un.) | Kaigan Sushi (demo) | R$ 22,90 | 0,73 |
| Milan | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 | 0,90 |
| Zenon (até R$ 50) | Smash burger clássico | Brasa Burger (demo) | R$ 29,90 | 0,90 |
| Zenon | Sundae de morango | Gelato Bom Clima (demo) | R$ 18,90 | 0,90 |
| Antonio (até R$ 25, chip vegetariano) | Sunomono | Kaigan Sushi (demo) | R$ 12,90 | 0,75 |

- Totais por pessoa (itens): Milan R$ 41,80 · Zenon R$ 48,80 · Antonio R$ 12,90 · **R$ 103,50 sem taxa**.
- 3 lojas: Kaigan Sushi, Brasa Burger e Gelato Bom Clima. Os dois sorvetes são da mesma sorveteria (1 pedido para os
  dois); Milan e Antonio dividem o pedido do Kaigan Sushi (a taxa dele é dividida entre os dois).
- Avisos na tela: "3 lojas = 3 pedidos, 3 taxas de entrega e 3 entregas (podem chegar em horários diferentes)" e
  "A taxa de entrega de cada loja só aparece no carrinho, antes de você confirmar". Taxas de demonstração (fictícias):
  Kaigan R$ 7,99 · Brasa R$ 5,99 · Gelato R$ 4,99; o valor que vale é o que o carrinho mostrar.
- A 2ª combinação empata no score e troca só o item do Antonio (Copinho de sorvete 1 bola, R$ 12,90); a 3ª troca o
  sorvete do Zenon pelo copinho (R$ 12,90). O empate da 1ª e 2ª é resolvido sempre na mesma ordem (determinístico).
- Se o quadro sair diferente no ensaio (ex.: outro provedor de LLM), usar `LLM_PROVIDER=mock`, que é determinístico.

## Quem fala o quê (resumo)
- **Thales:** narra tudo e clica no PC.
- **Milan, Zenon, Antonio:** só leem a própria frase em voz alta e tocam no celular. Celulares já com a câmera
  aberta antes do QR aparecer.

## Se algo falhar

| Falha | O que fazer (sem parar de falar) |
|---|---|
| QR não abre no celular | Thales lê o link curto em voz alta; ou o convidado abre o link já salvo nos favoritos |
| Celular sem rede | Thales responde por ele numa aba anônima no PC ("o Antonio está sem sinal, eu faço por ele") |
| Rodar Match demora > 10 s | "A IA está consultando o cardápio de cada loja." Se passar de 20 s: plano B |
| Erro na tela ou app cai | **Recarregar demo** (reset) e ir direto para o plano B |
| Pix não gera QR | Trocar a forma de pagamento desse convidado para dinheiro e seguir |
| Projetor/PC trava | Abrir o vídeo no celular de Zenon e narrar por cima |

## Plano B
1. **Modo demonstração offline:** o app roda com o MCP de demonstração e sem chave de LLM (`IFOOD_MCP_MODO=demo`,
   `LLM_PROVIDER=mock`). Não precisa de internet. É o modo padrão da demo.
2. **Vídeo gravado** do mesmo roteiro: `[preencher: caminho do arquivo no PC e no celular do Zenon]`. Thales narra
   por cima com as mesmas falas.

## Checklist pré-demo (fazer 15 min antes)
- [ ] Internet do local funcionando (e hotspot do celular como reserva).
- [ ] `.env` no PC do Thales: `IFOOD_MCP_MODO=demo`, `LLM_PROVIDER` definido (ou `mock`), chave Pix do organizador
      à mão (digitada na tela, nunca no git).
- [ ] App iniciado (`iniciar.bat`) e aberto em `http://localhost:8000`.
- [ ] **Recarregar demo** (reset) clicado: sem salas nem pedidos antigos.
- [ ] Celulares na **mesma rede** do PC; link testado num celular (endereço IP do PC, não `localhost`):
      `[preencher: http://IP-DO-PC:8000]`.
- [ ] Firewall do Windows liberando a porta 8000 na rede local.
- [ ] Zoom do navegador em 125–150% para o projetor; janela em tela cheia; notificações desligadas.
- [ ] Celulares com brilho alto, sem modo economia, câmera pronta para o QR.
- [ ] Vídeo do plano B aberto em outra aba/celular.
- [ ] Ensaio cronometrado feito pelo menos 2 vezes; tempo real: `[preencher]`.
