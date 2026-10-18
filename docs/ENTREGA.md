# Entrega — Match (Hackathon SEMCOMP × iFood 2026)

**Match — pedido em grupo com agentes no MCP do iFood.** Protótipo de hackathon, não afiliado ao iFood.
Equipe: Thales Miguel Hajes · Milan · Zenon · Antonio.

| Para a banca | Onde |
|---|---|
| **PDF único com os 6 entregáveis** (capa, sumário, diagramas e telas) | [`docs/entrega/Match-Entregaveis.pdf`](entrega/Match-Entregaveis.pdf) |
| Pitch (slides) | [`pitch/pitch.pdf`](../pitch/pitch.pdf) |
| Avaliar em 5 minutos (rodar com 3 comandos e testar sozinho) | [`README.md` → "Avaliar em 5 minutos"](../README.md#avaliar-em-5-minutos) |
| Vídeo da demo | [link do vídeo — preencher] |

## Os 6 entregáveis, na ordem do regulamento

**01 · Proposta de Negócio** — problema, público, solução, diferenciais frente a Uber Eats, DoorDash, Rappi e Ailo,
valor para o iFood (Patrocinado no leilão), modelo de negócio, métricas e viabilidade.
Fonte: [`docs/proposta-negocio.md`](proposta-negocio.md).

**02 · Desenho de Solução** — divisão IA × código × MCP, diagrama de componentes, sequência completa de um Match em
grupo (todas as tools do MCP na ordem) e fluxo do motor.
Fonte: [`docs/tecnico.md`](tecnico.md) §1–4.

**03 · Racional da Experiência** — princípios de design, jornadas do organizador e do convidado, por que leilão e
deck, confiança e segurança, identidade visual, acessibilidade, erros e estados.
Fonte: [`docs/racional-ux.md`](racional-ux.md).

**04 · Interface Visual** — linguagem visual e tokens, mais a galeria com 8 capturas reais do app (início, sala,
convidado, disputa das lojas, fim da rodada, "É um Match!", opção escolhida, confira antes do ok).
Fonte: [`docs/entrega/04-interface.md`](entrega/04-interface.md), imagens em [`pitch/img/`](../pitch/img/),
tokens em [`docs/design-ifood.md`](design-ifood.md). O app roda localmente (ver "Avaliar em 5 minutos").

**05 · Documento Técnico Resumido** — leilão de agentes por loja, otimizador, acerto em centavos e vaquinha,
máquina de estados da sala, segurança, uso correto do MCP, limites conhecidos e testes.
Fonte: [`docs/tecnico.md`](tecnico.md) §5–12; como rodar em [`README.md`](../README.md).

**06 · Feedback sobre os MCPs** — top 3 problemas por gravidade (ex.: `userLocation` sem documentação, 23 × 24
tools), o que funcionou bem e o registro de cada dor anotada durante o evento.
Fonte: [`docs/feedback-mcp.md`](feedback-mcp.md).

## Gerar o PDF de novo

O PDF sai dos Markdown acima; quem mudar um texto deve gerar de novo antes da submissão (Node 20+):

```bash
cd docs/entrega
npm i                 # uma vez (marked, mermaid, pdf-lib e playwright com versão fixa)
node gerar_pdf.mjs    # escreve Match-Entregaveis.pdf e diagramas/diagrama-N.png
```

Navegador: usa `CHROME_PATH` se definido, senão o Chromium do Playwright, senão o Edge ou o Chrome instalados
(no Windows o Edge já basta). Se nenhum abrir: `npx playwright install chromium`. Os diagramas Mermaid são
renderizados localmente (sem CDN). O HTML intermediário fica em `docs/entrega/_build/` (fora do git).
