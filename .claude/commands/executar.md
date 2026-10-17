---
description: Ideia aprovada → o engenheiro-chefe escreve o plano detalhado da próxima etapa (com modelo e esforço por agente) e para.
argument-hint: <ideia aprovada + ajustes da equipe>
---

A equipe aprovou: $ARGUMENTS

Você é o **engenheiro-chefe (orquestrador)**. Leia `CLAUDE.md`, `docs/orquestracao.md` e o plano vigente (se houver).

1. Registre a decisão em `docs/decisions.md` e atualize o `CLAUDE.md` (fase, ideia, MVP), mantendo-o enxuto.
2. Divida o MVP em **etapas** de 2–4h. A primeira é a **fatia vertical** (agente → ferramenta MCP → API iFood →
   tela) funcionando até a noite do dia 17; o pitch começa já na primeira etapa (tarefa do `pitch-demo`).
   Liste as etapas em `docs/planos/README.md` (número, nome, objetivo, status).
3. Escreva o plano detalhado da **próxima etapa** em `docs/planos/etapa-NN-<nome>.md` a partir de
   `docs/planos/TEMPLATE.md`. Para cada tarefa: agente, **modelo e esforço recomendados** (guia em
   `docs/orquestracao.md`, com justificativa quando fugir do padrão), arquivos exclusivos, dependências, critério
   de pronto testável. Se precisar de contratos complexos, use o subagente `arquiteto`.
4. Aponte o plano vigente no `CLAUDE.md` (linha "Plano vigente: ...").
5. Faça commit dos planos (`docs(plano): etapa NN`) e push.
6. **Pare** e responda curto: resumo da etapa, tabela de tarefas (agente/modelo/esforço), riscos. Diga à equipe:
   "pode dar `/clear` e depois `/continuar`".
