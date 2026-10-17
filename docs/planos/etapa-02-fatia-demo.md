# Etapa 02 — Fatia vertical do Match em modo demonstração

> Escrito pelo engenheiro-chefe (Opus). Este arquivo é a memória da etapa: depois de um `/clear`,
> `/continuar` lê só o `CLAUDE.md` e este plano e segue daqui.

- **Status da etapa:** planejada
- **Objetivo (1 frase):** o fluxo inteiro do Match em grupo roda de ponta a ponta contra um **MCP de demonstração**
  (mesmos nomes de tools do iFood, dados gravados com selo), sem depender de credencial nem de internet.
- **Pronto quando:** em `./iniciar.sh` (e `iniciar.bat`), em viewport 390×780: organizador cria a sala → 3 convidados
  entram pelo link (abas anônimas) e respondem → **Rodar Match** mostra a combinação com item/loja/preço/motivo/nota
  → organizador escolhe "separado" → partes por pessoa batem com o total (centavos) → 1 paga por Pix (QR aparece),
  1 por cartão simulado, 1 em dinheiro → organizador marca "recebi" → **Enviar pedidos** → cartões de pedido com
  status; o rastro das tools MCP aparece; `./iniciar.sh --testes` passa.
- **Prazo (horário BRT):** sáb 17/10 ~20h → **23h30**
- **Aprovado pela equipe em:** 17/10 ~19h45 (escopo §7 + §12 + §13 opção 1 de `etapa-01b-match-estrategia.md`)

## Contexto mínimo para retomar
- Decisões e limites do MCP: `docs/planos/etapa-01b-match-estrategia.md` (§4 pontuação, §5 tools, §12, §13).
- O esqueleto da Fase 0 é **referência**. Reaproveitar: `config.py`, `agente/provedores.py` (provedores de LLM),
  `iniciar.*`, build do front servido pelo FastAPI. O domínio antigo (lojas/vendedor/comprador, Merchant API) **não
  é usado** pelo Match; não apagar nesta etapa (os 13 testes antigos devem continuar passando).
- O Match é **cliente MCP**: fala com um servidor MCP pelo SDK `mcp` 2.x. Nesta etapa o servidor é o
  **`demo_server.py`** (em processo, `Client(servidor)`); na etapa 03 troca para o remoto
  `https://consumer-mcp.ifood.com.br/marketplace` com OAuth. **Mesmo código do motor e do checkout nos dois modos.**
- LLM: provedor do `.env`; **sem chave o modo `mock` precisa produzir a demo inteira** (determinístico).
- Regras: preço, taxa, prazo e disponibilidade só vêm de resposta de tool; nunca do LLM. `submitOrder` só com
  `userConsent: true` depois de confirmação humana na tela **e** 100% pago (modo separado).

## Contratos desta etapa

### C1. Cliente MCP — `backend/app/ifood_mcp/cliente.py`
```python
@dataclass
class ChamadaRastro: tool: str; resumo: str; ms: int; ok: bool; erro: str | None = None

class ClienteIFood:
    modo: str                      # "demo" | "real"
    rastro: list[ChamadaRastro]
    async def chamar(self, tool: str, **args) -> dict   # structured_content da tool; erro → ErroMCP(msg legível)

@asynccontextmanager
async def abrir_cliente(cfg: Config) -> AsyncIterator[ClienteIFood]
    # cfg.ifood_mcp_modo == "demo" → Client(criar_servidor_demo()); "real" → NotImplementedError("etapa 03")
```
Novo em `Config`: `ifood_mcp_modo` (env `IFOOD_MCP_MODO`, padrão `demo`).

### C2. Servidor MCP de demonstração — `backend/app/ifood_mcp/demo_server.py`
`criar_servidor_demo() -> MCPServer`. Tools com **os nomes e campos da doc oficial** (`docs/mcp-ifood.md`):
`getUser`, `listAddresses`, `searchOffers`, `browseOffers`, `getRecommendations`, `getMerchant`, `getItem`,
`createCart`, `addItemToCart`, `getCartDeliveryMethods`, `setCartDelivery`, `listPaymentMethods`,
`setCartPayment`, `getCart`, `submitOrder`, `trackOrder`, `getOrder`.
- Dados em `dados_demo_match.json`: endereço "Demonstração — São Carlos"; ~7 lojas **fictícias** (japonês, hamburgueria,
  poke/saudável, pizzaria, sorveteria, açaí, mercado GROCERIES) com 5–10 itens cada (nome, descrição, preço, tags
  `vegetariano`/`sem_lactose`/`sem_gluten` quando aplicável, `perecivel` para sorvete/açaí), `deliveryTime`, `distance`,
  `rating`, **taxa de entrega por loja (só aparece via `getCartDeliveryMethods`/`getCart`, como no real)**.
