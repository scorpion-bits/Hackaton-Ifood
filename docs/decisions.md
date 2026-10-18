# Decisões

Formato: data · decisão · por quê · quem aprovou · como reverter.

## 16/10/2026 — Fase 0 (antes do tema)

1. **Stack: FastAPI + SQLite + React/TS (Vite) + servidor MCP em Python (SDK `mcp` 2.x).**
   Por quê: uma linguagem no back reduz risco no Windows sem Docker; o SDK oficial em Python cobre stdio e HTTP.
   Aprovação: stack pedida pela equipe; linguagem do MCP decidida pelo Claude (equipe respondeu "não sei").
   Reverter: o servidor MCP é um arquivo (`backend/app/mcp_server.py`); trocar por TypeScript custa ~2h.

2. **IA gratuita com provedor plugável no `.env`:** `mock` (padrão, offline), `groq`, `gemini`, `ollama`;
   `openai`/`anthropic` opcionais. Por quê: a equipe pediu opção gratuita e a internet do evento é incerta.
   Modelo **não** vem pré-escolhido: `python -m app.agente.listar_modelos` mostra os disponíveis (evita nome inventado).
   Aprovação: equipe ("vamos usar alguma gratuita").

3. **Agente usa as ferramentas pelo protocolo MCP, em processo** (`mcp.Client(MCPServer)`), em vez de subprocesso.
   Por quê: uso real de MCP sem depender de subprocessos/event loop no Windows. O mesmo servidor sobe por stdio/HTTP.
   Aprovação: operacional (Claude).

4. **Ações com dinheiro/preço/pedido = proposta + confirmação humana na tela.** Nenhuma ferramenta MCP executa.
   Por quê: regra de qualidade da equipe e argumento de pitch ("agente confiável").
   Aprovação: regra da equipe (prompt inicial).

5. **iFood em dois modos com a mesma interface: `mock` (demonstração, padrão) e `real`.**
   O modo real só implementa leitura (token, lojas, cardápio); escrita levanta `NaoSuportado` até confirmarmos a doc.
   Por quê: o portal bloqueou leitura automática; não inventar endpoint. Ver `docs/ifood-apis.md`.
   Aprovação: regra da equipe ("nunca suponha endpoint").

6. **Frontend compilado servido pelo próprio FastAPI em :8000.** Um processo, uma URL na demo.
   Aprovação: operacional (Claude).

7. **Ideia: "Match" — composição de pedido por IA para 1 ou N pessoas, 1 ou mais lojas** (17/10 ~19h45).
   Escopo: §7 + §12 + §13 opção 1 de `docs/planos/etapa-01b-match-estrategia.md`. Demo = grupo multi-loja.
   Pagamento: só o organizador entra no iFood; "junto" (1 confirmação, N cobranças) ou "separado" (vaquinha: cada um
   paga a sua parte por Pix real para a chave do organizador, cartão simulado com selo ou dinheiro; o pedido só sai
   com 100% pago). Prazo: 10 min + 2 min por pessoa acima de 2. Descoberta contextual = extra abortável.
   Por quê: maior nota em originalidade e demo; o iFood já tem chat de pedido (Ailo), então o diferencial é a
   composição para grupo com números explicados. Aprovação: equipe. Reverter: o motor serve também 1 pessoa (modo individual).

8. **O Match é cliente MCP com servidor de demonstração local** (mesmos nomes de tools da doc, dados com selo);
   o modo real troca só o transporte (etapa 03). Por quê: desenvolver sem credencial e ter plano B sem internet.
   Aprovação: operacional (Claude). Agente `jurado` criado (aprovado pela equipe).

## 17/10/2026 — Etapa 04

9. **Leilão de agentes por loja (com LLM).** Cada restaurante tem um agente vendedor que só vê o próprio cardápio
   (vindo do MCP) e decide o que oferecer a cada pessoa; o IBits (agente comprador) otimiza entre os lances. Números
   só do MCP; fala com número fora do lance cai no texto determinístico. Por quê: o tema é "Vendendo com Agentes" e
   tira o Match do genérico ("grupo + IA" já existe). Aprovação: equipe. Reverter: `rodar_leilao` é uma etapa do motor.
10. **"Patrocinado" é a única política da loja e só dá visibilidade** (lance aparece primeiro, com rótulo); nunca muda
   nota nem escolha. Modelo de negócio no pitch. Aprovação: equipe delegou ao Claude. Reverter: `politica_lojas.json`.

11. **Rodada 3 — aderência ao regulamento oficial** (17/10 ~23h45). O regulamento pede "um agente que faz pedidos de
   verdade" e "agentes conversacionais e ferramentas determinísticas trabalhando juntos". Decisões: (a) **pedido real
   na conta de teste** — no modo real o checkout nunca escolhe Pix nem cartão online; só forma sem cobrança; envio só
   com `IFOOD_MCP_PERMITIR_ENVIO=true` (C16); (b) **"Ajustar com o IBits"** — conversa depois do resultado que muda o
   pedido de uma pessoa e roda o Match de novo (C14); (c) **"Só eu"** — o mesmo motor para 1 pessoa, sem QR (C15);
   (d) pacote de entrega com os 6 itens em PDF. Aprovação: equipe ("faça tudo que pensar ser melhor"). Reverter:
   cada item é um branch próprio (`match/04-ajustar-*`, `match/04-so-eu`, `match/03-pedido-real`).
12. **Patrocinado sem vaga garantida** (achado do jurado 2): pagar só muda a ordem das falas e o rótulo; o corte de
   lojas ignora o patrocínio. **Bebida nunca é oferta para quem pediu comida.** Aprovação: operacional (Claude).

## 18/10/2026 — Reta final (agente do Zenon no lugar do Milan)

13. **Sem mudar de ideia: "pedido completo" em vez de multicategoria em grupo** (18/10 03h20). Pesquisa de 03h05:
   nenhum app junta IA que compõe o pedido de várias pessoas a partir de frases livres + vaquinha (iFood só testa
   "Combinar pagamentos" com 2 pagantes); entrega com várias lojas já existe em DoorDash/Uber Eats/Wolt e o MCP do
   consumidor não controla logística. Então: cada pessoa recebe tudo o que pediu, na mesma loja quando der (busca com
   `refinements.merchantId`), combo quando for melhor, custo com taxa da busca. **Só eu** passa a aceitar compras de
   mercado/farmácia/pet/bebidas (1 carrinho por loja, sem juntar entregas). Aprovação: Zenon. Reverter: cada item
   (F1–F5) é um commit próprio; F3 (combos) sai se não estiver estável às 08h.
14. **O agente do Zenon assume back, MCP real e integração** enquanto o agente do Milan está sem tokens (18/10 03h22).
   Tudo registrado na Trilha A′ da etapa 05 para o Milan retomar. Aprovação: Zenon.

## Pendentes (👥 decisão humana na abertura)

- Provedor de IA da demo (Groq × Gemini × Ollama) depois de testar com a internet do evento.
