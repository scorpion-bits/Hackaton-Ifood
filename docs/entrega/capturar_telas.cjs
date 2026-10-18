// Telas do entregável 04 (docs/entrega/telas/*.png), celular 390×780 a 2×, modo demonstração.
// Rodar: bash docs/entrega/capturar_telas.sh (sobe o app em modo demo na porta 8000 e grava as telas).
// As telas do MCP real (real-*.png) não saem daqui: são capturas do app rodando com o iFood de verdade.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const URL = process.env.E2E_URL || 'http://localhost:8000/';
const SAIDA = process.env.SAIDA || path.join(__dirname, 'telas');
const CHROME = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const ESPERA = 40000;
fs.mkdirSync(SAIDA, { recursive: true });

const CONVIDADOS = [
  ['Bruno', 'japonês e um sorvete, até R$ 45'],
  ['Diego', 'hambúrguer e sorvete, até R$ 50'],
  ['Carla', 'algo barato e vegetariano, até R$ 25'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: fs.existsSync(CHROME) ? CHROME : undefined, args: ['--no-sandbox'] });
  const novo = async () => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 780 }, deviceScaleFactor: 2, locale: 'pt-BR' });
    return ctx.newPage();
  };
  const foto = async (p, nome) => {
    await p.waitForFunction(() => [...document.images].every((i) => i.complete), null, { timeout: 15000 }).catch(() => {});
    await p.waitForTimeout(400);
    await p.screenshot({ path: path.join(SAIDA, `${nome}.png`) });
    console.log('  ', nome);
  };
  const verPedido = async (p) => {
    await p.waitForSelector('.ld-sala, .ld-resultado', { timeout: ESPERA });
    if (await p.locator('.ld-sala').count()) await p.getByRole('button', { name: /Ver o pedido/ }).click({ timeout: ESPERA });
    await p.waitForSelector('.ld-resultado', { timeout: 15000 });
    await p.waitForTimeout(800);
  };

  // ---------- Em grupo ----------
  const org = await novo();
  await org.goto(URL);
  await org.waitForTimeout(600);
  await foto(org, '01-inicio');
  await org.getByRole('button', { name: 'Fazer um match' }).click();
  await org.waitForTimeout(500);
  await foto(org, '02-quem-vai-comer');
  await org.getByRole('button', { name: /Em grupo/ }).click();
  await org.getByLabel(/Seu nome/).fill('Ana');
  await org.getByPlaceholder('CPF, e-mail, telefone ou chave aleatória').fill('ana.republica@exemplo.com');
  await org.getByRole('button', { name: 'Criar sala' }).click();
  await org.waitForSelector('.qrcard');
  const sala = (await org.evaluate(() => location.hash)).split('/')[2];

  const conv = {};
  for (const [nome, frase] of CONVIDADOS) {
    const p = await novo();
    await p.goto(`${URL}#/s/${sala}`);
    await p.getByLabel('Seu nome').fill(nome);
    await p.locator('textarea').fill(frase);
    if (nome === 'Carla') await foto(p, '04-convidado');
    await p.getByRole('button', { name: 'Enviar meu pedido' }).click();
    await p.waitForSelector('text=Pronto');
    conv[nome] = p;
  }
  await org.waitForTimeout(2500);
  await foto(org, '03-sala');

  await org.getByRole('button', { name: 'Rodar Match' }).click();
  await org.waitForSelector('.ld-sala, .ld-resultado', { timeout: ESPERA });
  await org.waitForTimeout(3500);
  await foto(org, '05-avaliacao-lojas');
  await verPedido(org);
  await foto(org, '06-pedido-do-grupo');

  const campo = org.locator('.aj-pilula input, .aj-pilula textarea').first();
  await campo.scrollIntoViewIfNeeded();
  await campo.fill('troca o sorvete de Bruno por açaí');
  await org.getByRole('button', { name: 'Enviar ajuste ao Match' }).click();
  await org.waitForTimeout(6000);
  await org.locator('.aj').evaluate((el) => el.scrollIntoView({ block: 'center' }));
  await foto(org, '07-ajustar-conversa');
  await org.evaluate(() => window.scrollTo(0, 0));
  await foto(org, '08-ajustar-atualizado');

  await org.getByRole('button', { name: 'Confirmar pedido' }).click();
  await org.waitForTimeout(600);
  await foto(org, '09-como-pagar');
  await org.getByText('Cada um paga a sua parte (vaquinha)').click();
  await org.getByRole('button', { name: 'Montar pedido' }).click();
  await org.waitForSelector('text=Confira antes do ok', { timeout: ESPERA });
  await org.waitForTimeout(800);
  await foto(org, '10-confira');

  // Vaquinha: Carla paga por Pix (o organizador marca "Recebi"); Bruno e Diego no cartão simulado.
  const carla = conv['Carla'];
  await carla.waitForTimeout(2500);
  await carla.reload();
  await carla.waitForTimeout(1500);
  await carla.getByRole('button', { name: /Pix/ }).first().click();
  await carla.waitForSelector('img.qr', { timeout: 15000 });
  await carla.waitForTimeout(500);
  await foto(carla, '11-vaquinha-pix');
  for (const nome of ['Bruno', 'Diego']) {
    const p = conv[nome];
    await p.reload();
    await p.waitForTimeout(1500);
    await p.getByRole('button', { name: /Cartão/ }).first().click();
    await p.getByRole('button', { name: /\(simulado\)/ }).click();
    await p.waitForTimeout(800);
  }
  await org.reload();
  await org.waitForTimeout(1500);
  for (let i = 0; i < 3 && (await org.getByRole('button', { name: 'Recebi' }).count()); i++) {
    await org.getByRole('button', { name: 'Recebi' }).first().click();
    await org.waitForTimeout(1000);
  }
  await org.getByRole('button', { name: 'Enviar sem deslizar' }).click({ timeout: 15000 });
  await org.waitForTimeout(600);
  await foto(org, '12-confirmar-envio');
  await org.getByRole('button', { name: /Confirmo enviar/ }).click();
  await org.waitForTimeout(4000);
  await foto(org, '13-pedidos');

  // ---------- Só eu ----------
  const soEu = async (frase, compras, nomes) => {
    const p = await novo();
    await p.goto(URL);
    await p.getByRole('button', { name: 'Fazer um match' }).click();
    await p.getByRole('button', { name: /Só eu/ }).click();
    await p.getByLabel('Seu nome').fill('Ana');
    await p.locator('#soeu-texto').fill(frase);
    if (compras) await p.getByRole('radio', { name: /^Compras/ }).click();
    if (nomes[0]) await foto(p, nomes[0]);
    await p.getByRole('button', { name: 'Encontrar meu pedido' }).click();
    await verPedido(p);
    await foto(p, nomes[1]);
    if (nomes[2]) {
      await p.getByRole('button', { name: 'Confirmar pedido' }).click();
      await p.waitForSelector('text=Confira antes do ok', { timeout: ESPERA });
      await p.waitForTimeout(800);
      await foto(p, nomes[2]);
    }
  };
  await soEu('hambúrguer e uma batata frita', false, ['14-so-eu', '15-so-eu-pedido', '16-so-eu-confira']);
  await soEu('dipirona e protetor solar', true, ['17-compras-farmacia', '18-compras-pedido']);
  await soEu('arroz, feijão e bife', false, [null, '19-sem-compras-prato']);

  await browser.close();
  console.log('ok', SAIDA);
})().catch((e) => { console.error('ERRO', e); process.exit(1); });
