---
description: Recebe o enunciado oficial do hackathon e produz a análise de ideias. Não implementa nada.
argument-hint: <cole aqui o enunciado, regras e critérios>
---

Você é o **engenheiro-chefe (orquestrador)** da equipe no Hackathon iFood × SEMCOMP 29. Leia `CLAUDE.md`,
`docs/ifood-apis.md`, `docs/mcp.md` e `docs/decisions.md` antes de responder.

Enunciado e informações recebidas da equipe:

$ARGUMENTS

Faça, nesta ordem, e PARE no fim (não implemente nada):

0. Se o enunciado tiver regra sobre código feito antes do evento, diga logo no início o que isso significa para o
   esqueleto existente (usar, reescrever ou descartar).
1. Resumo do desafio, regras e critérios de avaliação. Se os critérios não vierem, use hipóteses explícitas e
   pergunte (no máximo 3 perguntas).
2. Quem é o "cliente" (lojista, entregador, consumidor, iFood) e a dor real dele.
3. O que as APIs do iFood permitem de fato (base: `docs/ifood-apis.md`) e o papel do MCP. Se o enunciado trouxer
   APIs, credenciais ou plataforma nova, use o subagente `pesquisador` para confirmar com fontes.
4. 4–5 ideias. Para cada: lado (VENDA, COMPRA ou OS DOIS), problema, usuário, o que o agente faz, APIs e ferramentas
   MCP usadas, demo de 2 minutos com o "momento uau", risco técnico. Pelo menos uma de cada lado; diga qual lado o
   enunciado favorece.
5. Tabela de notas (1–5): aderência ao tema · uso real de IA+MCP+APIs iFood · impacto/valor de negócio ·
   viabilidade em ~29h com 4 pessoas · força da demo · diferencial. Total ponderado (diga os pesos).
6. Recomendação + MVP mínimo (entra / fica fora) + plano por horas + quem faz o quê (Thales: pitch/front/testes;
   Milan: IA/back/design; Zenon: testes/pitch; Antonio: testes) + quais subagentes vão trabalhar em paralelo.

Salve a análise completa em `docs/planos/etapa-01-analise.md` (é a memória desta etapa: depois de um `/clear`
nada se perde), registre a etapa em `docs/planos/README.md`, aponte "Plano vigente" no `CLAUDE.md`, faça commit
(`docs(plano): etapa 01 análise do tema`) e push.

Termine com: o que mudou · 🧪 como testar · 👥 o que a equipe faz agora. Depois **aguarde a aprovação**; a equipe
vai responder com `/executar <ideia escolhida e ajustes>` (pode dar `/clear` antes).
