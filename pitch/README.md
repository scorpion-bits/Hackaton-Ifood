# Pitch do Match (máximo 5 min)

Um arquivo só (`index.html`), sem internet e sem instalar nada: **dois cliques no `index.html`** (Edge/Chrome).
PDF de reserva: `pitch.pdf` (claro). Telas do app: `img/app/` (visual atual com a logo Match):
- `01`–`08`: história da persona Ana no **modo demonstração** (selo "demonstração" visível), **sem foto colada** (antes as
  fotos de amostra caíam em prato errado; agora só `FOTOS_AMOSTRA=1` as liga).
- `real-avaliacao`, `real-pedido`, `real-prontos`: o app no **MCP real** (conta de teste, endereço em SP, IA Gemini),
  18/10 ~09h: logos, fotos, preços e carrinho do iFood. Aparecem no clique da prova do slide "Como funciona".

## Visual e som
- Sem emojis: ícones de traço em vermelho iFood, fotos reais de pratos do iFood (`img/pratos/`, do CDN do iFood
  via amostras do MCP em `docs/mcp-real/`) e a logo do iFood (`img/ifood-logo.svg`, Wikimedia Commons
  "File:IFood_logo.svg"; embutida no HTML para seguir a cor do slide) na capa, no "Como funciona", no "Quem ganha" e
  no fechamento ("match × iFood").
- **Vinheta "iFood!"** (`audio/vinheta-ifood.mp3`, 1,8 s): toca ao **avançar** para o slide que tem
  `data-som="vinheta"` (hoje o Fechamento). Só na janela principal (a do apresentador fica muda); voltar não toca.
  Para mudar de slide, mova o atributo `data-som="vinheta"` para outra `<section>`. Confira o volume do PC antes.

## Teclas
| Tecla | Ação |
|---|---|
| → / espaço / clique na direita | avança (alguns slides revelam um item por clique) |
| ← / clique na esquerda | volta |
| **F** | tela cheia |
| **S** | janela do apresentador: fala do slide, próximo slide e cronômetro (verde → amarelo em 4:30 → vermelho em 5:00) |
| **T** | tema claro ↔ escuro (o padrão segue o sistema; no projetor que "lava" as cores, use o escuro) |
| **R** | zera o cronômetro (ensaio) |

O cronômetro começa no **primeiro avanço**. A janela do apresentador segue a principal sozinha (mesmo navegador).

## Roteiro (dor geral, grupo como caso principal, ~3:30 + a vinheta)
| # | Slide | Até | Ideia |
|---|---|---|---|
| 1 | Capa | 0:10 | "Diga o que você precisa. O Match resolve no iFood." |
| 2 | A dor | 0:35 | Você sabe o que precisa, mas não o que buscar: 3 cenas (23h dor de cabeça · a turma com fome · a lista do mercado) + iFood 65 mi clientes / 180 mi pedidos (fonte no rodapé) |
| 3 | O grupo | 0:55 | O caso mais difícil: a Ana, sexta 21h, o grupo do WhatsApp (as mensagens aparecem sozinhas) → "virou a gerente do pedido" |
| 4 | Virada | 1:02 | "E se você só dissesse o que precisa?" |
| 5 | Sozinho | 1:25 | "um remédio para dor de cabeça" → 8 farmácias reais do iFood, analgésico sem receita (MCP real). "Não receita nada: acha o que ela pediu e ela confirma." |
| 6 | 1 · Cada um fala | 1:38 | Agora o grupo: QR, sem login, frase livre |
| 7 | 2 · O Match monta | 1:58 | 1 clique troca a tela: avaliação das lojas → pedido do grupo |
| 8 | 3 · Ajustar | 2:10 | "troca o sorvete de Bruno por açaí" |
| 9 | 4 · Cada um paga | 2:26 | divisão ao centavo, Pix para a Ana, só sai com 100% pago |
| 10 | Como funciona | 2:52 | IA conversa · código calcula · MCP executa; 1 clique: 3 telas do app no MCP real (hambúrguer + McFritas no mesmo McDonald's) + conta R$ 50,98 |
| 11 | Quem ganha | 3:12 | quem pede (sozinho ou em grupo), as lojas (restaurante, farmácia, mercado e pet), o iFood; 2 cliques: piloto e feedback do MCP |
| 12 | Fechamento | 3:30 | vinheta "iFood!" ao entrar; "A Ana voltou a ser só mais uma amiga com fome. Diga o que você precisa: o Match acha, monta e divide pelo iFood." |

**Vídeo:** não tem. As telas no celular contam a demo sem risco de o iFood cair no palco. Se a banca pedir, a demo ao
vivo fica para as perguntas (`docs/roteiro-demo.md`). **Números:** só os do iFood com fonte (rodapé do slide 3) e o
carrinho real de `docs/mcp-real/bug25-whopper-carrinho.json`. A pesquisa com usuários não teve respostas: não citar %.

## Regerar
- Telas: `bash pitch/scripts/capturar_telas.sh` (Linux/container; sobe o app em modo demonstração e grava `img/app/`).
- Telas do MCP real: com o app já rodando no modo real, `REAL=1 SAIDA=<pasta> node pitch/scripts/capturar_telas.cjs`
  (Playwright em `NODE_PATH`); as 3 `real-*` vieram do fluxo Só eu "um hambúrguer e uma batata frita".
- PDF: `cd pitch && npm install && npm run pdf` (escuro: `node exportar-pdf.mjs escuro`).
