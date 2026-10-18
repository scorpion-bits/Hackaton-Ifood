# Match — pedido em grupo com agentes no MCP do iFood

[![CI](https://github.com/scorpion-bits/Hackaton-Ifood/actions/workflows/ci.yml/badge.svg)](https://github.com/scorpion-bits/Hackaton-Ifood/actions/workflows/ci.yml)

> Protótipo do Hackathon SEMCOMP 29 × iFood ("Vendendo com Agentes"), São Carlos, out/2026.
> **Não é afiliado ao iFood** e não é o app oficial. Dados simulados aparecem com o selo **DEMONSTRAÇÃO**.

## Entregáveis (para a banca)

Tudo o que foi entregue está na pasta **[`entregaveis/`](entregaveis/)** (índice em
[`entregaveis/README.md`](entregaveis/README.md)):

| Arquivo | O que é |
|---|---|
| [`entregaveis/Match-Entregaveis.pdf`](entregaveis/Match-Entregaveis.pdf) | **Os 6 entregáveis num documento só**, na ordem do regulamento, com capa, sumário, diagramas e 24 telas |
| [`entregaveis/Match-Entregaveis.docx`](entregaveis/Match-Entregaveis.docx) | O mesmo documento em Word (editável, com as imagens) |
| [`entregaveis/Match-Pitch.pdf`](entregaveis/Match-Pitch.pdf) | Slides do pitch (12 slides) |

| # | Entregável | Texto-fonte no repositório |
|---|---|---|
| 01 | Proposta de Negócio | [`docs/proposta-negocio.md`](docs/proposta-negocio.md) |
| 02 | Desenho de Solução | [`docs/tecnico.md`](docs/tecnico.md) §1–4 |
| 03 | Racional da Experiência | [`docs/racional-ux.md`](docs/racional-ux.md) |
| 04 | Interface Visual | [`docs/entrega/04-interface.md`](docs/entrega/04-interface.md) + telas em [`docs/entrega/telas/`](docs/entrega/telas/) + o próprio app |
| 05 | Documento Técnico Resumido | [`docs/tecnico.md`](docs/tecnico.md) §5–12 e este README |
| 06 | Feedback sobre os MCPs | [`docs/feedback-mcp.md`](docs/feedback-mcp.md) |

O código está em [`backend/`](backend/) (FastAPI + MCP) e [`frontend/`](frontend/) (React); o pitch em
[`pitch/`](pitch/). O mapa da pasta `docs/` (entregáveis × bastidores da equipe) está em [`docs/README.md`](docs/README.md).

**O que é, em 3 linhas**
1. Cada pessoa escreve o que precisa em uma frase ("japonês e um sorvete, até 45"). A IA compõe **um pedido para 1 ou N
   pessoas**, em **uma ou mais lojas** (até 3), respeitando orçamento e restrições de cada um. Com o botão
   **"Compras"**, o mesmo vale para mercado, farmácia e pet shop ("remédio para dor de cabeça").
2. Cada loja tem um **agente vendedor** que só enxerga o próprio cardápio e disputa o pedido; o **Match** é o
   **agente comprador**, que escolhe a melhor combinação com uma conta justa e explicada (os itens de uma pessoa
   ficam na mesma loja sempre que der).
3. Tudo passa pelo **MCP do iFood (consumidor)**: busca, cardápio, carrinho, entrega, pagamento, pedido e
   acompanhamento. Preço e taxa só vêm das tools do MCP; nada sai sem o "ok" do organizador.

Detalhes e estado de cada parte: [`docs/tecnico.md`](docs/tecnico.md).

## Avaliar em 5 minutos

**O que é:** um app web em que um grupo diz o que quer comer em frases livres; agentes das lojas disputam o pedido,
o Match escolhe a melhor combinação (até 3 lojas) e o organizador monta os carrinhos pelo MCP do iFood e dá o ok.
Sem chave de IA e sem internet, tudo roda no modo demonstração (selo DEMONSTRAÇÃO).

**Rodar (3 comandos)** — precisa de Python 3.11+ e Node 20+:
```bash
git clone https://github.com/scorpion-bits/Hackaton-Ifood && cd Hackaton-Ifood
./iniciar.sh            # Windows: iniciar.bat (duplo clique)
# abra http://localhost:8000
```

**Testar sozinho (1 aba normal + 3 abas anônimas):**
1. Aba normal = organizador: "Fazer um match" → crie a sala e copie o link dos convidados.
2. Em cada aba anônima, abra o link, ponha um nome e uma frase:
   - aba 1: `Japonês e um sorvete, até 45`
   - aba 2: `Hambúrguer e sorvete, até 50`
   - aba 3: `Algo barato e vegetariano, até 25`
3. Opcional, na aba do organizador ("Também quero pedir"): `feijoada completa, até 60` — mostra o aviso
   "Não achei feijoada completa…" em vez de inventar um prato (com essa 4ª frase o resultado muda).
4. "Rodar Match" → "Como o Match avaliou cada loja" → "Ver o pedido" ("O pedido do grupo") → opcional:
   "Ajustar com o Match" (`troca o sorvete por açaí`) → "Confirmar pedido" → "Cada um paga a sua parte (vaquinha)"
   → pagamentos → "Deslize para enviar" → abra "Como a IA chegou aqui" (o rastro das tools MCP).
5. **Só eu:** "Fazer um match" → "Só eu" → `hambúrguer e uma batata frita` (os dois na mesma loja). Ligue
   **"Compras"** e peça `dipirona e protetor solar` (farmácia); sem "Compras", `arroz, feijão e bife` vira prato.

Resultado esperado das 3 primeiras frases e falas da disputa: [`docs/roteiro-demo.md`](docs/roteiro-demo.md).
Os 6 entregáveis estão na [pasta `entregaveis/`](#entregáveis-para-a-banca).

**Rede:** para usar celulares de verdade, eles precisam alcançar o PC (`http://<IP-do-PC>:8000`). Se o Wi-Fi
isolar os aparelhos (comum em rede de evento), use o hotspot do celular ou as abas anônimas no próprio PC.

## Como funciona (fluxo da demo)

```
Organizador (PC, único logado no iFood)          Convidados (celular, sem login)
  1. Cria a sala ─────── QR + link ──────────────▶ 2. Nome + frase + orçamento + chips
  3. "Rodar Match"
       listAddresses → searchOffers → getMerchant (MCP)
       IA interpreta → regras do pedido (Compras, mesma loja) → IA dá nota a cada item
       → leilão: 1 agente vendedor por loja (falas validadas) → otimizador (justiça, custo, prazo, nº de lojas)
  4. Avaliação ao vivo ("Como o Match avaliou cada loja") → "O pedido do grupo" com a melhor combinação;
     mudar = "Ajustar com o Match" em frase livre
  5. "Confirmar pedido" → pagamento único ou vaquinha (se uma loja não aceitar pedido, o Match monta a próxima opção)
       1 carrinho por loja: createCart → addItemToCart → getCartDeliveryMethods → setCartDelivery
                            → listPaymentMethods → setCartPayment → getCart (taxa real)
  6. Separado: partes exatas ao centavo ───────────▶ 7. Pix (para a chave do organizador),
     prazo: 10 min + 2 min por pessoa acima de 2         cartão simulado (só demo) ou dinheiro
  8. Com 100% pago, confirma → getCart de novo → submitOrder(userConsent: true) → trackOrder
  Rastro: cada chamada de tool aparece na tela, com o nome da documentação oficial.
```

O roteiro de 2 minutos com as falas e o resultado esperado está em [`docs/roteiro-demo.md`](docs/roteiro-demo.md).

## Rodar no Windows (sem Docker)

1. Instale **Python 3.11 a 3.14** ([python.org](https://www.python.org/downloads/), marque *Add python.exe to PATH*)
   e **Node.js 20+** ([nodejs.org](https://nodejs.org/)). Confira no PowerShell: `python --version` e `node --version`.
2. Baixe o projeto (`git clone` ou ZIP) e abra a pasta.
3. Dê **duplo clique em `iniciar.bat`**. Ou, no PowerShell, dentro da pasta:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1          # app em http://localhost:8000
   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 -Dev     # backend com reload + Vite em :5173
   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 -Testes  # testes do backend + tipos do frontend
   ```
   Na primeira vez o script cria `backend\.venv`, instala as dependências, copia `.env.example` para `.env`
   (tudo offline) e compila o frontend. Leva alguns minutos.
4. O navegador abre em **http://localhost:8000** quando o servidor responde. Para parar: `Ctrl+C`.

**Celulares dos convidados:** na mesma rede Wi-Fi, use o endereço que o script imprime (`http://<IP-do-PC>:8000`).
Na sala do organizador, preencha **"Base do link"** com esse IP (ex. `192.168.x.x`; evite `172.x`) para o QR
apontar para o PC. Se o Windows perguntar, permita o acesso em rede privada.

**Se der erro:** `pip install` falhou → confira a versão do Python e rode de novo; porta 8000 ocupada → feche o
outro processo; "Preencha IFOOD_MCP_CLIENT_ID" com o `.env` preenchido → reinicie o app e veja se não há a mesma
variável repetida e vazia mais abaixo no `.env` (vale a última).

## Rodar no Linux / macOS

```bash
./iniciar.sh            # instala o que faltar, compila o frontend e sobe http://localhost:8000
./iniciar.sh --dev      # backend com reload (8000) + Vite com hot reload (5173)
./iniciar.sh --testes   # pytest do backend + typecheck do frontend
```

## Modos (no `.env`)

| Variável | Valores | Para quê |
|---|---|---|
| `IFOOD_MCP_MODO` | `demo` (padrão) · `real` | `demo`: servidor MCP de demonstração dentro do app, com os **mesmos nomes de tools** da doc oficial e lojas fictícias (selo DEMONSTRAÇÃO); funciona sem internet. `real`: MCP oficial `https://consumer-mcp.ifood.com.br/marketplace` com login OAuth. |
| `LLM_PROVIDER` | `mock` (padrão) · `groq` · `gemini` · `ollama` · `openai` · `anthropic` | `mock` não usa IA nem chave: tudo cai no modo determinístico e a demo inteira roda. Os outros usam o modelo do `.env`. |
| `LLM_MODEL` | nome do modelo | Não chute: rode `python -m app.agente.listar_modelos` dentro de `backend/` (com o venv). |
| `LLM_API_KEY` | chave | Ou `GROQ_API_KEY` / `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. |
| `MATCH_LEILAO` | `on` (padrão) · `off` | `off` pula o leilão dos agentes das lojas e vai direto ao otimizador. |
| `IFOOD_MCP_PERMITIR_ENVIO` | `false` (padrão) · `true` | Só no modo real: com `false`, `submitOrder` fica travado e o pedido para no carrinho (a API responde 409 explicando). |

Com qualquer provedor, se a IA falhar ou demorar (limite de 8 s por chamada), o motor segue com o modo
determinístico. A IA nunca escreve preço, taxa ou prazo.

## Conectar o iFood real (conta de teste)

1. No [Portal do Desenvolvedor do MCP](https://mcp-developer.ifood.com.br/pt-BR) ("Faça login"), abra o agente
   aprovado e copie o **client id** e o **client secret**.
2. Cadastre a Redirect URL **exatamente** `http://localhost:8000/oauth/callback` (sem curinga).
3. No `.env` (que nunca vai para o git):
   ```
   IFOOD_MCP_MODO=real
   IFOOD_MCP_CLIENT_ID=...
   IFOOD_MCP_CLIENT_SECRET=...
   IFOOD_MCP_REDIRECT=http://localhost:8000/oauth/callback
   ```
4. Reinicie o app e toque em **"Conectar iFood"** na tela inicial (ou abra `http://localhost:8000/oauth/login`).
   Entre com uma **conta de teste** do Portal (e-mail `@test.ifood.com.br` + código gerado em "Gerar código").
5. O login volta para o app (`/#/conectado`). Os tokens ficam em `backend/.tokens_ifood.json`, que está no
   `.gitignore`, e são renovados sozinhos 5 min antes de expirar.

O login só funciona no PC onde o app roda (o retorno vai para o `localhost` dele).

> **Nunca pague o Pix de um pedido de teste: não há reembolso.** Na conta de teste o pedido não vai ao restaurante.
> O cartão simulado da vaquinha só existe no modo `demo`.

**Diagnóstico do MCP real** (só leitura, nunca chama `submitOrder`; grava amostras sanitizadas em `docs/mcp-real/`):
```bash
cd backend
.venv/bin/python -m app.ifood_mcp.diagnostico              # Windows: .venv\Scripts\python -m app.ifood_mcp.diagnostico
.venv/bin/python -m app.ifood_mcp.diagnostico --carrinho   # também cria 2 carrinhos, sem enviar pedido
```

## Testes

```bash
./iniciar.sh --testes                     # ou iniciar.ps1 -Testes no Windows
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run typecheck
```
Hoje: **565 testes** no backend (pytest), todos passando (18/10, 11h; o comando acima mostra o número exato).
Interface: `bash docs/testes/e2e/rodar.sh` (7 casos no navegador). Bateria de frases: `python -m app.match.bateria`. Os testes zeram as credenciais e isolam o arquivo de
tokens; nenhum teste chama o iFood real.

## Estrutura

```
backend/
  app/
    main.py              FastAPI: rotas, serve frontend/dist em :8000
    config.py            lê o .env (IFOOD_MCP_*, LLM_*)
    rotas_match.py       API da sala do Match (/api/salas/...)
    rotas_oauth.py       /oauth/login, /oauth/callback, /api/ifood/status, /api/ifood/sair
    match/               motor do Match
      motor.py           listAddresses → interpretar → regras → buscar → julgar → mesma loja → leilão → otimizar
      regras.py          regras do pedido lidas de regras_pedido.json (botão Compras, peso da mesma loja)
      interprete.py      frase → slots (consultas, restrições, orçamento, perfil, quantidades); IA + regras
      leilao.py          1 agente vendedor por loja; validação das falas; fallback por template
      politica_lojas.json  loja patrocinada do modo demo (só visibilidade)
      busca.py           searchOffers / getMerchant / browseOffers → candidatos (único leitor da descoberta)
      juiz.py            nota 0–1 + motivo por item; IA + regras
      otimizador.py      combinações com justiça, custo, prazo, nº de lojas (até 3)
      checkout.py        carrinhos, envio com consentimento, trackOrder (único leitor do carrinho/pedido)
      acerto.py          partes por pessoa em centavos; prazo da vaquinha
      pix.py             Pix copia e cola (BR Code estático, CRC16)
      salas.py           estado da sala em SQLite (máquina de estados)
      llm.py             chamada de IA com saída JSON e limite de tempo
    ifood_mcp/
      cliente.py         cliente MCP (demo em processo | real via Streamable HTTP) com rastro;
                         adapta argumentos ao input_schema (userLocation); trava o submitOrder real
      demo_server.py     servidor MCP de demonstração (17 tools com os nomes da doc)
      oauth.py           Authorization Code + PKCE S256 + client secret; tokens fora do git
      diagnostico.py     amostras sanitizadas do MCP real
    agente/provedores.py provedores de IA (mock, OpenAI-compatível, Anthropic)
  tests/                 pytest
frontend/src/
  App.tsx, api.ts, tipos.ts, estilo.css
  telas/                 Inicio, SoEu, Organizador, Convidado, Leilao, Resultado, Pagamento, Pedidos
  componentes/           Selo, Rastro, StatusIfood, CartaoPessoa, ContadorPrazo, BarraInferior, Deslizar…
    leilao/              visual das lojas, Ajustar com o Match, utilitários
pitch/                   slides (index.html); npm run pdf gera pitch/pitch.pdf
entregaveis/             PDF e DOCX dos 6 entregáveis + PDF do pitch (o que a banca lê)
docs/                    textos-fonte dos entregáveis, testes, planos e decisões (mapa em docs/README.md)
iniciar.bat · iniciar.ps1 · iniciar.sh · .env.example
```

Decisões e o porquê de cada uma: [`docs/decisions.md`](docs/decisions.md). Resumo do MCP do consumidor:
[`docs/mcp-ifood.md`](docs/mcp-ifood.md).

## Regras do projeto

- Preço, taxa, prazo e disponibilidade só vêm de resposta de tool do MCP; a IA nunca inventa número.
- `submitOrder` só com `userConsent: true`, depois da confirmação humana na tela (e 100% pago no modo separado).
- Segredos e tokens só no `.env` e em `backend/.tokens_ifood.json` (ambos fora do git).
- Dado simulado sempre com o selo DEMONSTRAÇÃO.

Equipe: Thales Miguel Hajes, Milan Bahrami, Zenon e Antonio.
