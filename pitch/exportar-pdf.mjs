// Exporta pitch/index.html para pitch/pitch.pdf usando um navegador já instalado (sem baixar nada).
// Uso: cd pitch && npm install && npm run pdf   (tema escuro: node exportar-pdf.mjs escuro)
// Navegador: variável PITCH_BROWSER, ou Edge/Chrome no Windows, ou Chromium/Chrome no Linux.
import { existsSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const aqui = dirname(fileURLToPath(import.meta.url));

function acharNavegador() {
  const candidatos = [
    process.env.PITCH_BROWSER,
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    ...(existsSync("/opt/pw-browsers")
      ? readdirSync("/opt/pw-browsers").filter((d) => d.startsWith("chromium-")).map((d) => `/opt/pw-browsers/${d}/chrome-linux/chrome`)
      : []),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ];
  const achado = candidatos.find((c) => c && existsSync(c));
  if (!achado) throw new Error("Nenhum navegador encontrado. Defina PITCH_BROWSER com o caminho do Chrome/Edge.");
  return achado;
}

const navegador = await chromium.launch({ executablePath: acharNavegador() });
const pagina = await navegador.newPage();
const tema = process.argv[2] === "escuro" ? "escuro" : "claro";
const saida = tema === "escuro" ? "pitch-escuro.pdf" : "pitch.pdf";
await pagina.goto(pathToFileURL(join(aqui, "index.html")).href + `?print&tema=${tema}`);
await pagina.waitForLoadState("load");
await pagina.pdf({ path: join(aqui, saida), width: "1600px", height: "900px", printBackground: true });
await navegador.close();
console.log(`PDF gerado em pitch/${saida} — faça commit dele.`);
