# Comércio com Agentes — Hackathon iFood × SEMCOMP 29

Esqueleto do projeto: um agente de IA que **vende** (lado do lojista) e **compra** (lado do cliente) usando
ferramentas expostas por um **servidor MCP** que fala com as **APIs do iFood**. Toda ação com dinheiro, preço ou
pedido é só uma **proposta**; a pessoa confirma na tela.

```
Pessoa ─▶ Frontend (React) ─▶ FastAPI ─▶ Agente (LLM) ─▶ Servidor MCP ─▶ Cliente iFood (mock | real)
                                              ▲                                   │
                                              └──── confirmação humana ◀──────────┘
```

> Modo padrão: **tudo offline** (`LLM_PROVIDER=mock`, `IFOOD_MODE=mock`). Os dados são fictícios e aparecem com o
> selo **DEMONSTRAÇÃO**.

## Rodar no Windows (sem Docker) — passo a passo

1. Instale **Python 3.11+** ([python.org](https://www.python.org/downloads/), marque *Add python.exe to PATH*) e
   **Node.js 20+** ([nodejs.org](https://nodejs.org/)). Confira no PowerShell:
   ```powershell
   python --version
   node --version
   ```
2. Baixe o projeto (`git clone` ou ZIP) e abra a pasta.
3. Dê **duplo clique em `iniciar.bat`**. Ou, no PowerShell, dentro da pasta:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
   ```
   Na primeira vez ele cria `backend\.venv`, instala dependências, cria o `.env` e compila o frontend (alguns minutos).
4. O navegador abre em **http://localhost:8000**. Para parar: `Ctrl+C` na janela.

Outros modos: `.\iniciar.ps1 -Dev` (hot reload em http://localhost:5173) · `.\iniciar.ps1 -Testes`.

**Se o `pip install` falhar no Python 3.14** (algum pacote sem versão pronta para 3.14): instale o Python 3.13,
apague `backend\.venv` e rode de novo com `py -3.13 -m venv backend\.venv` antes do script.

## Rodar no Linux/macOS

```bash
./iniciar.sh            # http://localhost:8000
./iniciar.sh --dev      # backend com reload + Vite em :5173
./iniciar.sh --testes   # pytest + checagem de tipos
```

## Ligar uma IA gratuita

Edite o `.env` (criado na primeira execução):

| Provedor | `.env` | Chave |
|---|---|---|
| Groq | `LLM_PROVIDER=groq` + `GROQ_API_KEY=...` | https://console.groq.com/keys |
| Gemini | `LLM_PROVIDER=gemini` + `GEMINI_API_KEY=...` | https://aistudio.google.com/apikey |
| Ollama (local) | `LLM_PROVIDER=ollama` | sem chave; instale https://ollama.com e baixe um modelo |

Depois escolha o modelo **sem chutar o nome**:
```bash
cd backend
.venv/bin/python -m app.agente.listar_modelos          # Linux
.venv\Scripts\python.exe -m app.agente.listar_modelos  # Windows
```
Coloque em `LLM_MODEL=` um modelo que suporte *tool calling* e reinicie. Sem internet? Volte para `LLM_PROVIDER=mock`.

## Ligar o iFood real

`IFOOD_MODE=real` + `IFOOD_CLIENT_ID` + `IFOOD_CLIENT_SECRET` (Portal do Desenvolvedor iFood → Meus Apps).
Teste sem alterar nada: `python -m app.ifood.testar_real` dentro de `backend/`. Hoje o modo real só **lê**
(lojas e cardápio). Veja o que está verificado em [`docs/ifood-apis.md`](docs/ifood-apis.md).

## Estrutura

| Caminho | O que é |
|---|---|
| `backend/app/main.py` | API FastAPI e servidor do frontend compilado |
| `backend/app/agente/` | laço do agente e provedores de LLM (mock, Groq/Gemini/Ollama/OpenAI, Anthropic) |
| `backend/app/mcp_server.py` | servidor MCP: ferramentas `vendedor_*` e `comprador_*` |
| `backend/app/acoes.py` | propostas pendentes e confirmação humana |
| `backend/app/ifood/` | cliente iFood: `mock.py` (demonstração) e `real.py` (Merchant API) |
| `backend/mcp_stdio.py` | servidor MCP sozinho, para Claude Desktop / MCP Inspector ([guia](docs/mcp.md)) |
| `frontend/` | React + TypeScript (Vite), mobile first |
| `pitch/` | slides Reveal.js locais; `npm run pdf` gera `pitch/pitch.pdf` (versionado) |
| `docs/` | APIs do iFood, MCP, decisões, plano de horas, checklist de entrega |

## API

| Método | Rota | Para quê |
|---|---|---|
| GET | `/api/saude` | provedor de IA, modo iFood, se é demonstração |
| POST | `/api/chat` | `{mensagem, lado: "comprador"\|"vendedor", conversa_id?}` → texto, passos, ações |
| GET | `/api/acoes?status=pendente` | ações propostas |
| POST | `/api/acoes/{id}/confirmar` · `/recusar` | decisão humana |
| POST | `/api/demo/resetar` | volta os dados de demonstração ao início |

## Pitch

```bash
cd pitch && npm install
# abrir index.html no navegador para apresentar
npm run pdf   # usa Edge/Chrome já instalado; gera pitch/pitch.pdf → commitar
```
