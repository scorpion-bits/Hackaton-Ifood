import type { Candidato, Combinacao, EstadoSala, Entendido, AjusteSala, ResultadoMatch } from "../../tipos";

/** Slots "pid" e "pid#k" viram uma lista por pessoa. */
export function agruparPorPessoa(escolhas: Record<string, Candidato>): Record<string, Candidato[]> {
  const g: Record<string, Candidato[]> = {};
  for (const [slot, c] of Object.entries(escolhas)) {
    const pid = slot.split("#")[0];
    (g[pid] ??= []).push(c);
  }
  return g;
}

/** Itens iguais (mesma loja e item) da mesma pessoa viram uma linha "2× Sundae". */
export function juntarIguais(itens: Candidato[]): Candidato[] {
  const m = new Map<string, { c: Candidato; n: number }>();
  for (const c of itens) {
    const k = `${c.loja_id}|${c.item_id}`;
    const e = m.get(k);
    if (e) {
      e.n += 1;
      e.c = { ...e.c, preco: Math.round((e.c.preco + c.preco) * 100) / 100 };
    } else m.set(k, { c: { ...c }, n: 1 });
  }
  return [...m.values()].map(({ c, n }) => (n > 1 ? { ...c, item_nome: `${n}× ${c.item_nome}` } : c));
}

/** Nota pode vir em 0-1 ou 0-100. */
export function fracao(nota: number): number {
  const n = nota > 1 ? nota / 100 : nota;
  return Math.max(0, Math.min(1, n));
}

/** Média das notas por pessoa (0-1). */
export function mediasPorPessoa(c: Combinacao): Record<string, number> {
  const g = agruparPorPessoa(c.escolhas);
  const r: Record<string, number> = {};
  for (const [pid, itens] of Object.entries(g)) {
    r[pid] = itens.reduce((s, i) => s + fracao(i.nota), 0) / itens.length;
  }
  return r;
}

/** C11: usa `afinidade` do backend; sem ela, média por pessoa das notas. */
export function afinidadeDe(c: Combinacao): number {
  if (typeof c.afinidade === "number" && Number.isFinite(c.afinidade)) return Math.round(c.afinidade);
  const v = Object.values(mediasPorPessoa(c));
  if (!v.length) return 0;
  return Math.round((100 * v.reduce((s, x) => s + x, 0)) / v.length);
}

/** Quem respondeu (ids) ou, sem essa informação, quem aparece na combinação. */
export function pessoasDoGrupo(sala: EstadoSala, c: Combinacao): string[] {
  const ids = sala.participantes.filter((p) => p.respondeu).map((p) => p.id);
  for (const pid of Object.keys(agruparPorPessoa(c.escolhas))) if (!ids.includes(pid)) ids.push(pid);
  return ids;
}

export function felizesDe(c: Combinacao): number {
  if (typeof c.felizes === "number") return c.felizes;
  return Object.values(mediasPorPessoa(c)).filter((m) => m >= 0.5).length;
}

export interface LojaResumo {
  id: string;
  nome: string;
  vertical: string;
}

/** Lojas distintas da combinação, na ordem em que aparecem. */
export function lojasDa(c: Combinacao): LojaResumo[] {
  const m = new Map<string, LojaResumo>();
  for (const i of Object.values(c.escolhas)) {
    if (!m.has(i.loja_id)) m.set(i.loja_id, { id: i.loja_id, nome: limparNome(i.loja_nome), vertical: i.vertical });
  }
  return [...m.values()];
}

/** "Kaigan Sushi (demo)" -> "Kaigan Sushi". */
export function limparNome(n: string): string {
  return n.replace(/\s*\((demo|demonstra[cç][aã]o)\)\s*$/i, "").trim() || n;
}

/** Rótulo curto para a arena: primeira palavra (duas, se a primeira for curta). */
export function nomeCurto(n: string): string {
  const p = limparNome(n).split(/\s+/);
  return p[0].length <= 3 && p[1] ? `${p[0]} ${p[1]}` : p[0];
}

export const leilaoVistoChave = (salaId: string) => `match.leilao.visto.${salaId}`;

/**
 * Assinatura do resultado: muda quando muda alguma escolha ou preço (ajuste do organizador, novo match).
 * O "leilão visto" é guardado por assinatura, não só pela sala.
 */
export function assinatura(res?: ResultadoMatch | null): string {
  if (!res) return "";
  const txt = res.combinacoes
    .map((c) =>
      Object.keys(c.escolhas)
        .sort()
        .map((k) => `${k}=${c.escolhas[k].loja_id}/${c.escolhas[k].item_id}/${c.escolhas[k].preco}`)
        .join(","),
    )
    .join("|");
  let h = 5381;
  for (let i = 0; i < txt.length; i++) h = ((h * 33) ^ txt.charCodeAt(i)) >>> 0;
  return `${res.combinacoes.length}-${h.toString(36)}`;
}

/** Com `sig`, só vale se o leilão visto foi o desta assinatura; sem ela, qualquer um conta. */
export function leilaoVisto(salaId: string, sig?: string): boolean {
  try {
    const v = localStorage.getItem(leilaoVistoChave(salaId));
    if (v === null) return false;
    return sig === undefined ? true : v === sig;
  } catch {
    return false;
  }
}

export function marcarLeilaoVisto(salaId: string, sig = "1"): void {
  try {
    localStorage.setItem(leilaoVistoChave(salaId), sig);
  } catch {
    /* ignora */
  }
}

const semAcento = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** "Milan: açaí no lugar do sorvete · Antonio: mais barato". O back já manda o resumo começando pelo nome (C14). */
export function textoEntendido(e: Entendido[] | string | undefined): string {
  if (!e) return "";
  if (typeof e === "string") return e.trim();
  return e
    .map((x) => (x.nome && !semAcento(x.resumo ?? "").startsWith(semAcento(x.nome)) ? `${x.nome}: ${x.resumo}` : x.resumo))
    .filter(Boolean)
    .join(" · ");
}

export function resumoAjuste(a: AjusteSala): string {
  return textoEntendido(a.entendido);
}

/** Chave de um item de uma pessoa na combinação (para marcar o que mudou depois de um ajuste). */
export function chaveItem(pid: string, c: Candidato): string {
  return `${pid}|${c.loja_id}|${c.item_id}`;
}

export function reduzirMovimento(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}
