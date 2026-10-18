# Avaliação do jurado simulado

## Rodada 1 — 17/10 ~22h30 (estado da etapa 03 + plano da etapa 04)

| Pilar | Hoje | Projetada (etapa 04 executada) |
|---|---|---|
| Visão & Originalidade | 6 | 8 (6,5 se o leilão parecer teatro) |
| Arquitetura & Engenharia | 7 | 8,5 com MCP real até `getCart` (7 sem) |
| Design & Experiência | 6,5 | 8,5 |
| Impacto | 4 | 6,5–7 |
| Comunicação & Pitch | 5 | 8 (pitch v2 + 3 ensaios) |
| **Total** | **≈ 28,5/50** | **≈ 39/50** |

### O que mais tira nota → correção (status)
1. MCP real não verificado → diagnóstico no PC + slide com rastro real e ms medidos (🔄 T0, correção do endereço/userLocation feita, T8).
2. Leilão pode parecer teatro → rótulo honesto ("A disputa pelo seu pedido", reprodução), indicador `fonte_fala`,
   decisão própria do agente (agrupar para economizar entrega, preço promocional), nota "substituída por D9" no §8 da 01b (🔄 T1/T2).
3. Impacto sem dado → números com fonte (✅ T5) + formulário aplicado no evento (👥 até 09h).
4. README do produto errado (✅ T4).
5. Pitch com `[preencher]` e Zenon R$ 40 × 50; citar a Rappi (pedido em grupo no BR) num slide comparativo (T14).
6. Demo estoura 2 min → orçamento de tempo no roteiro v2: leilão ≤ 10 s, deck 1 gesto, pagamento comprimido (T14).
7. Fala/motivo podem mentir sem número → validação semântica (restrição só com tag; superlativo só no template) (🔄 T1).
8. "92% de afinidade" sem base → legenda + "bem atendidos" no lugar de "felizes" (🔄 T2).
9. Itens inertes e QR com `localhost` → toast "fora deste protótipo" + `ip_local` em `/api/saude` (🔄 T3 + backend).
10. Patrocinado sem argumento → iFood Ads já é leilão e "dinheiro sozinho não compra posição" (✅ T5); CDC art. 36 (T12).

### Perguntas difíceis que precisam de resposta (T14 → `pitch-perguntas-banca.md`)
- "É agente ou workflow fixo?" — ordem das tools e dinheiro ficam em código de propósito; a IA decide o que buscar, a aderência e o que cada loja oferece.
- "Quem roda o agente do restaurante? A loja consentiu?" — hoje simulamos com o cardápio público do MCP; o protocolo deixa a loja plugar o próprio agente (loja controla a oferta, iFood controla as regras).
- "Por que a loja pagaria Patrocinado se não ganha?" — vitrine em canal de agentes; o iFood vende atenção, não a decisão.
- "Quanto custa o LLM com 8 agentes? Rate limit?" — medir no ensaio (`leilao.medicoes`); fallback cobre 429.
- "Latência no MCP real?" — medir pelo rastro.
- "A Rappi já faz pedido em grupo." — composição por IA, N lojas, vaquinha com trava, lojas disputando.
- "O que é 92%?" — legenda no deck.
- "Escala para 15 pessoas?" — documentar o limite.

### Frase de abertura sugerida
"Sexta à noite, quatro amigos, quatro vontades, um grupo de WhatsApp. Hoje os restaurantes vão disputar o pedido da
nossa turma — e o agente que compra trabalha para nós, não para quem paga anúncio."
Momento: lance "Patrocinado" fala primeiro → perde → vencedoras acendem → "É um Match!" (Thales narra).

## Rodada 2 — 17/10 ~23h (rodada 1 + correções do QA integradas)

| Pilar | Aval. 1 | Agora | Para 9+ |
|---|---|---|---|
| Visão & Originalidade | 6 | 7 | IA real ligada (hoje toda fala é "texto conferido"); Patrocinado que pareça verdadeiro; responder à Prosus/ToqanClaw ("o lado da loja já tem agentes; o Match é onde eles encontram o agente do cliente") |
| Arquitetura & Engenharia | 7 | 7,5 | Match com lojas reais (amostras em `docs/mcp-real/`); IA real; docs sem "em implementação"; frases do pitch iguais ao código |
| Design & Experiência | 6,5 | 8 | Sem jargão ("nota ≥ 0,7"); legenda da afinidade por loja; confete sobre o "82%"; teste com usuário |
| Impacto | 4 | 6 | Pesquisa n ≥ 20 aplicada; medição própria |
| Comunicação & Pitch | 5 | 6,5 | Pitch em ~5 min (12 slides é muito); sem `[preencher]`; 3 ensaios; vídeo gravado |
| **Total** | 28,5 | **35/50** | Projetado com as correções: 41–42; sem MCP real e IA real, teto ~38 |

Entregáveis: proposta 7 · desenho de solução 5 (desatualizado) · racional de UX 7,5 · interface 8 · doc técnico 5,5 · feedback do MCP 7,5.

Correções em andamento (T17d–g): Patrocinado sem vaga garantida no corte de lojas; bebida nunca oferecida a quem
pediu comida (o Poke patrocinado passa, honesto); jargão fora; docs sem "em implementação" + "Avaliar em 5 minutos";
feedback com top 3; pitch em ~5 min com frases iguais ao código ("juntar itens é regra nossa").
👥 Maiores alavancas: chave de IA + 1 Match com IA; diagnóstico `--carrinho` + push de `docs/mcp-real/`; pesquisa;
testar a rede do evento (isolamento de aparelhos → hotspot) e gravar o vídeo; 3 ensaios.
Plano B (MCP real não fecha até 07h): demo no modo demonstração + slide "Real × demonstração" com o que foi
verificado no real; nunca dizer "chamada real" sobre o rastro do demo.
