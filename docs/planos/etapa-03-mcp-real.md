# Etapa 03 — MCP real do iFood (+ polimento apontado pelo QA)

> Escrito pelo engenheiro-chefe (Opus). Este arquivo é a memória da etapa: depois de um `/clear`,
> `/continuar` lê só o `CLAUDE.md` e este plano e segue daqui.

- **Status da etapa:** em execução (rodada 1 desde 17/10 ~23h50)
- **Objetivo (1 frase):** o mesmo Match roda contra o **MCP real** (`consumer-mcp.ifood.com.br/marketplace`) com
  login OAuth de uma conta de teste, sem mudar motor nem telas; e a demo fica mais robusta (achados do QA 02.9).
- **Pronto quando:** no PC da equipe, com `IFOOD_MCP_MODO=real` e o `.env` preenchido: "Conectar iFood" abre o
  login oficial, volta para `localhost:8000/oauth/callback`, o Match roda com lojas/itens/preços **reais** perto do
  endereço da conta de teste e monta os carrinhos até o `getCart` (taxa real); `IFOOD_MCP_MODO=demo` continua
  idêntico; `./iniciar.sh --testes` passa.
- **Prazo (horário BRT):** sáb 17/10 ~23h45 → dom 18/10 **03h**
- **Aprovado pela equipe em:** escopo já aprovado (etapa 03 do `README.md`); envio real de pedido depende da pergunta 1 abaixo.

## Contexto mínimo para retomar
- Etapa 02 fechada (95 testes; QA aprovou o fluxo inteiro em 390×780). Código do Match: `backend/app/match/`
  (motor, otimizador, acerto, pix, checkout, salas), `backend/app/rotas_match.py`, `backend/app/ifood_mcp/`
  (`cliente.py` com `abrir_cliente(cfg)`; modo real hoje = `NotImplementedError("etapa 03")`), telas em `frontend/src/telas/`.
- **Só 2 arquivos leem campos das tools:** `match/busca.py` (descoberta, funções `ler_*`) e `match/checkout.py`
  (`_ler_*`). Adaptar ao formato real = mexer só neles.
- OAuth (verificado ao vivo, sem credencial): autorização `https://id.ifood.com.br/authorize`, token
  `https://id.ifood.com.br/token`, `authorization_code` + `refresh_token`, **PKCE S256**, `client_secret_basic`/`_post`,
  **sem registro dinâmico**. Metadados do recurso: `/.well-known/oauth-protected-resource/marketplace` →
  `authorization_servers: [id.ifood.com.br]` (não lista scopes). Redirect cadastrada: `http://localhost:8000/oauth/callback`.
- O login só funciona **no PC da equipe** (o retorno vai para o `localhost` de quem roda o app). O container da
  nuvem não tem o secret → o ciclo é: 🤖 escreve → 👥 roda o diagnóstico no PC e dá push das amostras → 🤖 adapta.
- SDK `mcp` 2.x no venv tem `mcp.client.streamable_http` e `mcp.client.auth`.
- Regras: secret e tokens só no `.env`/arquivo ignorado pelo git; **nunca pagar Pix de pedido de teste**;
  `submitOrder` real só com resposta da equipe à pergunta 1.

## Contratos desta etapa
### C9. OAuth e cliente real
- `backend/app/ifood_mcp/oauth.py`: `url_login(cfg) -> str` (gera `state` + `code_verifier`, guarda em memória,
  `code_challenge` S256, `redirect_uri` = `cfg.ifood_mcp_redirect` padrão `http://localhost:8000/oauth/callback`);
  `async trocar_codigo(cfg, code, state) -> Tokens`; `async token_valido(cfg) -> str` (renova com refresh 5 min antes
  de expirar). Tokens em `backend/.tokens_ifood.json` (**no `.gitignore`**), nunca no log nem em resposta HTTP.
- Rotas (em `backend/app/rotas_oauth.py`, incluídas no `main.py`): `GET /oauth/login` → 302 para o authorize;
  `GET /oauth/callback?code&state` → troca, salva, redireciona para `/#/conectado`; `GET /api/ifood/status` →
  `{modo, conectado, expira_em?, conta?}` (conta = só o primeiro nome do `getUser`, se existir); `POST /api/ifood/sair`.
