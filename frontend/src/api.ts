// Cliente da API do backend. Tipos espelham backend/app/main.py.

export type Lado = "vendedor" | "comprador";

export interface Acao {
  id: string;
  lado: Lado;
  tipo: string;
  resumo: string;
  motivo: string;
  status: "pendente" | "executada" | "recusada" | "erro";
  resultado: Record<string, unknown> | null;
}

export interface PassoAgente {
  ferramenta: string;
  argumentos: Record<string, unknown>;
  ok: boolean;
  resultado: string;
}

export interface RespostaChat {
  texto: string;
  passos: PassoAgente[];
  acoes: Acao[];
  provedor: string;
  modelo: string;
  conversa_id: string;
}

export interface Saude {
  ok: boolean;
  llm_provedor: string;
  llm_modelo: string;
  ifood_modo: string;
  demonstracao: boolean;
}

async function chamar<T>(caminho: string, corpo?: unknown): Promise<T> {
  const r = await fetch(caminho, {
    method: corpo === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  if (!r.ok) {
    const erro = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(erro.detail ?? `HTTP ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  saude: () => chamar<Saude>("/api/saude"),
  chat: (mensagem: string, lado: Lado, conversa_id?: string) =>
    chamar<RespostaChat>("/api/chat", { mensagem, lado, conversa_id }),
  confirmar: (id: string) => chamar<Acao>(`/api/acoes/${id}/confirmar`, {}),
  recusar: (id: string) => chamar<Acao>(`/api/acoes/${id}/recusar`, {}),
  resetarDemo: () => chamar<{ ok: boolean }>("/api/demo/resetar", {}),
};