- Todo payload tem `"demonstracao": true`. `submitOrder` exige `userConsent: true` (senão erro). `createCart` não é
  idempotente (cria sempre um novo). `trackOrder` avança o status a cada chamada (CONFIRMED → PREPARING → DISPATCHED
  → CONCLUDED) e devolve `agentHints.retryMessage`.
- `resetar_demo()` limpa carrinhos/pedidos.

### C3. Tipos do Match — `backend/app/match/modelos.py` (dataclasses, `asdict` vira JSON)
```python
Desejo(participante_id, nome, texto, orcamento_max: float|None, chips: list[str])
Intencao(participante_id, consultas: list[str], verticais: list[str], restricoes: list[str],
         vontades: list[str], orcamento_max: float|None, perfil: str)   # perfil: barato|rapido|equilibrado|qualidade
Candidato(participante_id, loja_id, loja_nome, item_id, item_nome, preco: float, eta_min: int|None,
          vertical: str, perecivel: bool, nota: float = 0.0, motivo: str = "", viola: list[str] = [])
Pesos(alfa_justica=0.5, beta_custo=0.3, gama_atraso=0.2, delta_lojas=0.15, epsilon_perecivel=0.3)
Combinacao(escolhas: dict[str, Candidato], lojas: list[str], score: float,
           componentes: dict[str, float], taxa_conhecida: bool, explicacao: str = "")
Parte(participante_id, nome, itens: float, taxa: float, desconto: float, total: float)
```

### C4. Otimizador e acerto (código puro, sem I/O)
- `match/otimizador.py`: `pesos_por_perfil(perfis: list[str]) -> Pesos`;
  `otimizar(candidatos: dict[str, list[Candidato]], pesos: Pesos, max_lojas: int = 2,
  taxas: dict[str, float] | None = None, top: int = 3) -> list[Combinacao]`.
  Restrições duras: `viola` não vazio ou `preco > orcamento_max` → fora. Enumeração exaustiva (≤ 8 candidatos por
  pessoa, ≤ 6 pessoas; podar se passar de 50 mil combinações). Score = §4 da 01b; `taxas=None` → custo sem taxa e
  `taxa_conhecida=False`. ε só para `vertical == "RESTAURANT"` e perecível vindo de loja diferente com |ΔETA| > 15 min.
- `match/acerto.py`: `calcular_partes(escolhas: dict[str, Candidato], nomes: dict[str,str],
  taxas: dict[str, float], descontos: dict[str, float]) -> list[Parte]` — taxa da loja dividida **igualmente entre
  quem pediu dela**; desconto proporcional ao valor; arredondar em centavos e **ajustar a sobra para que a soma das
  partes seja exatamente o total** dos carrinhos. `prazo_pagamento_min(n_pessoas) = 10 + 2 * max(0, n - 2)`.
- `match/pix.py`: `gerar_pix_copia_e_cola(chave, nome, cidade, valor, txid="***") -> str` — BR Code estático EMV
  (campos 00, 26 [00 br.gov.bcb.pix, 01 chave], 52 0000, 53 986, 54 valor, 58 BR, 59 nome≤25, 60 cidade≤15,
  62 [05 txid], 63 CRC16-CCITT-FALSE). Sem acento em nome/cidade.

### C5. Motor — `backend/app/match/motor.py` (+ `llm.py`, `interprete.py`, `juiz.py`, `busca.py`)
- `llm.py`: `async def completar_json(cfg, sistema: str, usuario: str) -> dict` usando o provedor do `.env`
  (reaproveitar clientes de `agente/provedores.py`); `mock` → `None` (cada chamador tem fallback determinístico).
