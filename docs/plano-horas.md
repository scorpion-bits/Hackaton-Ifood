# Plano de horas — 17/10 12h30 → 18/10 18h00 (~29h30)

> 👥 Confirmar na abertura: prazo de entrega, formato do pitch (tempo, vídeo?) e critérios.
> O ICMC fala em 27h; se a entrega for antes das 18h, puxe tudo proporcionalmente.
> Equipe: **Thales** (pitch, front, testes) · **Milan** (IA, back, design) · **Zenon** (testes, pitch) · **Antonio** (testes).

| Quando | Checkpoint | Thales | Milan | Zenon | Antonio | Claude 🤖 |
|---|---|---|---|---|---|---|
| **17/10 12h30–13h30** | Enunciado entendido | anota regras e critérios, fala com mentor | testa chave Groq/Gemini na rede do evento | cria conta no portal iFood (se liberado) | roda `iniciar.bat` no PC da apresentação | resumo do desafio + 4–5 ideias + notas (Fase 4) |
| **13h30–14h30** | 👥 **Ideia aprovada** | decide com a equipe | decide | decide | decide | MVP mínimo + plano detalhado |
| **14h30–20h00** | Fatia vertical: agente → MCP → API iFood → tela | telas do fluxo principal | prompt, ferramentas MCP | roteiro da demo de 2 min | testa cada commit no Windows | implementa ferramentas e fluxo |
| **20h00** | ✅ **Demo de ponta a ponta funcionando** (mesmo feia) | | | | | |
| **20h00–23h00** | Pitch começa + dados de demo | rascunho dos slides | ajusta qualidade das respostas | roteiro e texto do pitch | casos de erro (sem estoque, orçamento) | testes + seed de demo |
| **23h00–03h00** | Polimento do fluxo da demo (não do resto) | visual | robustez do agente | ensaio 1 | testa tudo de novo | bugs |
| **03h00–08h00** | Revezamento de sono (2 acordados) | | | | | |
| **18/10 08h00–12h00** | Gravar plano B + pitch completo | ensaio 2 | grava vídeo de tela | revisa números/fontes | testa na rede do evento | exporta PDF, atualiza README |
| **12h00–14h00** | Ensaios cronometrados | ensaio 3 | | | | só bugfix |
| **16h00** | 🧊 **Congelamento de código** (2h antes) | | | | | |
| **16h00–18h00** | Entrega + ensaio final | apresenta | suporte técnico | cronometra | botão "Recarregar demo" pronto | checklist de entrega |

Regras: demo estável > funcionalidade nova. Botão que não funciona sai da tela. Commit pequeno e frequente.
