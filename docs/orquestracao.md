# Orquestração: engenheiro-chefe + subagentes

## A ideia
O chat principal (Claude **Opus**) é o **engenheiro-chefe**: entende o tema, propõe ideias, escreve o **plano
detalhado de cada etapa** no repositório, **delega** cada tarefa a um subagente com o modelo e o esforço adequados,
integra, testa e faz commit. A equipe humana decide e valida.

```
        Equipe (decide, valida, apresenta)
                     │  /tema → /executar → /continuar … /status
                     ▼
        Engenheiro-chefe (chat principal, Opus) ──escreve──▶ docs/planos/etapa-NN.md
     ┌──────┬────────┬──────────┬───────────┬──────────┬────────────┐
 arquiteto  dev-     dev-mcp-   dev-        qa-        pitch-demo   pesquisador
 (contratos)backend  ifood      frontend    testador   (slides,     (fatos com
                                            (revisa)   roteiro)     fonte)
```

Subagentes em `.claude/agents/`. Cada tarefa tem **arquivos exclusivos** (sem conflito entre agentes paralelos);
subagente **não faz commit** — quem integra e commita é o engenheiro-chefe.

## Fluxo com /clear (contexto nunca explode)

| Passo | Comando | Resultado gravado no repo | Depois |
|---|---|---|---|
| 1 | `/tema <enunciado completo>` | `docs/planos/etapa-01-analise.md` | equipe escolhe a ideia |
| 2 | `/executar <ideia + ajustes>` | `docs/planos/etapa-02-*.md` com tarefas, agente, **modelo, esforço** | `/clear` |
| 3 | `/continuar` | código + plano atualizado (status, registro) + commit | `/clear` quando o chat sugerir |
| 4 | `/continuar` … | ao fechar uma etapa, ele já escreve o plano da próxima | repetir |
| — | `/status` | nada (só leitura) | a qualquer hora |

Depois de `/clear`, o chat só sabe o que está no `CLAUDE.md` e no plano vigente — por isso tudo que importa é
escrito lá. Se mudar a estratégia/escopo no meio, o engenheiro **para e pede aprovação**.

## Guia de modelo e esforço (padrão — o plano pode ajustar com justificativa)

| Tipo de tarefa | Agente | Modelo | Esforço |
|---|---|---|---|
| Plano da etapa, decisões de arquitetura | engenheiro-chefe / `arquiteto` | opus | high |
| Lógica do agente, ferramentas MCP, integração iFood | `dev-mcp-ifood` / `dev-backend` | opus | high |
| Endpoint ou ajuste simples no backend | `dev-backend` | sonnet | medium |
| Tela ou componente React novo | `dev-frontend` | sonnet | medium |
| Ajuste visual, texto, CSS | `dev-frontend` | haiku | low |
| Revisão antes de commit da demo | `qa-testador` | opus | high |
| Só rodar testes e relatar | `qa-testador` | haiku | low |
| Pesquisa com fontes | `pesquisador` | sonnet | medium |
| Texto do pitch, roteiro da demo | `pitch-demo` | opus | medium |
| Nota da banca simulada (pitch e entregáveis) | `jurado` | opus | high |
| Bug difícil / intermitente | dev da área | opus | xhigh |

Regra: começar pelo mais barato que dá conta; se a tarefa falhar ou voltar fraca, subir um nível e anotar no plano.

## Memória enxuta (CLAUDE.md)
- Limite: **250 linhas**, só estado vigente.
- Hook automático (`.claude/settings.json` → `.claude/hooks/limite-claude-md.mjs`): a cada edição do `CLAUDE.md`
  acima do limite, o Claude recebe a ordem de mover o que não é mais vigente para `docs/historico.md` (arquivar,
  nunca apagar) e voltar a ~180 linhas. No início de cada sessão o hook também confere.

## Se os comandos não aparecerem
Os comandos e o hook só existem se o chat estiver nesta branch (`claude/wizardly-hopper-vks5rs`) ou se ela tiver
sido juntada à `main`. Sem eles, cole o texto de `docs/prompt-abertura.md` com o enunciado.
