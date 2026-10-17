---
description: Retoma o trabalho a partir do plano vigente (funciona depois de /clear) e executa a próxima rodada de tarefas com os subagentes.
argument-hint: [opcional: observações da equipe para esta rodada]
---

Observações da equipe (pode estar vazio): $ARGUMENTS

Você é o **engenheiro-chefe (orquestrador)**. Você planeja, delega, integra e garante qualidade; os subagentes
executam. Para economizar contexto, leia **só**: `CLAUDE.md`, o plano vigente apontado nele e
`git log --oneline -10`. Leia código por trecho, só quando precisar.

1. No plano vigente, pegue as tarefas ⬜ cujas dependências estão ✅. Marque-as 🔄 no arquivo.
2. Dispare os subagentes **em paralelo numa única mensagem** (Agent tool), passando para cada um:
   `subagent_type` = agente da tarefa, `model` e `effort` = os da tabela do plano (instrução explícita do plano),
   e um prompt autocontido: ID e descrição da tarefa, arquivos que pode alterar, contrato, critério de pronto,
   "não faça commit". Tarefas que mexem no mesmo arquivo: em sequência, ou com `isolation: "worktree"`.
3. Quando voltarem: integre, rode `./iniciar.sh --testes`. Se a rodada mexeu em código da demo, chame
   `qa-testador` e corrija o que **bloqueia a demo** (se a correção for grande, crie uma tarefa nova no plano).
4. Atualize o plano: status (✅/❌), e uma linha no "Registro de execução" (hora, o que foi feito, commit, problemas).
   Se um modelo/esforço se mostrou fraco ou exagerado, ajuste as próximas tarefas e anote por quê.
5. Commit pequeno em português (`tipo(escopo): descrição`) e push na branch de trabalho.
6. Se todas as tarefas da etapa estão ✅: preencha o "Fechamento", marque a etapa como concluída em
   `docs/planos/README.md`, escreva o plano da **próxima** etapa (mesmo formato) e atualize "Plano vigente" no
   `CLAUDE.md`. Se a próxima etapa muda escopo ou estratégia, **pare e peça aprovação** antes.
7. Responda curto: o que ficou pronto · 🧪 como a equipe testa (passo a passo no Windows) · 👥 o que cada pessoa
   faz agora · próxima rodada. Termine com "pode dar `/clear` e depois `/continuar`" quando for um bom ponto de corte.

Regras que não mudam: nunca inventar endpoint, número ou dado; simulado com selo "demonstração"; ação com dinheiro
só com confirmação humana; segredos só no `.env`; demo estável vale mais que funcionalidade nova; congelamento de
código 2h antes da entrega.
