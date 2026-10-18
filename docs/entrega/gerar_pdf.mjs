// Gera docs/entrega/Match-Entregaveis.pdf com os 6 entregáveis do hackathon.
//
// Como rodar (Linux, macOS ou Windows; precisa de Node 20+):
//   cd docs/entrega
//   npm i
//   node gerar_pdf.mjs
// Navegador: usa CHROME_PATH se definido; senão o Chromium do Playwright; senão o Edge/Chrome instalado.
// Se nada funcionar: `npx playwright install chromium` (uma vez).
//
// Saídas: Match-Entregaveis.pdf, diagramas/diagrama-N.png (Mermaid renderizado) e _build/ (HTML intermediário).
// Reexecutável: lê os Markdown de origem a cada execução; não edita nenhum doc de origem.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { Marked } from 'marked';
import { chromium } from 'playwright';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, '..', '..');
const BUILD = path.join(AQUI, '_build');
const DIAGRAMAS = path.join(AQUI, 'diagramas');
const SAIDA = path.join(AQUI, 'Match-Entregaveis.pdf');
const REPO_WEB = 'https://github.com/scorpion-bits/Hackaton-Ifood/blob/main/';
const MERMAID_JS = path.join(AQUI, 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');
const CSS = fs.readFileSync(path.join(AQUI, 'estilo-impressao.css'), 'utf8');

const TITULO = 'Match — pedido em grupo com agentes no MCP do iFood';
const EVENTO = 'Hackathon SEMCOMP × iFood 2026 · "Vendendo com Agentes" · São Carlos';
const EQUIPE = 'Thales Miguel Hajes · Milan · Zenon · Antonio';
const DATA = '18 de outubro de 2026';
const AVISO = 'Protótipo de hackathon · não afiliado ao iFood. Dados simulados aparecem com o selo DEMONSTRAÇÃO.';

const TELAS_CAPA = ['docs/entrega/telas/01-inicio.png', 'docs/entrega/telas/07-ajustar-conversa.png', 'docs/entrega/telas/10-confira.png'];

const ler = (rel) => fs.readFileSync(path.join(RAIZ, rel), 'utf8').replace(/\r\n/g, '\n');
const tirarH1 = (md) => md.replace(/^\s*# [^\n]*\n/, '');
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Documento técnico: 02 = visão, componentes, sequência e fluxo; 05 = do leilão em diante.
function dividirTecnico() {
  const md = tirarH1(ler('docs/tecnico.md'));
  const corte = md.search(/^## 5\. /m);
  if (corte < 0) {
    console.warn('AVISO: não achei "## 5." em docs/tecnico.md; o 02 e o 05 recebem o documento inteiro.');
    return [md, md];
  }
  const nota05 = '> Continuação de `docs/tecnico.md` (seções 5 a 12). Visão geral, componentes, sequência e fluxo do motor ' +
    'estão no entregável 02.\n\n';
  return [md.slice(0, corte), nota05 + md.slice(corte)];
}

const [tec02, tec05] = dividirTecnico();

const ENTREGAVEIS = [
  { n: '01', titulo: 'Proposta de Negócio', fonte: 'docs/proposta-negocio.md',
    desc: 'Problema, público, solução, valor para o iFood, modelo de negócio, métricas e viabilidade.',
    md: tirarH1(ler('docs/proposta-negocio.md')), base: 'docs' },
  { n: '02', titulo: 'Desenho de Solução', fonte: 'docs/tecnico.md §1–4',
    desc: 'Divisão IA × código × MCP, componentes, sequência completa de um Match em grupo e fluxo do motor.',
    md: tec02, base: 'docs' },
  { n: '03', titulo: 'Racional da Experiência', fonte: 'docs/racional-ux.md',
    desc: 'Princípios, jornadas do organizador e do convidado, leilão e deck, confiança, acessibilidade e estados.',
    md: tirarH1(ler('docs/racional-ux.md')), base: 'docs' },
  { n: '04', titulo: 'Interface Visual', fonte: 'docs/entrega/04-interface.md · docs/entrega/telas/',
    desc: 'Linguagem visual, tokens e galeria com as capturas reais das telas do protótipo.',
    md: tirarH1(ler('docs/entrega/04-interface.md')), base: 'docs/entrega' },
  { n: '05', titulo: 'Documento Técnico Resumido', fonte: 'docs/tecnico.md §5–12',
    desc: 'Leilão de agentes, otimizador, acerto em centavos, estados da sala, segurança, uso do MCP, limites e testes.',
    md: tec05, base: 'docs' },
  { n: '06', titulo: 'Feedback sobre os MCPs', fonte: 'docs/feedback-mcp.md',
    desc: 'Top 3 problemas por gravidade, o que funcionou bem e o registro de dores durante o evento.',
    md: tirarH1(ler('docs/feedback-mcp.md')), base: 'docs' },
];

// ---------- Markdown -> HTML ----------
function converter(md, baseRel) {
  const marked = new Marked({ gfm: true });
  marked.use({
    walkTokens(tok) {
      if (tok.type === 'link' && tok.href && !/^([a-z]+:|#|mailto:)/i.test(tok.href)) {
        const alvo = path.posix.normalize(path.posix.join(baseRel, tok.href));
        tok.href = REPO_WEB + alvo.replace(/^\.\//, '');
      }
    },
    renderer: {
      code({ text, lang }) {
        if ((lang || '').trim() === 'mermaid') {
          // Em sequenceDiagram o ';' separa comandos e quebra o parser (e o GitHub); vira a entidade #59;
          if (/^\s*sequenceDiagram/.test(text)) text = text.replace(/;/g, '#59;');
          const linhas = text.split('\n').length;
          return `<div class="diagrama${linhas > 30 ? ' alto' : ''}"><pre class="mermaid">${esc(text)}</pre></div>\n`;
        }
        return false; // padrão do marked
      },
    },
  });
  let html = marked.parse(md);
  // Imagens/HTML cru com caminho relativo -> file:// absoluto
  html = html.replace(/(<img[^>]*\ssrc=")(?![a-z]+:)([^"]+)"/gi, (_, a, src) =>
    `${a}${pathToFileURL(path.join(RAIZ, baseRel, src)).href}"`);
  return html;
}

const pagina = (corpo) => `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>${CSS}</style></head><body>${corpo}</body></html>`;

function htmlEntregavel(e) {
  return pagina(`<header class="entregavel-cabecalho"><div class="num">${e.n}</div>
<h1>${esc(e.titulo)}</h1><div class="fonte">Fonte no repositório: ${esc(e.fonte)}</div></header>
${converter(e.md, e.base)}`);
}

function htmlCapaESumario(paginas) {
  const itens = ENTREGAVEIS.map((e, i) => `<li><span class="n">${e.n}</span>
<span class="tx"><span class="t">${esc(e.titulo)}</span><span class="d">${esc(e.desc)}</span></span>
<span class="p">p. ${paginas[i]}</span></li>`).join('\n');
  return pagina(`<section class="capa">
<div><div class="faixa"></div>
<div class="wordmark">♥ match</div>
<h1>Match — <span>pedido em grupo</span> com agentes no MCP do iFood</h1>
<div class="sub">${esc(EVENTO)}</div>
<div class="telas-capa">${TELAS_CAPA.filter((f) => fs.existsSync(path.join(RAIZ, f)))
    .map((f) => `<img src="${pathToFileURL(path.join(RAIZ, f)).href}" alt="">`).join('')}</div></div>
<div class="bloco"><div><b>Entregáveis</b> 01 a 06 do regulamento</div>
<div><b>Equipe</b> ${esc(EQUIPE)}</div>
<div><b>Data</b> ${esc(DATA)}</div>
<div><b>Repositório</b> github.com/scorpion-bits/Hackaton-Ifood</div></div>
<div class="aviso">${esc(AVISO)}</div>
</section>
<section class="sumario"><h2>Sumário</h2><ol>${itens}</ol>
<div class="extra">
<p><b>Pitch:</b> pitch/pitch.pdf · <b>Avaliar em 5 minutos:</b> README.md · <b>Índice para a banca:</b> docs/ENTREGA.md</p>
<p>Os textos deste PDF são gerados dos arquivos Markdown do repositório (docs/entrega/gerar_pdf.mjs). Em caso de
diferença, vale o repositório.</p></div></section>`);
}

// ---------- Navegador ----------
async function abrirNavegador() {
  const tentativas = [];
  if (process.env.CHROME_PATH) tentativas.push({ executablePath: process.env.CHROME_PATH });
  const local = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
  if (fs.existsSync(local)) tentativas.push({ executablePath: local });
  tentativas.push({}, { channel: 'msedge' }, { channel: 'chrome' });
  let ultimo;
  for (const t of tentativas) {
    try { return await chromium.launch(t); } catch (err) { ultimo = err; }
  }
  throw new Error('Nenhum navegador abriu. Rode `npx playwright install chromium` ou defina CHROME_PATH.\n' + ultimo);
}

let contDiagrama = 0;
async function renderPdf(browser, nome, html, rodape) {
  fs.writeFileSync(path.join(BUILD, nome + '.html'), html);
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
  await page.goto(pathToFileURL(path.join(BUILD, nome + '.html')).href, { waitUntil: 'load' });
  if (await page.$('pre.mermaid')) {
    await page.addScriptTag({ path: MERMAID_JS });
    await page.evaluate(async () => {
      window.mermaid.initialize({
        startOnLoad: false, theme: 'base', securityLevel: 'strict',
        themeVariables: {
          fontFamily: 'Inter, Segoe UI, Arial, sans-serif', fontSize: '14px',
          primaryColor: '#FDECEE', primaryBorderColor: '#EA1D2C', primaryTextColor: '#1A1A1A',
          lineColor: '#6F6F6F', secondaryColor: '#F7F7F7', tertiaryColor: '#FFFFFF',
          actorBkg: '#FDECEE', actorBorder: '#EA1D2C', noteBkgColor: '#FFF4D6', noteBorderColor: '#E0B100',
        },
        flowchart: { useMaxWidth: true }, sequence: { useMaxWidth: true }, state: { useMaxWidth: true },
      });
      // Diagrama muito largo (flowchart LR) fica ilegível em A4 retrato: renderiza de novo de cima para baixo.
      const proporcao = (svg) => {
        const vb = (svg.match(/viewBox="([^"]+)"/) || [])[1];
        if (!vb) return 1;
        const [, , w, h] = vb.split(/\s+/).map(Number);
        return w / h;
      };
      try {
        let i = 0;
        for (const pre of Array.from(document.querySelectorAll('pre.mermaid'))) {
          const fonte = pre.textContent;
          let { svg } = await window.mermaid.render(`dg${i++}`, fonte);
          const lr = /^\s*(flowchart|graph)\s+LR\b/m;
          if (lr.test(fonte) && proporcao(svg) > 1.8) {
            // escala final em A4 (área útil ~680 × 775 px); só troca se o TB ficar bem maior que o LR
            const escala = (sv) => {
              const vb = (sv.match(/viewBox="([^"]+)"/) || [])[1].split(/\s+/).map(Number);
              return Math.min(680 / vb[2], 775 / vb[3]);
            };
            const tb = (await window.mermaid.render(`dg${i++}`, fonte.replace(lr, (m, k) => `${k} TB`))).svg;
            if (escala(tb) > 1.3 * escala(svg)) svg = tb;
          }
          const div = document.createElement('div');
          div.innerHTML = svg;
          pre.replaceWith(div.firstElementChild);
        }
        return null;
      } catch (err) {
        return String(err && (err.message || err.str) || err) + ' ' + JSON.stringify(err).slice(0, 500);
      }
    }).then((erro) => { if (erro) throw new Error('Mermaid falhou: ' + erro); });
    for (const el of await page.$$('.diagrama')) {
      contDiagrama += 1;
      await el.screenshot({ path: path.join(DIAGRAMAS, `diagrama-${contDiagrama}.png`) });
    }
  }
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete));
  const buf = await page.pdf({
    format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: Boolean(rodape),
    headerTemplate: '<span></span>',
    footerTemplate: rodape
      ? `<div style="width:100%;font-family:Inter,Segoe UI,Arial,sans-serif;font-size:7.5pt;color:#8a8a8a;padding:0 15mm;">
         <span style="color:#EA1D2C;font-weight:700">Match</span> · ${esc(rodape)}</div>`
      : '<span></span>',
  });
  await page.close();
  return buf;
}

async function main() {
  fs.rmSync(BUILD, { recursive: true, force: true });
  fs.rmSync(DIAGRAMAS, { recursive: true, force: true });
  fs.mkdirSync(BUILD, { recursive: true });
  fs.mkdirSync(DIAGRAMAS, { recursive: true });

  const browser = await abrirNavegador();
  try {
    const partes = [];
    for (const e of ENTREGAVEIS) {
      const buf = await renderPdf(browser, e.n, htmlEntregavel(e), `${e.n} · ${e.titulo}`);
      const doc = await PDFDocument.load(buf);
      partes.push({ e, buf, paginas: doc.getPageCount() });
    }
    // Capa (1 pág.) + sumário (1 pág.) -> o 01 começa na página 3
    const inicio = [];
    let p = 3;
    for (const parte of partes) { inicio.push(p); p += parte.paginas; }
    const capaBuf = await renderPdf(browser, '00-capa', htmlCapaESumario(inicio), null);

    const final = await PDFDocument.create();
    final.setTitle(TITULO);
    final.setAuthor(EQUIPE);
    final.setSubject('Entregáveis 01–06 · Hackathon SEMCOMP × iFood 2026');
    final.setLanguage('pt-BR');
    for (const buf of [capaBuf, ...partes.map((x) => x.buf)]) {
      const src = await PDFDocument.load(buf);
      const pags = await final.copyPages(src, src.getPageIndices());
      pags.forEach((pg) => final.addPage(pg));
    }
    const capaPags = (await PDFDocument.load(capaBuf)).getPageCount();
    if (capaPags !== 2) console.warn(`AVISO: capa + sumário ocupam ${capaPags} páginas (esperado 2); números do sumário ficam deslocados.`);

    // Número de página no rodapé (exceto capa)
    const fonte = await final.embedFont(StandardFonts.Helvetica);
    const total = final.getPageCount();
    final.getPages().forEach((pg, i) => {
      if (i === 0) return;
      const txt = `${i + 1} / ${total}`;
      const w = fonte.widthOfTextAtSize(txt, 7.5);
      // rodapé do Chromium fica ~ 8 mm da borda; alinhar à direita da margem de 15 mm
      pg.drawText(txt, { x: pg.getWidth() - 42.5 - w, y: 25, size: 7.5, font: fonte, color: rgb(0.54, 0.54, 0.54) });
    });
    fs.writeFileSync(SAIDA, await final.save());
    console.log(`OK: ${path.relative(RAIZ, SAIDA)} · ${total} páginas · ${contDiagrama} diagramas em ${path.relative(RAIZ, DIAGRAMAS)}/`);
    partes.forEach((x, i) => console.log(`  ${x.e.n} ${x.e.titulo}: p. ${inicio[i]} (${x.paginas} pág.)`));
  } finally {
    await browser.close();
  }
}

main().catch((err) => { console.error(err); process.exit(1); });