- `interprete.interpretar(cfg, desejo) -> Intencao` (LLM com saída JSON; fallback por palavras-chave + chips).
- `busca.buscar(cliente, intencao, endereco) -> list[Candidato]` — `searchOffers` (resultKind ITEM) por consulta,
  `getMerchant`/`getItem` para preço e tags; ≤ 8 por pessoa. Nada de preço fora da resposta da tool.
- `juiz.avaliar(cfg, desejo, candidatos) -> list[Candidato]` — nota 0–1 + motivo curto (LLM; fallback por sobreposição
  de palavras/tags). Alergia/restrição: se o item não tiver tag, `motivo` inclui "pode não estar informado — confirme
  com a loja" (não elimina).
- `motor.rodar_match(cfg, cliente, desejos: list[Desejo]) -> dict` → `{"combinacoes": [...top 3], "intencoes": [...],
  "avisos": [...], "rastro": [...]}` (chama `listAddresses` primeiro).

### C6. Checkout — `backend/app/match/checkout.py`
- `montar_carrinhos(cliente, combinacao, endereco_id) -> list[dict]` por loja: `createCart` → `addItemToCart`* →
  `getCartDeliveryMethods` → `setCartDelivery` → `listPaymentMethods` → `setCartPayment` → `getCart`;
  devolve `{loja_id, loja_nome, cart_id, itens, subtotal, taxa, desconto, total, eta_min}` (valores do `getCart`).
- `enviar_pedidos(cliente, carrinhos, consentimento: bool) -> list[dict]` — `consentimento` falso → erro; antes de
  cada envio `getCart` de novo: total mudou → para e devolve `{"status": "total_mudou"}`; envia em sequência; falha →
  para e devolve o que foi enviado + `{"status": "falhou", "loja_id", "erro"}`.
- `acompanhar(cliente, order_id) -> dict` (`trackOrder`).

### C7. API da sala — `backend/app/rotas_match.py` (incluída em `main.py`; estado em SQLite, tabela própria)
Estados: `coletando → match_pronto → aguardando_pagamentos → pronto_para_enviar → enviado`.
Ações do organizador exigem header `X-Organizador: <token>`.
| Método e rota | Corpo | Resposta |
|---|---|---|
| `POST /api/salas` | `{organizador_nome, chave_pix?}` | `{sala_id, token_organizador, link_convite}` |
| `GET /api/salas/{id}` | — | estado completo: `{estado, demonstracao, participantes[{id,nome,respondeu}], resultado?, carrinhos?, modo_pagamento?, partes?, pagamentos{pid:{forma,status,pix?}}, prazo_fim?, pedidos?, rastro}` |
| `POST /api/salas/{id}/participantes` | `{nome}` | `{participante_id}` (o organizador também é participante) |
| `PUT /api/salas/{id}/participantes/{pid}/desejo` | `{texto, orcamento_max?, chips[]}` | `{ok}` |
| `POST /api/salas/{id}/rodar` 🔒 | — | `resultado` (C5) |
| `POST /api/salas/{id}/escolher` 🔒 | `{combinacao: int, modo_pagamento: "junto"\|"separado"}` | monta carrinhos (C6), calcula partes (C4), define prazo |
| `POST /api/salas/{id}/pagamentos/{pid}` | `{forma: "pix"\|"cartao_simulado"\|"dinheiro"}` | `{status, pix_copia_e_cola?}`; cartão simulado → `pago` com selo |
| `POST /api/salas/{id}/pagamentos/{pid}/recebi` 🔒 | — | marca `pago` |
| `POST /api/salas/{id}/pagamentos/{pid}/resolver` 🔒 | `{acao: "organizador_cobre"\|"remover_itens"}` | recalcula |
| `POST /api/salas/{id}/enviar` 🔒 | `{confirmo: true}` | só se `junto` ou todos `pago` → `pedidos` (C6) |
| `POST /api/salas/{id}/pedidos/{order_id}/atualizar` | — | `trackOrder` |
| `POST /api/demo/resetar` | — | também limpa salas e o demo MCP |

### C8. Frontend — rotas por hash (`#/`, `#/s/{id}`, `#/s/{id}/org`), polling de 2 s em `GET /api/salas/{id}`
- `frontend/src/tipos.ts` espelha C3/C7. `api.ts` ganha funções das rotas C7. Token do organizador e
  "lembrar de mim" (nome + chips) em `localStorage` com try/catch.
