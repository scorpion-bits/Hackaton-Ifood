# Entregáveis — Match (Hackathon SEMCOMP × iFood 2026)

**Match — diga o que você precisa; o Match resolve no iFood.** Um agente de IA que opera o MCP do iFood (consumidor)
para montar o pedido de 1 ou N pessoas, em até 3 lojas, da frase livre ao carrinho. Protótipo de hackathon, não
afiliado ao iFood. Equipe: Thales Miguel Hajes · Milan Bahrami · Zenon · Antonio.

## Os arquivos desta pasta

| Arquivo | O que é |
|---|---|
| **[`Match-Entregaveis.pdf`](Match-Entregaveis.pdf)** | Os 6 entregáveis num documento só, na ordem do regulamento: capa, sumário com páginas, diagramas e 24 telas reais |
| [`Match-Entregaveis.docx`](Match-Entregaveis.docx) | O mesmo conteúdo em Word, com as imagens (para editar ou copiar trechos) |
| [`Match-Pitch.pdf`](Match-Pitch.pdf) | Slides do pitch (12 slides, ~3:30 de fala) |
| Slides interativos (com a vinheta) | [`pitch/index.html`](../pitch/index.html): abrir no navegador; mesmo conteúdo do PDF |
| Diagramas | [`docs/entrega/diagramas/`](../docs/entrega/diagramas/) (PNG, gerados dos blocos Mermaid do `docs/tecnico.md`) |
| Telas | [`docs/entrega/telas/`](../docs/entrega/telas/) (24 PNG: modo demonstração e MCP real) |
| Código | [`backend/`](../backend/) (FastAPI, cliente MCP, motor do Match) e [`frontend/`](../frontend/) (React) |

## Onde está cada entregável

| # | Entregável (regulamento) | No PDF/DOCX | Texto-fonte no repositório |
|---|---|---|---|
| 01 | **Proposta de Negócio** — problema, proposta de valor, público, valor para o iFood, modelo e métricas | seção 01 | [`docs/proposta-negocio.md`](../docs/proposta-negocio.md) |
| 02 | **Desenho de Solução** — fluxo geral, IA × código × MCP, componentes, sequência das tools | seção 02 | [`docs/tecnico.md`](../docs/tecnico.md) §1–4 |
| 03 | **Racional da Experiência** — princípios, jornadas, botão Compras, um pedido só, confiança, acessibilidade | seção 03 | [`docs/racional-ux.md`](../docs/racional-ux.md) |
| 04 | **Interface Visual** — linguagem visual, tokens e 24 telas (grupo, só eu, compras e MCP real) | seção 04 | [`docs/entrega/04-interface.md`](../docs/entrega/04-interface.md), imagens em [`docs/entrega/telas/`](../docs/entrega/telas/); o app roda com `iniciar.bat` / `./iniciar.sh` |
| 05 | **Documento Técnico Resumido** — leilão de agentes, otimizador, acerto, estados, segurança, uso do MCP, testes | seção 05 | [`docs/tecnico.md`](../docs/tecnico.md) §5–12 e o [`README.md`](../README.md) |
| 06 | **Feedback sobre os MCPs** — top 4 dores por gravidade, o que funcionou e o registro feito durante o evento | seção 06 | [`docs/feedback-mcp.md`](../docs/feedback-mcp.md) |

**Rodar o app em 5 minutos:** [`README.md` → "Avaliar em 5 minutos"](../README.md#avaliar-em-5-minutos) (sem chave de IA
e sem internet, tudo roda no modo demonstração).

## Gerar de novo (depois de mudar um texto)

```bash
cd pitch && npm i && npm run pdf && cd ..          # slides → pitch/pitch.pdf
cd docs/entrega && npm i && node gerar_pdf.mjs     # → entregaveis/Match-Entregaveis.pdf (+ copia o pitch)
python gerar_docx.py                               # → entregaveis/Match-Entregaveis.docx (pandoc + python-docx)
bash capturar_telas.sh                             # opcional: refaz as telas 01–19 no modo demonstração
```
