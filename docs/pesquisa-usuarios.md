# Pesquisa rápida com usuários: pedido de delivery em grupo (SEMCOMP, 17/10/2026)

**Por que:** não existe dado público brasileiro sobre pedido em grupo (ver `docs/pesquisa-mercado.md` §4). Esta
pesquisa é a nossa evidência do problema. Meta: **~30 respostas** hoje no evento. Tempo por pessoa: **~1 minuto**.

👥 **Quem faz:** Zenon e Antonio (montar o Google Forms, gerar QR, abordar pessoas). Encerrar coleta às **09h de 18/10**
para dar tempo de tabular antes do congelamento (10h30).

## Como montar no Google Forms (5 min)
1. forms.google.com → "Em branco" → título: **"Pedir comida em grupo: 1 minuto"**.
2. Configurações → **desligar** "Coletar endereços de e-mail" e "Limitar a 1 resposta" (não exige login).
3. Colar a abertura (abaixo) na descrição. Criar as 6 perguntas (todas obrigatórias, exceto a 6b).
4. "Enviar" → ícone de link → encurtar → gerar QR (ex.: qr-code-generator) e deixar no celular/notebook.
5. Aba "Respostas" → ícone do Planilhas → cria a planilha para tabular.

## Texto de abertura (consentimento)
> Somos uma equipe do hackathon SEMCOMP × iFood. Queremos entender como as pessoas pedem comida **em grupo**.
> São 6 perguntas, leva 1 minuto. **É anônimo**: não pedimos nome, e-mail ou telefone. As respostas serão usadas
> só em números agregados na apresentação do hackathon. Ao continuar, você concorda em participar. Pode parar a
> qualquer momento.

## Perguntas (≤ 6)

**1. Quando foi a última vez que você pediu delivery junto com outras pessoas (amigos, família, república, trabalho)?**
(múltipla escolha) Na última semana · No último mês · Nos últimos 6 meses · Há mais de 6 meses · Nunca
→ *Se "Nunca": ir para a pergunta 6 (configurar "Ir para a seção com base na resposta").*

**2. Nessa última vez, quanto tempo o grupo levou para decidir o que pedir?**
(múltipla escolha) Menos de 5 min · 5 a 15 min · 15 a 30 min · Mais de 30 min · Não lembro

**3. O que aconteceu? (marque tudo que vale)**
(caixas de seleção) Pedimos tudo juntos em um pedido · Cada um pediu separado no próprio app · Alguém desistiu de
pedir · Alguém ficou com algo que não queria · Desistimos de pedir / fomos comer em outro lugar · Correu tudo bem

**4. Alguém queria comida de um restaurante diferente do resto do grupo?**
(múltipla escolha) Sim, e pedimos de mais de um lugar · Sim, mas alguém cedeu · Não · Não lembro

**5. Como vocês dividiram a conta?**
(múltipla escolha) Uma pessoa pagou e os outros fizeram Pix depois · Dividimos igual · Cada um pagou o que pediu ·
Uma pessoa pagou tudo e ninguém devolveu (ou ficou faltando) · Cada um pediu e pagou separado · Outro

**6. Imagine: cada um escreve uma frase ("quero algo leve até R$ 30", "sem carne"), uma IA monta o pedido do grupo
em 1 ou mais restaurantes, e cada um paga a sua parte por Pix. O quanto você usaria?**
(escala linear 1 a 5) 1 = Nunca usaria · 5 = Usaria com certeza
6b. (opcional, resposta curta) O que faria você **não** usar?

## Como tabular (15 min, na planilha do Forms)
Anotar **n** = total de respostas e **n_grupo** = respostas que não marcaram "Nunca" na P1.

| Indicador | Cálculo | Base |
|---|---|---|
| % que pediu em grupo no último mês | (semana + mês) / n | n |
| % que levou **mais de 15 min** para decidir | (15–30 + >30) / respostas válidas da P2 (sem "Não lembro") | n_grupo |
| % em que **cada um pediu separado** | marcou "Cada um pediu separado" / n_grupo | n_grupo |
| % com **atrito** (desistiu, ficou com o que não queria, ou o grupo desistiu) | marcou pelo menos 1 dessas 3 / n_grupo | n_grupo |
| % que **quis lojas diferentes** | ("Sim, e pedimos…" + "Sim, mas alguém cedeu") / respostas válidas da P4 | n_grupo |
| % em que **alguém adiantou e cobrou Pix depois** ou ficou faltando dinheiro | (opção 1 + opção 4 da P5) / n_grupo | n_grupo |
| Intenção de uso | média da P6 e **% de notas 4 ou 5** (top-2) | n |
| Objeções | agrupar a 6b em 3–4 temas (ex.: privacidade, confiança na IA, prefiro escolher) | quem respondeu |

Fórmulas úteis no Planilhas: `=CONT.SE(B:B;"Na última semana")`, `=CONT.SE(D:D;"*separado*")` (caixas de seleção
vêm numa célula só, separadas por vírgula, por isso o `*`), `=MÉDIA(G:G)`, `=CONT.SE(G:G;">=4")/CONT.VALORES(G2:G)`.

**Regras de honestidade:** sempre dizer o **n** e a base (n ou n_grupo); com n < 20 não falar em porcentagem, falar
"X de Y pessoas"; arredondar para inteiro; não somar opções da P3 (é múltipla). Não chamar de "pesquisa
representativa": é amostra de conveniência (participantes de um evento de computação).

## Frase de pitch modelo
> "Perguntamos para **X** pessoas aqui na SEMCOMP: **Y%** levaram mais de 15 minutos para decidir o pedido do grupo,
> em **Z%** das vezes cada um acabou pedindo separado, e **W%** usariam o Match (nota 4 ou 5)."
> Rodapé do slide: *Pesquisa da equipe, SEMCOMP São Carlos, 17/10/2026, n = X, amostra de conveniência, anônima.*

Variante para n pequeno: "**X de Y** pessoas que pediram em grupo disseram que alguém precisou adiantar o dinheiro e cobrar Pix depois."

## Resultado

**Não aplicada.** A coleta não aconteceu durante o evento (18/10). Nenhum número desta pesquisa aparece nos
entregáveis nem no pitch; ela fica como primeiro passo do piloto.
