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
  /** C11: 0-100, média por pessoa das notas. Ausente em resultado antigo (o front calcula). */
  afinidade?: number;
  /** C11: pessoas com média de nota >= 0,5. */
  felizes?: number;
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

// C11: leilão de agentes por loja (só leitura no front).
export interface OfertaLeilao {
  slot_id: string;
  participante_id: string;
  nome: string;
  item_id: string;
  item_nome: string;
  preco: number;
  nota: number;
  motivo: string;
}

export interface LojaLeilao {
  loja_id: string;
  loja_nome: string;
  vertical: string;
  eta_min: number | null;
  avaliacao: number | null;
  imagem_url: string | null;
  patrocinado: boolean;
  passou: boolean;
  ofertas: OfertaLeilao[];
  atende: number;
  afinidade: number;
  fala: string;
  fonte_fala: "llm" | "modelo";
  vencedora: boolean;
}

export type TipoFala = "abertura" | "passe" | "lance" | "replica" | "fechamento";

export interface FalaLeilao {
  /** "ibits" ou o loja_id. */
  quem: string;
  tipo: TipoFala;
  texto: string;
  preco?: number | null;
  afinidade?: number | null;
  vencedoras?: string[];
}

/** Medições do servidor (opcional; o front não inventa o que faltar). */
export interface MedicoesLeilao {
  ms_total?: number;
  ms_por_loja?: Record<string, number>;
  chamadas_llm?: number;
}

export interface Leilao {
  llm: boolean;
  medicoes?: MedicoesLeilao;
  demonstracao: boolean;
  lojas: LojaLeilao[];
  falas: FalaLeilao[];
  vencedoras: string[];
}

export interface ResultadoMatch {
  combinacoes: Combinacao[];
  /** C11: ausente em resultado antigo ou se o leilão falhou. */
  leilao?: Leilao;
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
  /** Taxa de serviço do iFood (bug 29), já incluída no total; dividida nas partes junto com a entrega. */
  servico?: number;
  desconto: number;
  total: number;
  eta_min: number | null;
  /** Forma de pagamento escolhida no carrinho (C16). No modo real é sempre uma forma sem cobrança online. */
  pagamento?: { id?: string; nome: string; tipo?: string; offline: boolean };
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

/** C14: o que o IBits entendeu de um ajuste, por pessoa. */
export interface Entendido {
  participante_id: string;
  nome: string;
  resumo: string;
}

/** C14: POST /api/salas/{id}/ajustar -> 200. */
export interface RespostaAjuste {
  entendido: Entendido[];
  resultado: ResultadoMatch;
}

/** C14: histórico em GET /api/salas/{id}. `entendido` pode vir como lista ou como texto. */
export interface AjusteSala {
  texto: string;
  entendido?: Entendido[] | string;
  em?: string;
}

export interface EstadoSala {
  estado: EstadoSalaNome;
  demonstracao: boolean;
  conta_teste?: boolean;
  /** O organizador cadastrou chave Pix ao criar a sala (o GET nunca devolve a chave inteira). */
  tem_chave_pix?: boolean;
  participantes: Participante[];
  resultado?: ResultadoMatch;
  carrinhos?: Carrinho[];
  modo_pagamento?: ModoPagamento;
  partes?: Parte[];
  pagamentos?: Record<string, Pagamento>;
  prazo_fim?: string;
  pedidos?: Record<string, unknown>[];
  /** C14 (opcional): ajustes já feitos com o IBits, do mais antigo ao mais novo. */
  ajustes?: AjusteSala[];
  /** Bug 21 (opcional): avisos gravados ao montar os carrinhos (ex.: loja que o iFood recusou e saiu do pedido). */
  avisos?: string[];
  rastro: ChamadaRastro[];
}

export interface SalaCriada {
  sala_id: string;
  token_organizador: string;
  link_convite: string;
  participante_id?: string;
}

export interface Desejo {
  texto: string;
  orcamento_max?: number | null;
  chips: string[];
}

// C9: GET /api/ifood/status
export interface StatusIfood {
  modo: "demo" | "real";
  conectado: boolean;
  expira_em?: string;
  conta?: string;
}