- `abrir_cliente(cfg)` modo `real`: sessão MCP Streamable HTTP em `https://consumer-mcp.ifood.com.br/marketplace`
  com `Authorization: Bearer <token_valido>`; 401 → renova 1 vez e repete; sem token → `ErroMCP("Conecte o iFood
  primeiro")` (a API devolve 401 legível). Mesmo `ClienteIFood`/rastro do demo.
- `GET /api/salas/{id}` passa a refletir `demonstracao: false` no modo real e `conta_teste: true`.

### C10. Diagnóstico real (roda no PC da equipe)
`python -m app.ifood_mcp.diagnostico [--carrinho]` (usa o token salvo): `list_tools` (nome, descrição, input_schema)
→ `docs/mcp-real/tools.json`; chamadas **só leitura** `getUser`, `listAddresses`, `searchOffers` ("pizza",
"sorvete", "hambúrguer" com ITEM e MERCHANT), `getMerchant` e `getItem` do 1º resultado, `getRecommendations`
→ `docs/mcp-real/<tool>.json`. Com `--carrinho`: `createCart` em 2 lojas diferentes (testa 2 carrinhos abertos),
`addItemToCart`, `getCartDeliveryMethods`, `listPaymentMethods`, `getCart` — **nunca `submitOrder`**.
**Sanitização obrigatória** antes de gravar: remover/mascarar nome, e-mail, telefone, CPF/`taxPayerIdentificationNumber`,
`paymentMethods` (últimos dígitos), endereço textual (manter só bairro/cidade e coordenadas arredondadas a 2 casas),
qualquer campo com `token`. Imprime um resumo (nº de tools, nomes que diferem da doc, campos de preço/taxa achados).

## Tarefas

