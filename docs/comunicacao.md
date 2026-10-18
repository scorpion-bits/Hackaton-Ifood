# Comunicação entre os agentes (Milan · Thales · Zenon)

> Criado pelo agente do Zenon em 18/10 01h25, a pedido do Zenon. **Agente do Milan e agente do Thales: leiam este
> arquivo no começo de cada rodada** (`git pull origin ccr-4c429dbb-lp7btg`). Ele não substitui o `docs/quadro.md`
> nem o `docs/testes/para-o-thales.md`: é só o lugar de **pedido e resposta** entre pessoas/agentes.

## Onde cada coisa vai
| Canal | Para quê | Quem escreve |
|---|---|---|
| `docs/quadro.md` | quem está fazendo o quê (reserva de arquivos, status) | cada um na sua linha |
| `docs/testes/para-o-thales.md` | fila de pedidos que o agente do Thales executa no PC dele | Milan/Zenon acrescentam P novo |
| `docs/testes/bugs.md` | bug achado em teste | agente do Thales cria; quem corrige muda o status |
| **este arquivo** | pergunta, pedido de decisão e resposta entre Milan, Thales e Zenon | qualquer um; **só acrescenta no fim** |

## Regras
1. Hora sempre do relógio: `TZ=America/Sao_Paulo date +%d/%m\ %Hh%M`.
2. Uma mensagem por linha da tabela, curta. Detalhe longo → link para o arquivo.
3. Não editar a mensagem de outra pessoa; responder na coluna **Resposta** (com hora e nome) ou numa linha nova.
4. Quem decide produto, escopo e integração: **Milan** (`docs/AVISO-EQUIPE.md`). Pitch e apresentação: **Thales**.
   O Zenon (remoto) executa o que for pedido aqui, no quadro ou no plano da etapa 05 — não cria tarefa nova sozinho.
5. Status: ⬜ aguardando resposta · 💬 respondido · ✅ resolvido · ❌ recusado.

## Modelo de mensagem
```
| Z/M/T + nº | dd/mm hhHmm | De → Para | Assunto: o que é, por que importa, o que você pede (decisão/tarefa) | ⬜ | |
```

## Mensagens
| ID | Hora | De → Para | Mensagem | Status | Resposta |
|---|---|---|---|---|---|
| Z1 | 18/10 01h25 | Zenon → Milan | **O resultado do Match está parecendo um Tinder** (deslizar para os lados, "Ver próxima", "Dar match", "É um Match!"). Não é o modelo do produto: o IBits **já escolhe sozinho** o pedido do grupo com base no que cada um falou. Proposta mínima (só front, `Deck.tsx`/`Resultado.tsx`): mostrar direto a melhor combinação, **sem rejeitar nem deslizar**; mudar = "Ajustar com o IBits" (que já existe); botão "Confirmar pedido" leva ao pagamento. Erro meu: veio de um protótipo que eu transformei em tela na etapa 04. **Peço a sua decisão** (o deck está congelado no aviso): posso fazer essa mudança? Não mexo antes da resposta. | ⬜ | |
| Z2 | 18/10 01h25 | Zenon → Milan · Thales | **Pitch é do Thales.** O Zenon não mexe mais em `pitch/*`, `docs/roteiro-demo.md`, `docs/roteiro-video.md` nem `docs/pitch-perguntas-banca.md`. Milan: no plano da etapa 05 (teu arquivo), a B3 e a parte de pitch da B8 podem passar para o Thales. O branch `zenon/b7-video` (roteiros) só entra se o Thales quiser; o vídeo `match-demo-rascunho.mp4` já foi entregue ao Zenon para repassar. | ⬜ | |
| Z3 | 18/10 01h25 | Zenon → Milan | **`docs/plano-nota-maxima.md` são só sugestões**, não tarefas. Nada dali vale sem você ou o Thales colocarem no plano/fila. Desculpa pelo ruído. Pendente de integração do Zenon: `zenon/b4-bugs-8-11` (bugs 8 e 11 do `bugs.md`, já ✅). | ⬜ | |
| Z4 | 18/10 01h25 | Zenon → Milan | **O que o Zenon (remoto) pode fazer agora**, se você quiser: bugs de front do `bugs.md` (hoje nenhum aberto); a mudança do Z1 se aprovada; regerar o PDF dos entregáveis perto das 12h30. Me diga aqui o que priorizar. | ⬜ | |
| Z5 | 18/10 01h31 | Zenon → Milan · Thales | **D1 modo palco** (no teu "Próximo passo" da etapa 05, prazo 03h): esqueci dele no Z4. Ele saiu de uma sugestão minha (`plano-nota-maxima`) e é ferramenta de **apresentação** (área do Thales). Depois do "nada novo", **não faço** a menos que vocês dois confirmem aqui até ~02h; sem resposta, fica fora e pode riscar do plano. Thales: este arquivo ainda não está na tua branch (`git pull origin ccr-4c429dbb-lp7btg`). | ⬜ | |
