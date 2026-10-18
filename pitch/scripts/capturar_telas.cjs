// Capturas do pitch (persona Ana): app em modo demonstração, celular 390×844, 2× (nítido no projetor).
// Rodar: bash pitch/scripts/capturar_telas.sh  →  grava pitch/img/app/*.png
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const URL = process.env.E2E_URL || 'http://localhost:8000/';
const SAIDA = process.env.SAIDA || path.join(__dirname, '..', 'img', 'app');
const CHROME = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
fs.mkdirSync(SAIDA, { recursive: true });

const CONVIDADOS = [
  ['Bruno', 'japonês e um sorvete, até R$ 45'],
  ['Diego', 'hambúrguer e sorvete, até R$ 50'],
  ['Carla', 'algo barato e vegetariano, até R$ 25'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: fs.existsSync(CHROME) ? CHROME : undefined, args: ['--no-sandbox'] });
  const novo = async () => {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'pt-BR' });
    return ctx.newPage();
  };
  const foto = (p, nome) => p.screenshot({ path: path.join(SAIDA, `${nome}.png`) });

  const org = await novo();
  await org.goto(URL);
  await org.waitForTimeout(600);
  await foto(org, '01-inicio');
  await org.getByRole('button', { name: 'Fazer um match' }).click();
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
    if (nome === 'Carla') await foto(p, '03-convidado');
    await p.getByRole('button', { name: 'Enviar meu pedido' }).click();
    await p.waitForSelector('text=Pronto');
    conv[nome] = p;
  }
  await org.waitForTimeout(2500);
  await foto(org, '02-sala');

  await org.getByRole('button', { name: 'Rodar Match' }).click();
  await org.waitForSelector('.ld-sala, .ld-resultado', { timeout: 40000 });
  await org.waitForTimeout(3500);
  await foto(org, '04-avaliacao');
  if (await org.locator('.ld-sala').count()) await org.getByRole('button', { name: /Ver o pedido/ }).click({ timeout: 40000 });
  await org.waitForSelector('.ld-resultado', { timeout: 15000 });
  await org.waitForTimeout(800);
  await foto(org, '05-pedido');

  // Ajustar com o IBits
  const campo = org.locator('.aj-pilula input, .aj-pilula textarea').first();
  await campo.scrollIntoViewIfNeeded();
  await campo.fill('troca o sorvete de Bruno por açaí');
  await org.getByRole('button', { name: 'Enviar ajuste ao IBits' }).click();
  await org.waitForTimeout(6000);
  await org.locator('.aj').evaluate((el) => el.scrollIntoView({ block: 'center' }));
  await foto(org, '06-ajustar');

  await org.getByRole('button', { name: 'Confirmar pedido' }).click();
  await org.getByText('Cada um paga a sua parte (vaquinha)').click();
  await org.getByRole('button', { name: 'Montar pedido' }).click();
  await org.waitForSelector('text=Confira antes do ok', { timeout: 20000 });
  await org.waitForTimeout(800);
  await foto(org, '07-confira');

  const carla = conv['Carla'];
  await carla.waitForTimeout(2500);
  await carla.reload();
  await carla.waitForTimeout(1500);
  await carla.getByRole('button', { name: /Pix/ }).first().click();
  await carla.waitForSelector('img.qr', { timeout: 15000 });
  await carla.waitForTimeout(500);
  await foto(carla, '08-vaquinha-pix');

  await browser.close();
  console.log('ok', SAIDA);
})().catch((e) => { console.error('ERRO', e); process.exit(1); });
