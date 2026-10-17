import type {
  Desejo,
  EstadoSala,
  FormaPagamento,
  ModoPagamento,
  ResultadoMatch,
  SalaCriada,
  StatusIfood,
} from "./tipos";

async function chamar<T>(
  caminho: string,
  opc: { metodo?: string; corpo?: unknown; token?: string | null } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opc.corpo !== undefined) headers["Content-Type"] = "application/json";
  if (opc.token) headers["X-Organizador"] = opc.token;
  const r = await fetch(caminho, {
    method: opc.metodo ?? (opc.corpo !== undefined ? "POST" : "GET"),
    headers,
    body: opc.corpo !== undefined ? JSON.stringify(opc.corpo) : undefined,
  });
  if (!r.ok) {
    let det = `Erro ${r.status}`;
    try {
      const j = await r.json();
      if (typeof j.detail === "string") det = j.detail;
    } catch {
      /* corpo não é JSON */
    }
    throw new Error(det);
  }
  return (await r.json()) as T;
}

const S = (id: string) => `/api/salas/${encodeURIComponent(id)}`;

export const api = {
  criarSala: (organizador_nome: string, chave_pix?: string) =>
    chamar<SalaCriada>("/api/salas", { corpo: { organizador_nome, chave_pix: chave_pix || undefined } }),
  estado: (id: string) => chamar<EstadoSala>(S(id)),
  entrar: (id: string, nome: string) =>
    chamar<{ participante_id: string }>(`${S(id)}/participantes`, { corpo: { nome } }),
  desejo: (id: string, pid: string, d: Desejo) =>
    chamar<{ ok: boolean }>(`${S(id)}/participantes/${encodeURIComponent(pid)}/desejo`, {
      metodo: "PUT",
      corpo: d,
    }),
  rodar: (id: string, token: string) =>
    chamar<ResultadoMatch>(`${S(id)}/rodar`, { metodo: "POST", corpo: {}, token }),
  escolher: (id: string, token: string, combinacao: number, modo_pagamento: ModoPagamento) =>
    chamar<unknown>(`${S(id)}/escolher`, { corpo: { combinacao, modo_pagamento }, token }),
  pagar: (id: string, pid: string, forma: FormaPagamento) =>
    chamar<{ status: string; pix_copia_e_cola?: string }>(`${S(id)}/pagamentos/${encodeURIComponent(pid)}`, {
      corpo: { forma },
    }),
  recebi: (id: string, pid: string, token: string) =>
    chamar<unknown>(`${S(id)}/pagamentos/${encodeURIComponent(pid)}/recebi`, { metodo: "POST", corpo: {}, token }),
  resolver: (id: string, pid: string, token: string, acao: "organizador_cobre" | "remover_itens") =>
    chamar<unknown>(`${S(id)}/pagamentos/${encodeURIComponent(pid)}/resolver`, { corpo: { acao }, token }),
  enviar: (id: string, token: string) =>
    chamar<unknown>(`${S(id)}/enviar`, { corpo: { confirmo: true }, token }),
  atualizarPedido: (id: string, orderId: string) =>
    chamar<unknown>(`${S(id)}/pedidos/${encodeURIComponent(orderId)}/atualizar`, { metodo: "POST", corpo: {} }),
  ifoodStatus: () => chamar<StatusIfood>("/api/ifood/status"),
  ifoodSair: () => chamar<unknown>("/api/ifood/sair", { metodo: "POST", corpo: {} }),
  resetar: () => chamar<unknown>("/api/demo/resetar", { metodo: "POST", corpo: {} }),
};

// Armazenamento local (sempre com try/catch: pode estar bloqueado).
export function lerLocal<T>(chave: string): T | null {
  try {
    const v = localStorage.getItem(chave);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}
export function gravarLocal(chave: string, valor: unknown): void {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    /* ignora */
  }
}
export function apagarLocal(chave: string): void {
  try {
    localStorage.removeItem(chave);
  } catch {
    /* ignora */
  }
}

export const chaveOrg = (salaId: string) => `match.org.${salaId}`;
export const chaveEu = "match.eu";
export const chaveBase = "match.base";
export interface Eu {
  nome: string;
  chips: string[];
}
export const lerToken = (salaId: string) => lerLocal<string>(chaveOrg(salaId));

export const chaveUltimaSala = "match.ultima_sala";

/** Apaga todas as chaves `match.*` deste aparelho. */
export function limparMatchLocal(): void {
  try {
    const ks: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("match.")) ks.push(k);
    }
    ks.forEach((k) => localStorage.removeItem(k));
  } catch {
    /* ignora */
  }
}

/** Sala do organizador mais recente salva neste aparelho (ou null). */
export function ultimaSalaOrg(): string | null {
  const u = lerLocal<string>(chaveUltimaSala);
  if (u && lerLocal<string>(chaveOrg(u))) return u;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("match.org.")) return k.slice("match.org.".length);
    }
  } catch {
    /* ignora */
  }
  return null;
}
