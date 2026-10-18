// Smoke de interface do Match (390×780, modo demonstração), com verificação automática: sai com código 1 se algo falhar.
// Rodar com `bash docs/testes/e2e/rodar.sh` (sobe o app em modo demo, instala o Playwright fora do repositório e roda).
// Verifica: texto esperado na tela, nada de "undefined"/"NaN"/"[object", sem rolagem horizontal, sem erro de página,
// console ou HTTP inesperado (404/409/422 são respostas legíveis do app). Capturas em $E2E_SAIDA (padrão: /tmp/e2e).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const URL = process.env.E2E_URL || 'http://localhost:8000/';
const SAIDA = process.env.E2E_SAIDA || '/tmp/e2e';
const CHROME = process.env.E2E_CHROME || '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
fs.mkdirSync(SAIDA, { recursive: true });

const falhas = [];
const ok = [];

function vigiar(page, nome) {
  page.on('pageerror', (e) => falhas.push(`[${nome}] erro na página: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error' && !/status of (404|409|422)/.test(m.text())) falhas.push(`[${nome}] console: ${m.text()}`); });
  page.on('response', (r) => { if (r.status() >= 500) falhas.push(`[${nome}] HTTP ${r.status()} ${r.request().method()} ${r.url()}`); });
}

async function checar(page, nome, esperados) {
  const r = await page.evaluate(() => ({
    texto: document.body.innerText,
    largura: document.documentElement.scrollWidth,
    tela: document.documentElement.clientWidth,
  }));
  for (const ruim of ['undefined', 'NaN', '[object']) if (r.texto.includes(ruim)) falhas.push(`[${nome}] texto "${ruim}" na tela`);
  if (r.largura > r.tela + 1) falhas.push(`[${nome}] rolagem horizontal (${r.largura}px > ${r.tela}px)`);
  for (const e of esperados) if (!r.texto.includes(e)) falhas.push(`[${nome}] faltou "${e}" na tela`);
  await page.screenshot({ path: path.join(SAIDA, `${nome}.png`) });
  return r.texto;
}

async function verPedido(page) {
  await page.waitForSelector('.ld-resultado, .ld-sala', { timeout: 40000 });
  if (await page.locator('.ld-sala').count()) await page.getByRole('button', { name: /Ver o pedido/ }).click({ timeout: 40000 });
  await page.waitForSelector('.ld-resultado', { timeout: 15000 });
  await page.waitForTimeout(400);
}

const SOLO = [
  ['solo-pizza-coca', 'uma pizza e uma coca', ['Forno da Praça Pizzaria', 'Refrigerante 2 L', 'com taxa']],
  ['solo-combo', 'hambúrguer com batata e refri', ['Combo smash + batata + refri', 'Combo com']],
  ['solo-farmacia', 'dipirona e protetor solar', ['Drogaria Bem Estar', 'Dipirona', 'Protetor solar']],
  ['solo-mercado', 'preciso fazer compras: arroz, feijão e detergente', ['Mercadinho Bairro Feliz', 'Arroz', 'Detergente']],
  // T16 / bug 40: prato feito vai para restaurante; "Onde pedir? Restaurante" faz "arroz e feijão" virar PF
  ['solo-marmita', 'arroz, feijão, salada e guarnição', ['Tempero de Casa']],
  ['solo-onde-restaurante', 'arroz e feijão', ['Tempero de Casa'], 'Restaurante'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: fs.existsSync(CHROME) ? CHROME : undefined, args: ['--no-sandbox'] });
  const novo = async (nome) => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 780 }, locale: 'pt-BR' });
    const p = await ctx.newPage();
    vigiar(p, nome);
    return p;
  };
  for (const [nome, frase, esperados, onde] of SOLO) {
    const antes = falhas.length;
    try {
      const p = await novo(nome);
      await p.goto(URL);
      await p.getByRole('button', { name: 'Fazer um match' }).click();
      await p.getByRole('button', { name: /Só eu/ }).click();
      await p.getByLabel('Seu nome').fill('Teste');
      await p.locator('#soeu-texto').fill(frase);
      if (onde) await p.getByRole('radio', { name: onde }).click();
      await p.getByRole('button', { name: 'Encontrar meu pedido' }).click();
      await verPedido(p);
      await checar(p, nome, esperados);
      if (nome === 'solo-farmacia') {  // vai até o carrinho (1 pessoa monta direto)
        await p.getByRole('button', { name: 'Confirmar pedido' }).click();
        await p.waitForSelector('text=Confira antes do ok', { timeout: 20000 });
        await checar(p, `${nome}-carrinho`, ['Drogaria Bem Estar', 'Taxa de entrega']);
      }
    } catch (e) {
      falhas.push(`[${nome}] não completou: ${String(e.message).split('\n')[0]}`);
    }
    if (falhas.length === antes) ok.push(nome);
  }

  // grupo: organizador + 2 convidados pelo link; convidada vê só a parte dela; organizador monta e envia (demo)
  const antes = falhas.length;
  try {
    const org = await novo('grupo-org');
    await org.goto(URL);
    await org.getByRole('button', { name: 'Fazer um match' }).click();
    await org.getByRole('button', { name: /Em grupo/ }).click();
    await org.getByLabel(/Seu nome/).fill('Org');
    await org.getByRole('button', { name: 'Criar sala' }).click();
    await org.waitForSelector('.qrcard');
    const sala = (await org.evaluate(() => location.hash)).split('/')[2];
    const convidados = [];
    for (const [nome, frase] of [['Ana', 'pizza e um refri'], ['Bia', 'hambúrguer com batata e refri']]) {
      const p = await novo(`grupo-${nome}`);
      await p.goto(`${URL}#/s/${sala}`);
      await p.getByLabel('Seu nome').fill(nome);
      await p.locator('textarea').fill(frase);
      await p.getByRole('button', { name: 'Enviar meu pedido' }).click();
      await p.waitForSelector('text=Pronto');
      convidados.push(p);
    }
    await org.waitForTimeout(2500);
    await org.getByRole('button', { name: 'Rodar Match' }).click();
    await verPedido(org);
    await checar(org, 'grupo-resultado', ['O pedido do grupo', 'Ana', 'Bia', 'Combo smash + batata + refri']);
    const ana = convidados[0];
    await verPedido(ana);
    const textoAna = await checar(ana, 'grupo-ana', ['Esta é a sua parte', 'seus itens']);
    if (textoAna.includes('Combo smash')) falhas.push('[grupo-ana] a convidada vê o combo de outra pessoa');
    await org.getByRole('button', { name: 'Confirmar pedido' }).click();
    await org.getByRole('button', { name: 'Montar pedido' }).click();
    await org.waitForSelector('text=Confira antes do ok', { timeout: 20000 });
    await checar(org, 'grupo-revisao', ['Confira antes do ok']);
  } catch (e) {
    falhas.push(`[grupo] não completou: ${String(e.message).split('\n')[0]}`);
  }
  if (falhas.length === antes) ok.push('grupo');

  await browser.close();
  console.log(`OK: ${ok.join(', ') || '—'}`);
  if (falhas.length) {
    console.log(`FALHAS (${falhas.length}):\n- ${falhas.join('\n- ')}`);
    process.exit(1);
  }
  console.log(`Tudo certo. Capturas em ${SAIDA}`);
})().catch((e) => { console.error('ERRO', e); process.exit(1); });
