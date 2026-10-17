# Design da home iFood (referência para o protótipo "Match")

Pesquisa feita em 17/10/2026. Regra: só o que tem fonte; o resto fica "NÃO VERIFICADO". O portal e vários sites do iFood
bloqueiam leitura automática (403), então nada foi conferido no app real. **Antes do pitch, 👥 abrir o app e comparar.**

## 1. Design system do iFood
| Afirmação | Status | Fonte |
|---|---|---|
| O iFood tem design system interno: iFDL (linguagem/tokens) + iFDS (componentes React, Android...) | Confirmado | [tech.ifood.com.br, IFDS (24/02/2026)](https://tech.ifood.com.br/en/front-end/ifds-por-dentro-dos-padroes-de-engenharia-e-arquitetura-de-componentes-do-ifood-design-system/) |
| Tokens/Figma/pacotes são públicos | NÃO VERIFICADO (artigo não cita pacote publicado; GitHub `ifood` só mostra o fork `buck`) | [github.com/ifood](https://github.com/ifood) |
| O nome "Pastel" é do design system do iFood | NÃO VERIFICADO (nenhuma fonte; outro site cita "Pomodoro DS", não oficial) | [designmd.app](https://designmd.app/brands/ifood) |
| Tokens são CSS vars `--ifdl-*` (ex.: `--ifdl-color-brand-primary-default`, `--ifdl-spacing-scale-12`, `--ifdl-border-radius-re`, `--ifdl-font-family-ifood-body`) | Confirmado (nomes; valores não publicados) | IFDS, link acima |
| Tokens organizados em `tokens/{brand}/{theme}/` com Style Dictionary | Confirmado via busca (página deu 403 na leitura) | [Medium iFood Tech, Style Dictionary](https://medium.com/ifood-tech/design-system-style-dictionary-at-scale-58d06a5f022a) |
| Vermelho principal `#EA1D2C` | Confirmado como "o vermelho do iFood hoje" (aparece em exemplo de código do blog técnico) | IFDS, link acima |
| Demais hex (`#C8101E` escuro, `#FF3341` claro, `#FFB800` amarelo, `#50A773` verde, cinzas `#1A1A1A/#6F6F6F/#DCDCDC/#F7F7F7`) | NÃO OFICIAL: extração automática de site de terceiros, sem afiliação | [designmd.app/brands/ifood (05/07/2026)](https://designmd.app/brands/ifood) |
| Paleta inclui vermelho + amarelo, verde, laranja, rosa | Análise de terceiro (sem hex) | [Medium, Marina Oliveira](https://medium.com/@marinaoliveirasm/ifood-e-rappi-an%C3%A1lise-comparativa-de-identidades-visuais-aplicadas-%C3%A0-interfaces-digitais-23d8f2c342a4) |
| Fonte própria "iFood" (Display/Text/Condensed) e "iFood RC", autor Fabio Haag Type | NÃO VERIFICADO (só o site de terceiros; nada na busca sobre Haag + iFood). O token `font-family-ifood-body` confirma que existe fonte própria. | designmd.app; IFDS |
| Fonte própria é livre | NÃO VERIFICADO. Tratar como proprietária. |
| Raios 4/8/12/16/24/pill; espaços 4-8-12-16-24-32-48 | NÃO OFICIAL (designmd.app). Exemplo oficial só mostra `padding:16px; border-radius:8px`. | IFDS |
| Ícones | NÃO VERIFICADO (sem biblioteca pública achada) |

Alternativa gratuita: **Inter** (listada no Google Fonts: [fonts.google.com/specimen/Inter](https://fonts.google.com/specimen/Inter); licença OFL NÃO VERIFICADA nesta sessão, confirmar na página). "Parecida com a do iFood" é julgamento nosso, não fato. Ícones: Lucide ou Material Symbols (conferir licença na hora).

## 2. Estrutura da home do app (o que a fonte sustenta)
| Item | Status | Fonte |
|---|---|---|
| Topo: endereço de entrega, toque troca o endereço; lista de lojas depende dele | Confirmado | [iFood institucional, delivery perto de mim](https://institucional.ifood.com.br/clientes/delivery-perto-de-mim-agora/) |
| Grade/linha rolável de ícones de verticais: Restaurantes, Mercados, Farmácias, Pet Shops, Bebidas, Shopping; **Turbo** (raio vermelho) rolando para a esquerda | Confirmado (ordem na tela NÃO VERIFICADA) | mesma fonte; [iFood além da comida (04/06/2026)](https://institucional.ifood.com.br/clientes/ifood-e-mais-que-comida/) |
| Destaques/banners grandes no centro; atalhos sazonais ("Retrospectiva 2025" ícone "25" + banner) | Confirmado | [Olhar Digital (11/12/2025)](https://olhardigital.com.br/2025/12/11/dicas-e-tutoriais/o-que-voce-mais-pediu-no-ifood-em-2025-veja-como-fazer-retrospectiva/); [Tecnoblog (2023)](https://tecnoblog.net/noticias/ate-o-ifood-tem-seu-wrapped-saiba-como-acessar-a-retrospectiva/) (403 na leitura, resumo da busca) |
| Área de ofertas/cupons | Confirmado (posição NÃO VERIFICADA) | iFood além da comida |
| Busca (ícone/barra) | NÃO VERIFICADO onde fica; app tem "busca e navegação por categorias" | [App Store iFood](https://apps.apple.com/br/app/ifood-pedir-delivery-em-casa/id483017239) |
| Seções "Últimas lojas", "Famosos no iFood", "Lojas" | NÃO VERIFICADO (nenhuma fonte achada) |
| Card de loja: o usuário compara avaliação, tipo de comida, distância, tempo e taxa; filtro "entrega grátis" | Confirmado (campos, não o layout) | [iFood institucional, delivery perto de mim](https://institucional.ifood.com.br/clientes/delivery-perto-de-mim-agora/) |
| Barra inferior: **Pedidos** (inferior direito, citada em 2 páginas); **Perfil** (inferior direito, ajuda oficial) | Confirmado, mas as duas fontes se contradizem sobre qual é o último item | [Como funciona a entrega](https://institucional.ifood.com.br/ajuda/como-funciona-a-entrega-do-ifood/); [Suporte](https://institucional.ifood.com.br/clientes/suporte-do-ifood/); [Conta e cadastro](https://institucional.ifood.com.br/ajuda/conta-e-cadastro-ifood/) |
| Rótulos "Início" e "Busca" | NÃO VERIFICADO (nenhuma página oficial cita). Adotar Início · Busca · Pedidos · Perfil como convenção nossa. |
| Clube iFood fica em Perfil > Clube iFood | Confirmado | [Passageiro de Primeira](https://passageirodeprimeira.com/?p=484058) |
| Redesign da home em 2025-2026 | NÃO VERIFICADO (nenhuma notícia achada) |

## 3. IA e grupo dentro do iFood
- **Ailo** é o agente de IA do iFood: WhatsApp (texto/voz, Pix) e **app próprio separado** "Ailo - Powered by iFood" (login pela conta iFood). Nenhuma fonte indica atalho dentro do app iFood: [Mobile Time (28/08/2026)](https://www.mobiletime.com.br/noticias/28/08/2026/ifood-pagamento-agentico/), [Mobile Time (16/07/2026)](https://www.mobiletime.com.br/noticias/16/07/2026/ailo-ifood-whatsapp-flui/), [App Store Ailo](https://apps.apple.com/br/app/ailo-powered-by-ifood/id6757810480?l=en-GB). Entrada dentro do app iFood: **NÃO VERIFICADO**.
- **Pedido em grupo no iFood:** NÃO VERIFICADO (nenhum anúncio achado). Existe teste de **"Combinar pagamentos"** (2 formas no mesmo pedido, atalho 50%, só para grupo restrito, sem Pix duplicado): [Tecnoblog (06/2026)](https://tecnoblog.net/noticias/ifood-testa-opcao-de-dividir-pagamento-com-outra-pessoa/). Argumento de pitch: o iFood só divide *pagamento*, não *composição*.

## 4. Concorrentes: pedido em grupo
| Padrão | Uber Eats | DoorDash | Rappi |
|---|---|---|---|
| Criar na página da loja + gerar link | Sim, "Invite guests" | Sim, "Create a group order" | Sim, link |
| Convidado sem conta | Depende: sem conta se o host paga; logado se paga a própria parte | Sim, sem conta | Não, exige app |
| Prazo | Opcional, envio manual ou automático | Entra até o checkout (até 24h) | NÃO VERIFICADO |
| Limite por pessoa | Opcional | Definido pelo host antes de iniciar | NÃO VERIFICADO |
| Travar carrinho | "Lock order & continue" | Host fecha e finaliza | Host paga ao fim |
| Pagamento | Host paga tudo ou cada um paga a sua | Host (um frete só) | Host paga |
Fontes: [Uber Eats help](https://help.uber.com/en/ubereats/stores/article/how-to-place-a-group-order?nodeId=3b5e94fc-e5c4-4c74-ac47-61b9fb709d0f), [Uber, FAQ grupos grandes](https://help.uber.com/en/ubereats/restaurants/article/large-group-orders-faq?nodeId=5dfdd2a2-ac78-4dd8-81c4-0500ca29cc12), [DoorDash FAQ](https://help.doordash.com/en-us/business/article/group-orders-faq), [ENTER.CO (09/11/2023)](https://www.enter.co/?p=547407).
Vale imitar: link no WhatsApp, lista de quem já entrou, contagem regressiva, host trava e fecha, remover pessoa/item antes de fechar.

## 5. Recomendações para o protótipo
**Tokens CSS** (vermelho oficial; resto = escolha nossa, não afirmar que é do iFood):
```css
:root{
  --brand:#EA1D2C;          /* confirmado (blog técnico iFood) */
  --brand-dark:#C8101E;     /* NÃO OFICIAL (designmd.app) */
  --brand-soft:#FDECEE;     /* nosso */
  --ink:#1A1A1A; --ink-2:#6F6F6F; --line:#DCDCDC; --bg:#F7F7F7; --card:#FFF;
  --ok:#50A773; --star:#FFB800;
  --r-sm:8px; --r-md:12px; --r-lg:16px; --r-pill:999px;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-6:24px;
  --font:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
}
```
**Ordem dos componentes:** 1) topo com "Entregar em" + endereço; 2) busca; 3) linha rolável de verticais (Restaurantes, Mercados, Farmácias, Pet, Bebidas, Shopping + **Match** com selo "novo"); 4) banner grande do Match (carrossel de destaques); 5) faixa de cupons; 6) seção de lojas com cards (nota ★, categoria, distância, tempo, taxa/"Grátis"); 7) barra inferior Início · Busca · **Match** (central, destacado) · Pedidos · Perfil. A aba central é decisão de design nossa: o iFood real não tem esse item (NÃO VERIFICADO), por isso o selo "protótipo".
**Cuidados de marca:** sem logo, sem fotos, sem fonte proprietária; usar nome "Match" e wordmark próprio; ilustrações/emoji neutros; rodapé fixo discreto "Protótipo de hackathon, não afiliado ao iFood"; dados simulados com selo "demonstração".
**Match em si:** copiar o fluxo Uber/DoorDash (link, quem entrou, prazo, trava) e diferenciar com IA que compõe o pedido por frase livre e vaquinha com prazo.
