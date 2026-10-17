// Mantém o CLAUDE.md enxuto (só estado vigente).
//   node .claude/hooks/limite-claude-md.mjs post    -> PostToolUse (Write|Edit): se passar do limite, devolve ao Claude a ordem de arquivar
//   node .claude/hooks/limite-claude-md.mjs inicio  -> SessionStart: avisa no início da sessão se já estiver acima do limite
import { existsSync, readFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const LIMITE = 250; // linhas máximas do CLAUDE.md
const ALVO = 180; // depois de arquivar, ficar perto disto
const raiz = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const claudeMd = join(raiz, "CLAUDE.md");
const modo = process.argv[2] || "post";

function linhas(caminho) {
  return readFileSync(caminho, "utf8").split(/\r?\n/).length;
}

const instrucao = (n) =>
  `CLAUDE.md está com ${n} linhas (limite ${LIMITE}). Faça agora a manutenção: mova para docs/historico.md ` +
  `(no topo, com a data e o motivo) tudo que não é mais vigente — etapas concluídas, decisões substituídas, ` +
  `pendências resolvidas, detalhes que já estão em docs/. Deixe no CLAUDE.md só o estado atual e ponteiros ` +
  `para os arquivos, até ~${ALVO} linhas. Não apague informação: arquive.`;

let entrada = {};
try {
  const bruto = readFileSync(0, "utf8");
  entrada = bruto.trim() ? JSON.parse(bruto) : {};
} catch {
  entrada = {};
}

if (!existsSync(claudeMd)) process.exit(0);

if (modo === "inicio") {
  const n = linhas(claudeMd);
  if (n > LIMITE) {
    console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: instrucao(n) } }));
  }
  process.exit(0);
}

const arquivo = entrada?.tool_input?.file_path;
if (!arquivo || basename(arquivo) !== "CLAUDE.md" || resolve(arquivo) !== resolve(claudeMd)) process.exit(0);
const n = linhas(claudeMd);
if (n > LIMITE) {
  console.log(JSON.stringify({ decision: "block", reason: instrucao(n) }));
}
process.exit(0);
