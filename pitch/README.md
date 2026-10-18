# Pitch do Match (máximo 5 min)

Um arquivo só (`index.html`), sem internet e sem instalar nada: **dois cliques no `index.html`** (Edge/Chrome).
PDF de reserva: `pitch.pdf` (claro). Telas do app: `img/app/` (visual atual com a logo Match):
- `01`–`08`: história da persona Ana no **modo demonstração** (selo "demonstração" visível), **sem foto colada** (antes as
  fotos de amostra caíam em prato errado; agora só `FOTOS_AMOSTRA=1` as liga).
- `real-avaliacao`, `real-pedido`, `real-prontos`: o app no **MCP real** (conta de teste, endereço em SP, IA Gemini),
  18/10 ~09h: logos, fotos, preços e carrinho do iFood. Aparecem no clique da prova do slide "Como funciona".

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

## Roteiro (persona, ~4:50)
| # | Slide | Até | Ideia |
|---|---|---|---|
| 1 | Capa | 0:15 | "Ninguém mais vira o gerente do pedido." |
| 2 | Essa é a Ana | 0:45 | Sexta 21h, república, o grupo do WhatsApp (as mensagens aparecem sozinhas) |
| 3 | As dores | 1:20 | 4 cliques: ninguém decide · cada um quer uma coisa · cada bolso um limite · a conta fica com ela; + iFood 65 mi clientes / 180 mi pedidos (fonte no rodapé) |
| 4 | Virada | 1:30 | "E se cada um só dissesse o que quer?" |
| 5 | 1 · Cada um fala | 1:55 | QR, sem login, frase livre |
| 6 | 2 · O IBits monta | 2:30 | 1 clique troca a tela: avaliação das lojas → pedido do grupo |
| 7 | 3 · Ajustar | 2:50 | "troca o sorvete de Bruno por açaí" |
| 8 | 4 · Cada um paga | 3:20 | divisão ao centavo, Pix para a Ana, só sai com 100% pago |
| 9 | Como funciona | 3:55 | IA conversa · código calcula · MCP executa; 1 clique: 3 telas do app no MCP real (Big Mac + McFritas na mesma loja) + conta R$ 50,98 |
| 10 | Quem ganha | 4:30 | turma, lojas, iFood; 2 cliques: piloto e feedback do MCP |
| 11 | Fechamento | 4:50 | "A Ana voltou a ser só mais uma amiga com fome." |

**Vídeo:** não tem. As telas no celular contam a demo sem risco de o iFood cair no palco. Se a banca pedir, a demo ao
vivo fica para as perguntas (`docs/roteiro-demo.md`). **Números:** só os do iFood com fonte (rodapé do slide 3) e o
carrinho real de `docs/mcp-real/bug25-whopper-carrinho.json`. A pesquisa com usuários não teve respostas: não citar %.

## Regerar
- Telas: `bash pitch/scripts/capturar_telas.sh` (Linux/container; sobe o app em modo demonstração e grava `img/app/`).
- Telas do MCP real: com o app já rodando no modo real, `REAL=1 SAIDA=<pasta> node pitch/scripts/capturar_telas.cjs`
  (Playwright em `NODE_PATH`); as 3 `real-*` vieram do fluxo Só eu "um hambúrguer e uma batata frita".
- PDF: `cd pitch && npm install && npm run pdf` (escuro: `node exportar-pdf.mjs escuro`).
