# Pedidos para o Thales — fila que o agente do Thales executa com ele

> **Agente do Thales:** no começo de cada rodada, dê `git pull origin ccr-4c429dbb-lp7btg` e leia este arquivo. Pegue o
> primeiro item ⬜ cujo "Depende de" está ok, guie o Thales passo a passo no PC dele (Windows, `backend\.venv`) e, ao
> terminar, mude o status para ✅ (ou ❌ com o motivo) e escreva o resultado na coluna "Resultado". Problema novo →
> linha no `docs/testes/bugs.md`. Dê push no teu branch (`claude/wizardly-hopper-vks5rs`) e deixe 1 linha no
> `docs/quadro.md` ("Thales → Milan: Pnn feito"). Nunca commitar o `.env`, chave, token nem dado pessoal; nunca
> `submitOrder`/`setCartPayment` sem o Milan pedir aqui; nunca pagar Pix.
>
> **Milan/Zenon:** só acrescentam linhas novas no fim (P seguinte) com hora do `date`; não mudam linha de outra pessoa.
> Milan, Thales e Zenon trabalham em paralelo: este arquivo é o canal, não precisa chamar o Thales.

| ID | Hora | Pedido (passo a passo) | Depende de | Status | Resultado |
|---|---|---|---|---|---|
| P1 | 18/10 00h56 | **Endereço na conta de teste (bugs 4 e 6).** (1) Entrar no app ou site do iFood com a conta `unique-thales@test.ifood.com.br` e salvar o endereço do evento por lá. (2) Se não der, testar `safe-thales` e `fair-thales` (Conectar iFood no app com cada uma → `.venv\Scripts\python.exe -m app.ifood_mcp.diagnostico`). (3) Com uma conta que tenha endereço: rodar o diagnóstico de novo e dar push só do `docs/mcp-real/listAddresses.json` novo (sanitizado). Anotar qual conta funcionou. | — | ⬜ | |
| P2 | 18/10 00h56 | **IA real (A3).** (1) `git pull origin ccr-4c429dbb-lp7btg` (traz `app/match/testar_ia.py`). (2) No `.env`: `LLM_PROVIDER=groq`, `LLM_MODEL=openai/gpt-oss-120b`, `GROQ_API_KEY=…` (já tem). (3) `cd backend` → `.venv\Scripts\python.exe -m app.match.testar_ia > ..\docs\testes\ia-real.txt`. (4) Conferir que o arquivo não tem a chave e dar push. Se der muito "caíram no fallback", rodar de novo com `LLM_MODEL=llama-3.3-70b-versatile` em `ia-real-2.txt`. | — | ⬜ | |
| P3 | 18/10 00h56 | **Match real até o carrinho.** Aguardar o Milan marcar aqui "A1 pronto" (correção dos bugs 1, 2, 3 e 5). Depois: `IFOOD_MCP_MODO=real` no `.env`, `iniciar.bat`, sala com 3 pessoas do roteiro → Rodar Match → escolher → ver o carrinho com taxa real. **Sem enviar o pedido.** Print da tela do carrinho + bug novo no `bugs.md`. | P1 ✅ (A1 pronto: ver P4) | ⬜ | |
| P4 | 18/10 01h12 | **A1 pronto** (bugs 1, 2, 3 e 5 corrigidos no `ccr`, 402 testes). Faça junto com o P3, **depois do P1** (sem endereço salvo o `createCart` sempre falha): (1) `git pull origin ccr-4c429dbb-lp7btg`. (2) `.venv\Scripts\python.exe -m app.ifood_mcp.diagnostico --carrinho` e push de `createCart.json`, `getCartDeliveryMethods.json`, `listPaymentMethods.json`, `getCart.json` (ainda não temos amostra de carrinho **com sucesso**). (3) No P3, anotar no `bugs.md`: o `createCart` devolve `cartId` e `items[].cartItemId`? o `getCart` traz `subtotal`/`deliveryFee`/`total` como número? (4) Escolher na demo item **sem opção obrigatória** (ex.: pizza com sabor obrigatório pode ser recusada sem `options`) — se recusar, anotar o erro. (5) Duas pessoas com o **mesmo item**: o carrinho real faz 2 linhas ou 1 com `quantity: 2`? (6) O `listPaymentMethods` da conta tem forma "na entrega/dinheiro"? Sem ela, o app para antes do `setCartPayment` (é o esperado). | P1 ✅ | ⬜ | |
