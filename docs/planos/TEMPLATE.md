# Etapa NN — <nome curto>

> Escrito pelo engenheiro-chefe (Opus). Este arquivo é a memória da etapa: depois de um `/clear`,
> `/continuar` lê só o `CLAUDE.md` e este plano e segue daqui.

- **Status da etapa:** planejada | em execução | concluída
- **Objetivo (1 frase):**
- **Pronto quando:** (critério testável, ex.: "no Windows, clicar X mostra Y e o teste Z passa")
- **Prazo (horário BRT):**
- **Aprovado pela equipe em:** (data/hora ou "aguardando")

## Contexto mínimo para retomar
(5–10 linhas: o que já existe, decisões que valem, arquivos-chave. Nada que já esteja no CLAUDE.md.)

## Contratos desta etapa
(rotas, ferramentas MCP, tipos — só o que muda nesta etapa)

## Tarefas

| ID | Tarefa | Agente | Modelo | Esforço | Arquivos (só estes) | Depende de | Pronto quando | Status |
|---|---|---|---|---|---|---|---|---|
| NN.1 | | dev-mcp-ifood | opus | high | `backend/app/mcp_server.py` | — | teste X passa | ⬜ |
| NN.2 | | dev-frontend | sonnet | medium | `frontend/src/...` | NN.1 | build ok + tela Y | ⬜ |
| NN.3 | Revisão | qa-testador | opus | high | (só leitura) | NN.1, NN.2 | sem "bloqueia a demo" | ⬜ |

Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ❌ falhou (ver registro) · ⏸️ adiado

**Por que esses modelos/esforços:** (1 linha por escolha fora do padrão de `docs/orquestracao.md`)

**Paralelismo:** (quais tarefas rodam juntas numa mesma rodada)

## Riscos e plano B
-

## Registro de execução
(o engenheiro anota aqui ao fim de cada rodada: data/hora, tarefas concluídas, commit, problemas)

## Fechamento
(preenchido ao concluir: o que entregou, o que ficou para a próxima etapa, próxima etapa sugerida)