- **Visual "dentro do app do iFood"** (pedido da equipe, 17/10; referência com fontes: `docs/design-ifood.md` — tokens, ordem
  da home, fonte Inter no lugar da proprietária): a tela **Início** imita a home do app — topo com
  endereço, abas Início/Restaurantes/Mercados/Bebidas, chips (Ordenar · Pra retirar · Entrega grátis), círculos de
  categorias, banner, "Últimas lojas" e barra inferior (Início · Busca · **Match** · Pedidos · Perfil). O Match entra
  como **banner de destaque** ("Pedir em grupo? Dê um Match") + **aba central na barra inferior**. Paleta vermelha
  (`--marca: #EA1D2C`), cantos arredondados, fonte do sistema. **Sem logo nem fotos do iFood**: ícones/emoji e
  formas CSS; lojas e itens só do demo MCP. Rodapé fixo pequeno: "Protótipo de hackathon · não é o app oficial".
  Só a home é decorativa; os itens da home que não funcionam ficam visualmente desabilitados (regra: botão que não
  funciona não aparece como clicável).
- Telas: **Início** (home estilo iFood + entrada do Match) · **Sala do organizador** (QR + link, lista quem respondeu, botão Rodar) ·
  **Convidado** (≤ 30 s: nome, frase, orçamento, chips) · **Resultado** (quadro por pessoa: item, loja, preço, nota,
  motivo; total; avisos; alternativas 2 e 3) · **Revisão e pagamento** (por loja: subtotal, taxa, total, ETA; aviso
  "N pedidos, N cobranças"; junto/separado; partes; Pix QR, cartão simulado, dinheiro; contador de prazo; recebi) ·
  **Pedidos** (1 cartão por pedido com status) · **Rastro** (lista recolhível das tools MCP). Selo DEMONSTRAÇÃO
  sempre visível quando `demonstracao`.

## Tarefas

| ID | Tarefa | Agente | Modelo | Esforço | Arquivos (só estes) | Depende de | Pronto quando | Status |
|---|---|---|---|---|---|---|---|---|
| 02.1 | MCP de demonstração + cliente MCP com rastro (C1, C2) | dev-mcp-ifood | opus | high | `backend/app/ifood_mcp/` (novo: `__init__.py`, `cliente.py`, `demo_server.py`, `dados_demo_match.json`), `backend/app/config.py`, `.env.example`, `backend/tests/test_ifood_mcp.py` | — | teste percorre a sequência obrigatória inteira via `ClienteIFood` (listAddresses → … → submitOrder → trackOrder); `submitOrder` sem consent falha; rastro registra cada tool | ⬜ |
| 02.2 | Otimizador, acerto, prazo e Pix (C3, C4) | dev-backend | opus | high | `backend/app/match/__init__.py`, `modelos.py`, `otimizador.py`, `acerto.py`, `pix.py`, `backend/tests/test_otimizador.py`, `test_acerto_pix.py` | — | testes: restrição elimina; justiça escolhe combinação sem ninguém com nota baixa; perfil "barato" muda o vencedor; exemplo Thales/Milan da §13 (partes somam o total ao centavo); prazo(2)=10, prazo(4)=14; CRC do Pix válido e campos corretos | ⬜ |
| 02.3 | Motor: LLM JSON, intérprete, busca, juiz (C5) | dev-backend | opus | high | `backend/app/match/llm.py`, `interprete.py`, `busca.py`, `juiz.py`, `motor.py`, `backend/tests/test_motor.py` | 02.1, 02.2 | com `LLM_PROVIDER=mock`, 3 desejos do roteiro (japonês+sorvete / hambúrguer+sorvete / econômico vegetariano) geram top 3 coerente usando só preços do demo MCP; teste com provedor HTTP falso cobre o caminho LLM | ⬜ |
| 02.4 | Checkout com consentimento e acompanhamento (C6) | dev-mcp-ifood | opus | high | `backend/app/match/checkout.py`, `backend/tests/test_checkout.py` | 02.1, 02.2 | testes: sem consentimento não envia; total mudou → para; falha no 2º pedido → 1º enviado e status "falhou" com loja | ⬜ |
| 02.5 | API da sala + estado + pagamentos (C7) | dev-backend | sonnet | high | `backend/app/rotas_match.py`, `backend/app/match/salas.py`, `backend/app/main.py` (só incluir o router e estender o reset), `backend/tests/test_salas.py` | 02.2, 02.3, 02.4 | teste de API faz o fluxo inteiro do "Pronto quando" com TestClient; ações sem token → 403; enviar antes de 100% pago → 409 | ⬜ |
| 02.6 | Front A: rotas, tipos, api, Início, Sala do organizador (QR), Convidado | dev-frontend | sonnet | medium | `frontend/src/App.tsx`, `main.tsx`, `api.ts`, `tipos.ts`, `estilo.css`, `frontend/src/telas/Inicio.tsx`, `Organizador.tsx`, `Convidado.tsx`, `frontend/src/componentes/Selo.tsx`, `Rastro.tsx`, `BarraInferior.tsx`, `frontend/package.json` (+ `qrcode`) | contratos C7/C8 | `npm run build` ok; home estilo iFood com banner e aba Match; criar sala e entrar como convidado funcionam contra o backend | ⬜ |
| 02.7 | Front B: Resultado, Revisão e pagamento, Pedidos | dev-frontend | sonnet | high | `frontend/src/telas/Resultado.tsx`, `Pagamento.tsx`, `Pedidos.tsx`, `frontend/src/componentes/CartaoPessoa.tsx`, `ContadorPrazo.tsx` | 02.6 | build ok; fluxo do "Pronto quando" no navegador 390×780 sem erro no console | ⬜ |
| 02.8 | Pitch v1 + roteiro da demo | pitch-demo | opus | medium | `pitch/index.html`, `docs/roteiro-demo.md`, `docs/pitch-perguntas-banca.md` | — | 8–10 slides com a narrativa (problema → Match → IA indispensável → demo → negócio/LCM/Ailo → internacional → viabilidade), fatos só da 01b com fonte; roteiro de 2 min com as frases dos 3 convidados | ⬜ |
| 02.9 | Revisão da etapa | qa-testador | opus | high | (só leitura) | todas | nada "bloqueia a demo"; Windows: nada exige Docker/bash | ⬜ |

