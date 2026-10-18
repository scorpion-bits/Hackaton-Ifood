# Roteiro do vídeo — plano B da demo (≤ 2 min)

Usar se a demo ao vivo falhar. Mesmo roteiro da demo (`docs/roteiro-demo.md`), gravado com antecedência.
Voz: **Thales**. Tela: PC (app em 390 px de largura, centralizado) + 1 celular para o convidado.

## Como gravar (no PC do Thales)
- Gravador: **Win + Alt + R** (Xbox Game Bar) ou OBS. 1080p, 30 fps. Áudio: microfone do fone, ambiente silencioso.
- App: `iniciar.bat`, `IFOOD_MCP_MODO=demo`, `LLM_PROVIDER=mock`, `MATCH_LEILAO=on`. **Recarregar demo** antes.
- Navegador em modo celular (F12 → modo dispositivo, 390 × 780) ou janela estreita; zoom 125%.
- Convidados: 3 abas anônimas no mesmo PC (mais fácil de gravar) ou celulares reais filmados por cima.
- Selo DEMONSTRAÇÃO tem que aparecer na tela. Nada de dado pessoal real (use os nomes Milan, Zenon, Antonio).
- Gravar a tela sem voz primeiro; gravar a voz depois por cima, lendo as falas abaixo (fica mais limpo).
- Salvar como `match-demo.mp4` no PC e no celular do Zenon. Caminho final: `[preencher]`.

## Cenas

| # | Tempo | O que aparece na tela | Voz do Thales |
|---|---|---|---|
| 1 | 0:00–0:08 | Início do app → banner "Pedir em grupo? Dê um Match" | "Sexta à noite, quatro amigos, quatro vontades. Em vez do grupo do WhatsApp, eu abro o Match." |
| 2 | 0:08–0:18 | Sala criada, QR e link | "Só eu entro no iFood. Meus amigos leem o QR, sem login." |
| 3 | 0:18–0:38 | Aba do convidado: Milan digita "japonês e um sorvete, até R$ 45" e envia; corte rápido para Zenon e Antonio; volta à sala com os 3 "respondeu" | "Cada um escreve do seu jeito: japonês e sorvete até 45; hambúrguer e sorvete até 50; algo barato e vegetariano até 25." |
| 4 | 0:38–0:41 | Clique em **Rodar Match** | "Agora as lojas disputam o nosso pedido." |
| 5 | 0:41–0:53 | Disputa inteira (sem Pular): Poke Verde Patrocinado fala primeiro, demais lances, réplica da sorveteria, fechamento | "Cada restaurante tem um agente vendedor que só vê o próprio cardápio. O Poke Verde é Patrocinado: pagou para falar primeiro… e atende só 1 de 3. A sorveteria decide juntar os 2 sorvetes num pedido só. O IBits, agente comprador da turma, fecha: 3 de 3 bem atendidos." |
| 6 | 0:53–1:03 | **Ver as opções** → deck → 1 deslize → "É um Match!" | "Um gesto, e é um Match." |
| 7 | 1:03–1:10 | **Separado** | "Cada um paga a sua parte; a taxa de cada loja é dividida só entre quem pediu dela." |
| 8 | 1:10–1:30 | Milan escolhe Pix (QR aparece); Zenon e Antonio, dinheiro; organizador toca **Recebi** nos três; barra chega a 100% | "O Pix vai direto para a minha chave. O pedido só sai com 100% pago." |
| 9 | 1:30–1:45 | "Confira antes do ok" com os 3 carrinhos → **Deslize para enviar** | "Preço e taxa vêm do iFood, não da IA. 3 lojas, 3 pedidos, avisado antes. Nada sai sem o meu ok." |
| 10 | 1:45–1:55 | Rastro do MCP aberto (lista de tools com ms) | "Cada linha é uma tool do MCP do iFood. Aqui, com dados de demonstração; o mesmo código fala com o MCP real." |
| 11 | 1:55–2:00 | Cartela final vermelha: "Match — ninguém vira gerente do pedido" + "Protótipo de hackathon · não afiliado ao iFood" | "Ninguém virou gerente do pedido." |

## Se der tempo: versão com o MCP real
Se o Match real rodar até o `getCart` no PC (conta de teste), gravar **só** a cena 10 com o selo
"iFood real · conta de teste" e o rastro real (com ms), e trocar a voz por: "Isso é uma chamada real ao MCP do iFood,
em conta de teste. O envio fica travado de propósito." Nunca gravar `submitOrder` real nem Pix de pedido de teste.

## Checklist
- [ ] Duração ≤ 2:00 · [ ] selo visível · [ ] áudio audível no projetor · [ ] arquivo no PC e no celular do Zenon
- [ ] Assistido uma vez inteiro por alguém que não gravou