| ID | Tarefa | Agente | Modelo | Esforço | Arquivos (só estes) | Depende de | Pronto quando | Status |
|---|---|---|---|---|---|---|---|---|
| 03.1 | OAuth + cliente MCP real + diagnóstico (C9, C10) | dev-mcp-ifood | opus | high | `backend/app/ifood_mcp/oauth.py`, `cliente.py`, `diagnostico.py`, `backend/app/rotas_oauth.py`, `backend/app/main.py` (só incluir router), `backend/app/config.py` (`ifood_mcp_redirect`), `.gitignore`, `.env.example`, `backend/tests/test_oauth.py` | — | testes com HTTP falso: PKCE S256 correto, state inválido → 400, troca/refresh, token nunca aparece em resposta/log, 401 → refresh 1×; `IFOOD_MCP_MODO=demo` inalterado; diagnóstico sanitiza (teste com payload falso cheio de dados pessoais) | 🔄 |
| 03.2 | Front: "Conectar iFood", selo real × demonstração + polimento do QA | dev-frontend | sonnet | medium | `frontend/src/telas/Inicio.tsx`, `Organizador.tsx`, `Convidado.tsx`, `Resultado.tsx`, `frontend/src/componentes/Selo.tsx`, `frontend/src/componentes/StatusIfood.tsx` (novo), `frontend/src/api.ts`, `frontend/src/tipos.ts`, `frontend/src/estilo.css`, `frontend/src/App.tsx` | C9 (contrato) | build ok; no modo real o organizador vê "Conectar iFood"/"Conectado"; selo "iFood real · conta de teste"; itens do QA abaixo resolvidos | ✅ |
| 03.3 | Robustez do motor e do Pix (QA 02.9 #2, #7) | dev-backend | sonnet | high | `backend/app/match/motor.py`, `backend/app/match/pix.py`, `backend/tests/test_motor.py`, `backend/tests/test_acerto_pix.py` | — | pedido fora do cardápio ("feijoada") gera aviso "Não achei X; a opção mais próxima é Y" ou 409 se nota < 0,5 para todos; chave Pix normalizada (CPF/CNPJ só dígitos, telefone +55…, e-mail minúsculo, aleatória intacta) com testes | ✅ |
| 03.4 | 👥 Rodar login + diagnóstico no PC e dar push das amostras | equipe | — | — | `docs/mcp-real/*.json` | 03.1 | `docs/mcp-real/tools.json` e amostras no git; responder "2 carrinhos abertos?" | ⬜ |
| 03.5 | Adaptar busca e checkout ao formato real + feedback do MCP | dev-mcp-ifood | opus | high | `backend/app/match/busca.py`, `backend/app/match/checkout.py`, `backend/tests/test_formato_real.py` (fixtures = amostras sanitizadas), `docs/feedback-mcp.md`, `docs/mcp-ifood.md` | 03.4 | testes com as amostras reais passam; Match roda no PC com dados reais até o `getCart`; diferenças doc × real registradas | ⬜ |
| 03.6 | Revisão da etapa | qa-testador | opus | high | (só leitura) | 03.1–03.5 | nada "bloqueia a demo"; modo demo intacto; nenhum dado pessoal nas amostras/commits | ⬜ |

Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ❌ falhou (ver registro) · ⏸️ adiado

**Itens do QA 02.9 para a 03.2 (front):** botão "Recarregar demo" discreto (só no modo demo; o roteiro cita);
"Não sou {nome}" na tela do convidado (apaga o `match.pid` — abas anônimas dividem o localStorage); "Voltar para a
sua sala" na home se houver token salvo; cards de loja da home sem números que não vêm do MCP (só nome + "demo");
"N de M responderam" sem contar o organizador que não respondeu; quadro sem resumo/aviso duplicado; "2× Sundae" em
vez de linha repetida; rastro mostra `userConsent: sim` (não `True`); campo de orçamento aceita vírgula
(`inputMode="decimal"`, `type="text"`); formulário de desejo do organizador recolhível; dica no campo "Base do link"
("use o IP do Wi-Fi, ex. 192.168.x.x; evite 172.x").

**Por que esses modelos/esforços:** 03.3 sonnet/high: mudanças localizadas mas com regra de dinheiro (Pix) e de
honestidade (aviso de "não achei"). 03.5 opus/high: mapear formato real sem quebrar o demo é o ponto mais arriscado.

**Paralelismo:** Rodada 1: 03.1, 03.2, 03.3 · depois 👥 03.4 · Rodada 2: 03.5 · Rodada 3: 03.6.

## Perguntas para a equipe (bloqueiam só o `submitOrder` real)
1. Quais formas de pagamento a conta de teste mostra no app/opencode? Existe alguma que **não** cobre de verdade
   (ex.: "pagar na entrega")? Se não houver, a demo real para no `getCart` e o envio fica no modo demonstração.

## Riscos e plano B
- **Login não volta para o app** (redirect diferente, porta ocupada): conferir a Redirect URL exata no Portal;
  plano B = demo com `IFOOD_MCP_MODO=demo` (já pronta).
- **Formato real muito diferente da doc:** 03.5 isola em `busca.py`/`checkout.py`; se faltar tempo, a demo real mostra
  só a descoberta (busca + carrinho) e o restante segue no demo, dito com clareza no pitch.
- **Rate limit / lentidão do MCP real:** limitar consultas por slot (≤ 2) no modo real; cache por sala.
- **2 carrinhos simultâneos não permitidos:** checkout monta e envia loja por loja (o código já é sequencial).

## Registro de execução
(o engenheiro anota aqui ao fim de cada rodada: data/hora, tarefas concluídas, commit, problemas)
- 18/10 ~00h30 — 03.2 ✅ (ce2f12d: Conectar iFood, selo real, Recarregar demo, "Não sou fulano", orçamento com
  vírgula, 2×) · 03.3 ✅ (75ae96d + cadee7a: aviso "opção aproximada" com limiar 0,5; Pix normalizado). 122 testes.
  **03.1 ainda em andamento** quando a equipe pediu `/clear`: arquivos parciais commitados como wip
  (`ifood_mcp/oauth.py`, `config.py` com `ifood_mcp_redirect`/`ifood_mcp_scope`). **Ao retomar:** conferir se
  existem `ifood_mcp/oauth.py`, `ifood_mcp/diagnostico.py`, `rotas_oauth.py`, `tests/test_oauth.py` e se `main.py`
  inclui o router; rodar os testes. Completo → marcar 03.1 ✅ e passar a 03.4 (👥). Incompleto → redisparar a 03.1
  (mesmo prompt do contrato C9/C10) dizendo para **continuar** a partir dos arquivos existentes.
- Pendências menores: front pode destacar `motivo` que começa com "Opção aproximada:"; juiz sugere bebida como
  "opção mais próxima" em empate (ex.: pizza sem glúten → refrigerante) — ajustar `juiz.py` na etapa 04.

## Fechamento
(preenchido ao concluir: o que entregou, o que ficou para a próxima etapa, próxima etapa sugerida)