Status: ⬜ a fazer · 🔄 em andamento · ✅ feito · ❌ falhou (ver registro) · ⏸️ adiado

**Por que esses modelos/esforços:**
- 02.2 opus/high (fora do padrão de "endpoint simples"): é o coração do produto e mexe com dinheiro (centavos).
- 02.5 sonnet/high: rota é padrão, mas a máquina de estados e as travas de pagamento pedem mais cuidado.
- 02.7 sonnet/high: telas de dinheiro e prazo; erro visual aqui vira erro de confiança na banca.

**Paralelismo:** Rodada 1: 02.1, 02.2, 02.6, 02.8 · Rodada 2: 02.3, 02.4, 02.7 · Rodada 3: 02.5 · Rodada 4: 02.9 +
integração (engenheiro-chefe: `./iniciar.sh --testes`, build, Playwright no fluxo completo).
(02.6 e 02.7 programam contra os contratos C7/C8; a integração real acontece depois da 02.5.)

## Riscos e plano B
- **Sem chave de LLM:** o fallback `mock` tem de sustentar a demo sozinho → testar sempre com `LLM_PROVIDER=mock`.
- **Enumeração explode com muitas pessoas:** limite de 8 candidatos/pessoa e poda; demo usa 3–4 pessoas.
- **Formato real das tools diferente da doc:** o demo segue a doc; a etapa 03 ajusta o mapeamento no `busca.py` e no
  `checkout.py` (único lugar que lê campos das tools). Registrar diferenças em `docs/feedback-mcp.md`.
- **Pix com chave real de alguém da equipe:** a chave é digitada na tela e fica só no SQLite local; nunca no git.
- **Escopo da etapa grande:** se às 23h30 o front B não fechar, a etapa 03 começa mesmo assim (MCP real é crítico)
  e o front B termina na 04.

## Registro de execução
(o engenheiro anota aqui ao fim de cada rodada: data/hora, tarefas concluídas, commit, problemas)

## Fechamento
(preenchido ao concluir: o que entregou, o que ficou para a próxima etapa, próxima etapa sugerida)
