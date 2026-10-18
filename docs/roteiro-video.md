# Roteiro do vídeo — plano B da demo (≤ 2 min)

Usar se a demo ao vivo falhar. Mesmo fluxo da demo (`docs/roteiro-demo.md`), gravado com antecedência.
Voz: **Thales**. Tela: PC (app em 390 px de largura, centralizado) + abas de convidado.

Frase que guia: *"pedido em grupo sem dor: cada um fala o que quer, o IBits monta, divide a conta e pede pelo iFood"*.
Não narrar o Patrocinado. Não dizer que os restaurantes têm agentes no iFood.

## Como gravar (no PC do Thales)
- Gravador: **Win + Alt + R** (Xbox Game Bar) ou OBS. 1080p, 30 fps. Áudio: microfone do fone, ambiente silencioso.
- App: `iniciar.bat`, `IFOOD_MCP_MODO=demo`, `LLM_PROVIDER=mock`, `MATCH_LEILAO=on`. **Recarregar demo** antes.
- Navegador em modo celular (F12 → modo dispositivo, 390 × 780) ou janela estreita; zoom 125%.
- Convidados: 3 abas anônimas no mesmo PC (mais fácil de gravar) ou celulares reais filmados por cima.
- Selo "DEMONSTRAÇÃO · dados simulados" tem que aparecer. Nada de dado pessoal real (use Milan, Zenon, Antonio).
- Gravar a tela sem voz primeiro; gravar a voz depois por cima, lendo as falas abaixo.
- Salvar como `match-demo.mp4` no PC e no celular do Zenon e anotar a pasta em `docs/roteiro-demo.md` (Plano B).

## Cenas

| # | Tempo | O que aparece na tela | Voz do Thales |
|---|---|---|---|
| 1 | 0:00–0:08 | Início do app → **Fazer um match** → **Em grupo** | "Sexta à noite, quatro amigos, quatro vontades. Em vez do grupo do WhatsApp, eu abro o Match." |
| 2 | 0:08–0:15 | Sala criada, QR e link | "Só eu entro no iFood. Meus amigos leem o QR, sem login." |
| 3 | 0:15–0:33 | Aba do convidado: Milan digita "japonês e um sorvete, até R$ 45" e envia; corte rápido para Zenon e Antonio; volta à sala com os 3 "respondeu" | "Cada um fala do seu jeito: japonês e sorvete até 45; hambúrguer e sorvete até 50; algo barato e vegetariano até 25." |
| 4 | 0:33–0:36 | **Rodar Match** | "Agora o IBits monta o pedido." |
| 5 | 0:36–0:46 | Disputa (cortar na edição para ~10 s) até o fechamento do IBits | "Para cada loja, o IBits olha só o cardápio dela, que vem do iFood. A tela mostra isso como uma disputa." |
| 6 | 0:46–0:54 | **Ver as opções** → 1º cartão: Kaigan + Gelato + Brasa, 3 de 3 bem atendidos | "Três de três bem atendidos, e cada item diz o porquê." |
| 7 | 0:54–1:14 | Desce até **Ajustar com o IBits** → digita "troca o sorvete do Milan e do Zenon por açaí" → bolha "Entendi" → disputa curta → cartão "Atualizado" com Açaí do Campus e "Novo" | "E se mudar de ideia? É só falar com o agente. Ele entende quem e o quê, refaz só o que mudou, e o açaí entra. Conversa com o agente; a conta, com o código." |
| 8 | 1:14–1:20 | **Dar match** → "É um Match!" → **Cada um paga a sua parte (vaquinha)** | "Agora a conta: cada um paga a sua parte; a taxa de cada loja só entre quem pediu dela." |
| 9 | 1:20–1:36 | Milan escolhe Pix (QR aparece); Zenon e Antonio, dinheiro; organizador toca **Recebi** nos três; barra chega a 100% | "O Pix vai para a minha chave. O pedido só sai com 100% pago." |
| 10 | 1:36–1:48 | "Confira antes do ok" com os 3 carrinhos → **Deslize para enviar** | "Três lojas, três carrinhos, com a taxa de cada um. Nada sai sem o meu ok." |
| 11 | 1:48–1:56 | **Como a IA chegou aqui** (rastro do MCP) | "Cada linha é uma tool do MCP do iFood. Aqui, com dados de demonstração; o mesmo código fala com o MCP real." |
| 12 | 1:56–2:00 | Cartela final vermelha: "Match — pedido em grupo sem dor" + "Protótipo de hackathon · não afiliado ao iFood" | "Cada um fala, o IBits monta, divide a conta e pede pelo iFood." |

Se a bolha da cena 7 mostrar o nome duas vezes ("Milan: Milan: …", bug de front visto em 18/10 ~03h), regravar
depois da correção ou cortar a bolha na edição e manter o cartão "Atualizado".

## Se der tempo: trecho com o MCP real
> ⚠️ confirmar no PC do Thales (tarefa A1): só gravar se o Match real chegar ao carrinho da conta de teste.

Se chegar, gravar **só** a cena 11 com o selo "iFood real · conta de teste" e o rastro real, e trocar a voz por:
"Isso é o MCP do iFood de verdade, numa conta de teste. Lojas, preço e taxa vêm do iFood. O envio fica travado de
propósito." Nunca gravar `submitOrder` real com pagamento online nem Pix de pedido de teste.

## Checklist
- [ ] Duração ≤ 2:00 · [ ] selo visível · [ ] áudio audível no projetor · [ ] arquivo no PC e no celular do Zenon
- [ ] Ajustar aparece inteiro (frase → "Entendi" → cartão "Atualizado")
- [ ] Assistido uma vez inteiro por alguém que não gravou
