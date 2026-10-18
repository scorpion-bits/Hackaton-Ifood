# ⚠️ AVISO À EQUIPE E A TODOS OS AGENTES — leia antes de qualquer tarefa

> Vale a partir de **sáb 17/10 ~23h15** (decisão do Milan, a equipe está sendo avisada). Substitui qualquer plano
> que diga o contrário. Agente (Claude ou outro): leia este arquivo e o `docs/quadro.md` **antes** de editar código.

## 1. Estratégia daqui até a submissão (dom 12h30)
**Foco único: o MCP real do iFood + o Match em pedido em grupo, funcionando de ponta a ponta.**
Enxugar ao máximo; nada de ideia nova até termos algo funcional no MCP real.

Prioridades, nesta ordem:
1. **MCP real funcionando**: login OAuth → endereço → busca (`searchOffers`/`getMerchant`/`getItem`) → carrinho
   (`createCart`/`addItemToCart`) → entrega e pagamento → `getCart` com taxa e total reais. `submitOrder` real só
   com consentimento na tela e `IFOOD_MCP_PERMITIR_ENVIO=true`; **nunca pagar Pix de pedido de teste**.
   (É a tarefa T8 de `docs/planos/etapa-04-leilao-e-entrega.md`.)
2. **Match em grupo estável**: criar sala → convidados entram pelo link/QR → cada um escreve o que quer → combinação
   com item/loja/preço/motivo → divisão da conta → pedidos. Só correção de bug.
3. **Tudo integrado e na `main`** (hoje a `main` está atrasada em relação ao branch de integração).
4. **Pitch enxuto**: uma frase só — *"pedido em grupo sem dor: cada um fala o que quer, o IBits monta, divide a
   conta e pede pelo iFood"*. O leilão é só a forma visual de mostrar que a IA avalia cada loja (um agente por loja
   que só vê o cardápio dela); **não dizer** que os restaurantes têm agentes no iFood.

**Congelado** (não expandir; só corrigir bug se quebrar a demo):
- Leilão de agentes, deck "É um Match!" e animações — ficam como estão.
- "Patrocinado" — não evoluir e não destacar no pitch.
- Funcionalidade nova de qualquer tipo, pesquisa nova, refatoração grande.

## 2. Regras de colaboração (obrigatórias para todo agente)

### 2.1 Autor humano em todo commit
Cada pessoa usa a própria sessão do Claude. **Todo commit leva quem pediu o trabalho**:
- No início da sessão, o agente pergunta **"quem é você?"** (nome e e-mail) se ainda não souber.
- Commit com autor humano: `git commit --author="Nome <email>" -m "..."`.
- E a linha `Responsável: Nome` no fim da mensagem (antes do `Co-Authored-By` do Claude, se houver).
- Equipe: Thales Miguel Hajes · Milan (`milan.b.dev@gmail.com`) · Zenon · Antonio. Sem o e-mail da pessoa →
  perguntar a ela; não inventar.

### 2.2 Quadro de trabalho (`docs/quadro.md`) — é assim que os agentes "conversam"
- **Antes de começar**: `git pull` do branch de integração, ler o quadro, registrar uma linha (pessoa, branch,
  tarefa, **arquivos que vai mexer**, status, hora) e dar push **só dessa linha** logo em seguida.
- **Arquivo já reservado por outra linha "em andamento"** → não mexer; escrever em "Recados" e escolher outra coisa
  ou esperar.
- **Ao terminar ou parar**: atualizar a linha (✅, commit, o que ficou pendente) e dar push.
- Conflito no `docs/quadro.md` no push → `git pull --rebase` e manter as linhas dos dois lados.

### 2.3 Branches e integração
- Branch de integração: **`ccr-4c429dbb-lp7btg`** (integração vigente). Daqui sai o PR para a `main`.
- Branch novo de tarefa: `<pessoa>/<tarefa>` (ex.: `zenon/fix-convidado`), criado a partir do de integração.
- Commits pequenos em português: `tipo(escopo): descrição` (regra de sempre).
- Quem integra no `ccr-4c429dbb-lp7btg` e na `main` é **uma sessão só por vez** (marcada no quadro como
  "integração"). Ninguém faz force-push em branch dos outros.
- Antes do push: `./iniciar.sh --testes` (e `cd frontend && npm run build` se mexeu no front).
