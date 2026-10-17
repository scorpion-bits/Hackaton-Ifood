// Espelha C3 (backend/app/match/modelos.py) e C7 (API da sala).
export interface Candidato {
  participante_id: string;
  loja_id: string;
  loja_nome: string;
  item_id: string;
  item_nome: string;
  preco: number;
  eta_min: number | null;
  vertical: string;
  perecivel: boolean;
  nota: number;
  motivo: string;
  viola: string[];
}

export interface Combinacao {
  escolhas: Record<string, Candidato>;
  lojas: string[];
  score: number;
  componentes: Record<string, number>;
  taxa_conhecida: boolean;
  explicacao: string;
}

export interface Parte {
  participante_id: string;
  nome: string;
  itens: number;
  taxa: number;
  desconto: number;
  total: number;
}

export interface Intencao {
  participante_id: string;
  consultas: string[];
  verticais: string[];
  restricoes: string[];
  vontades: string[];
  orcamento_max: number | null;
  perfil: string;
}

export interface ChamadaRastro {
  tool: string;
  resumo: string;
  ms: number;
  ok: boolean;
  erro?: string;
}

export interface ResultadoMatch {
  combinacoes: Combinacao[];
  intencoes: Intencao[];
  avisos: string[];
  rastro: ChamadaRastro[];
}

export interface Carrinho {
  loja_id: string;
  loja_nome: string;
  cart_id: string;
  itens: unknown[];
  subtotal: number;
  taxa: number;
  desconto: number;
  total: number;
  eta_min: number | null;
}

export type EstadoSalaNome =
  | "coletando"
  | "match_pronto"
  | "aguardando_pagamentos"
  | "pronto_para_enviar"
  | "enviado";

export type FormaPagamento = "pix" | "cartao_simulado" | "dinheiro";
export type ModoPagamento = "junto" | "separado";

export interface Pagamento {
  forma: FormaPagamento;
  status: string;
  pix?: string;
}

export interface Participante {
  id: string;
  nome: string;
  respondeu: boolean;
}

export interface EstadoSala {
  estado: EstadoSalaNome;
  demonstracao: boolean;
  participantes: Participante[];
  resultado?: ResultadoMatch;
  carrinhos?: Carrinho[];
  modo_pagamento?: ModoPagamento;
  partes?: Parte[];
  pagamentos?: Record<string, Pagamento>;
  prazo_fim?: string;
  pedidos?: Record<string, unknown>[];
  rastro: ChamadaRastro[];
}

export interface SalaCriada {
  sala_id: string;
  token_organizador: string;
  link_convite: string;
}

export interface Desejo {
  texto: string;
  orcamento_max?: number | null;
  chips: string[];
}
