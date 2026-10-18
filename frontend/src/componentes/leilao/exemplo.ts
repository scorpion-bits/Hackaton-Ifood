// FIXTURE SÓ PARA DESENVOLVIMENTO (npm run dev, rota #/leilao-exemplo). Segue o contrato C11.
// Lojas e itens fictícios do demo; nada aqui vem do iFood.
import type { Candidato, ChamadaRastro, Combinacao, EstadoSala, Leilao, LojaLeilao, ResultadoMatch } from "../../tipos";

const KAIGAN = { id: "loja-demo-japones", nome: "Kaigan Sushi (demo)", vertical: "RESTAURANT" };
const GELATO = { id: "loja-demo-sorvete", nome: "Gelato Bom Clima (demo)", vertical: "RESTAURANT" };
const BRASA = { id: "loja-demo-burger", nome: "Brasa Burger (demo)", vertical: "RESTAURANT" };
const POKE = { id: "loja-demo-poke", nome: "Poke Verde (demo)", vertical: "RESTAURANT" };
const PIZZA = { id: "loja-demo-pizza", nome: "Forno da Praça Pizzaria (demo)", vertical: "RESTAURANT" };
const MERCADO = { id: "loja-demo-mercado", nome: "Mercadinho Bairro Feliz (demo)", vertical: "GROCERIES" };

function cand(
  pid: string,
  l: { id: string; nome: string; vertical: string },
  item: string,
  preco: number,
  nota: number,
  motivo: string,
  eta = 35,
): Candidato {
  return {
    participante_id: pid,
    loja_id: l.id,
    loja_nome: l.nome,
    item_id: `${l.id}:${item}`,
    item_nome: item,
    preco,
    eta_min: eta,
    vertical: l.vertical,
    perecivel: false,
    nota,
    motivo,
    viola: [],
  };
}

const combinacoes: Combinacao[] = [
  {
    escolhas: {
      p1: cand("p1", KAIGAN, "Combo salmão 15 peças", 54.9, 0.94, "Pediu japonês e salmão", 35),
      p2: cand("p2", KAIGAN, "Combo vegetariano 12 peças", 38.9, 0.88, "Japonês sem peixe, como pediu", 35),
      "p3#1": cand("p3", GELATO, "Sorvete de frutas vermelhas sem lactose 500 ml", 27.9, 0.91, "Sem lactose, doce", 50),
    },
    lojas: [KAIGAN.id, GELATO.id],
    score: 0.91,
    componentes: {},
    taxa_conhecida: false,
    explicacao: "Duas lojas atendem todo mundo: japonês para Ana e Bruno, sorvete sem lactose para Carla.",
    afinidade: 91,
    felizes: 3,
  },
  {
    escolhas: {
      p1: cand("p1", BRASA, "Duplo cheddar bacon", 38.9, 0.62, "Opção aproximada: não há japonês aqui; hambúrguer é o mais perto de 'algo salgado'", 30),
      p2: cand("p2", BRASA, "Burger vegano", 34.9, 0.8, "Vegano, como pediu", 30),
      p3: cand("p3", BRASA, "Smash burger clássico", 29.9, 0.41, "Opção aproximada: sem lactose não confirmado no cardápio. Confirme com a loja", 30),
    },
    lojas: [BRASA.id],
    score: 0.6,
    componentes: {},
    taxa_conhecida: false,
    explicacao: "Uma loja só: uma entrega, mas dois pedidos ficam longe do que foi pedido.",
    afinidade: 61,
    felizes: 1,
  },
  {
    escolhas: {
      p1: cand("p1", POKE, "Poke de salmão", 42.9, 0.78, "Salmão cru, perto de japonês", 40),
      p2: cand("p2", POKE, "Poke de tofu", 36.9, 0.81, "Sem carne", 40),
      p3: cand("p3", POKE, "Bowl de quinoa e legumes", 33.9, 0.55, "Opção aproximada: sem sobremesa nesta loja", 40),
    },
    lojas: [POKE.id],
    score: 0.7,
    componentes: {},
    taxa_conhecida: false,
    explicacao: "",
    // sem `afinidade` e `felizes`: o front calcula da média das notas
  },
];

function lojaL(
  l: { id: string; nome: string; vertical: string },
  extra: Partial<LojaLeilao>,
): LojaLeilao {
  return {
    loja_id: l.id,
    loja_nome: l.nome,
    vertical: l.vertical,
    eta_min: 35,
    avaliacao: 4.7,
    imagem_url: null,
    patrocinado: false,
    passou: false,
    ofertas: [],
    atende: 0,
    afinidade: 0,
    fala: "",
    fonte_fala: "modelo",
    vencedora: false,
    ...extra,
  };
}

export const leilaoExemplo: Leilao = {
  llm: true,
  demonstracao: true,
  medicoes: { ms_total: 6400, chamadas_llm: 4 },
  lojas: [
    lojaL(KAIGAN, { atende: 2, afinidade: 91, avaliacao: 4.7, fala: "Atendo 2 de 3 com japonês, R$ 93,80. Nota 4,7.", fonte_fala: "llm", vencedora: true }),
    lojaL(GELATO, { atende: 1, afinidade: 91, avaliacao: 4.9, eta_min: 50, fala: "Fecho o sorvete sem lactose, R$ 27,90. Nota 4,9.", fonte_fala: "llm", vencedora: true }),
    lojaL(BRASA, { patrocinado: true, atende: 3, afinidade: 61, avaliacao: 4.6, eta_min: 30, fala: "Atendo todo mundo, R$ 103,70. Nota 4,6.", fonte_fala: "modelo" }),
    lojaL(POKE, { atende: 3, afinidade: 71, avaliacao: 4.8, eta_min: 40, fala: "Atendo todo mundo, R$ 113,70. Nota 4,8.", fonte_fala: "modelo" }),
    lojaL(PIZZA, { passou: true, fala: "Aqui não tem japonês nem sorvete. Passo.", fonte_fala: "modelo" }),
    lojaL(MERCADO, { passou: true, fala: "Sou mercado, nada de pronto aqui. Passo.", fonte_fala: "modelo" }),
  ],
  falas: [
    { quem: "ibits", tipo: "abertura", texto: "Pedido novo para 3 pessoas: japonês, vegetariano e algo sem lactose. Quem topa?" },
    { quem: PIZZA.id, tipo: "passe", texto: "Aqui não tem japonês nem sorvete. Passo." },
    { quem: MERCADO.id, tipo: "passe", texto: "Sou mercado, nada de pronto aqui. Passo." },
    { quem: BRASA.id, tipo: "lance", texto: "Atendo todo mundo, mas só com hambúrguer.", preco: 103.7, afinidade: 61 },
    { quem: POKE.id, tipo: "lance", texto: "Atendo todo mundo com poke, nota 4,8.", preco: 113.7, afinidade: 71 },
    { quem: KAIGAN.id, tipo: "lance", texto: "Atendo 2 de 3 com japonês de verdade, R$ 93,80.", preco: 93.8, afinidade: 91 },
    { quem: GELATO.id, tipo: "lance", texto: "Fecho o sorvete sem lactose, R$ 27,90. Nota 4,9.", preco: 27.9, afinidade: 91 },
    { quem: GELATO.id, tipo: "replica", texto: "Com o Kaigan fecha os 3 pedidos em 2 lojas." },
    {
      quem: "ibits",
      tipo: "fechamento",
      texto: "Rodada fechada: Kaigan + Gelato, 91% de afinidade. As taxas aparecem no carrinho antes do seu ok.",
      vencedoras: [KAIGAN.id, GELATO.id],
    },
  ],
  vencedoras: [KAIGAN.id, GELATO.id],
};

const rastro: ChamadaRastro[] = [
  ["searchOffers", '"sushi" → 6 itens', 412],
  ["searchOffers", '"sorvete sem lactose" → 4 itens', 388],
  ["getMerchant", "Kaigan Sushi · aberto", 190],
  ["getMerchant", "Gelato Bom Clima · aberto", 175],
  ["getItem", "Combo salmão 15 peças · R$ 54,90", 120],
  ["getItem", "Sorvete de frutas vermelhas · R$ 27,90", 118],
].map(([tool, resumo, ms]) => ({ tool: tool as string, resumo: resumo as string, ms: ms as number, ok: true }));

export const salaExemplo: EstadoSala = {
  estado: "match_pronto",
  demonstracao: true,
  participantes: [
    { id: "p1", nome: "Ana", respondeu: true },
    { id: "p2", nome: "Bruno", respondeu: true },
    { id: "p3", nome: "Carla", respondeu: true },
  ],
  resultado: {
    combinacoes,
    intencoes: [],
    avisos: ["Gelato Bom Clima: alergia ou restrição pode não constar no cardápio."],
    rastro,
    leilao: leilaoExemplo,
  },
  rastro,
};

// ---- C14: ajuste simulado (só dev). "troca o sorvete da Carla por açaí" -> Gelato sai, Açaí Tropical entra. ----
const ACAI = { id: "loja-demo-acai", nome: "Açaí Tropical (demo)", vertical: "RESTAURANT" };

export const leilaoAjustado: Leilao = {
  llm: false,
  demonstracao: true,
  medicoes: { ms_total: 2100 },
  lojas: [
    lojaL(KAIGAN, { atende: 2, afinidade: 91, fala: "Mantenho o japonês da Ana e do Bruno, R$ 93,80.", vencedora: true }),
    lojaL(ACAI, { atende: 1, afinidade: 90, avaliacao: 4.8, eta_min: 40, fala: "Açaí sem lactose para a Carla, R$ 24,90.", vencedora: true }),
    lojaL(GELATO, { passou: true, fala: "Sem açaí por aqui. Passo.", fonte_fala: "modelo" }),
    lojaL(BRASA, { atende: 3, afinidade: 58, eta_min: 30, fala: "Atendo todo mundo com hambúrguer.", fonte_fala: "modelo" }),
  ],
  falas: [
    { quem: "ibits", tipo: "abertura", texto: "Pedido refeito: a Carla quer açaí no lugar do sorvete. Quem topa?" },
    { quem: GELATO.id, tipo: "passe", texto: "Sem açaí por aqui. Passo." },
    { quem: ACAI.id, tipo: "lance", texto: "Açaí sem lactose para a Carla, R$ 24,90.", preco: 24.9, afinidade: 90 },
    { quem: KAIGAN.id, tipo: "lance", texto: "Mantenho o japonês da Ana e do Bruno, R$ 93,80.", preco: 93.8, afinidade: 91 },
    {
      quem: "ibits",
      tipo: "fechamento",
      texto: "Rodada fechada: Kaigan + Açaí Tropical, 91% de afinidade.",
      vencedoras: [KAIGAN.id, ACAI.id],
    },
  ],
  vencedoras: [KAIGAN.id, ACAI.id],
};

export const resultadoAjustado: ResultadoMatch = {
  ...salaExemplo.resultado!,
  combinacoes: [
    {
      ...combinacoes[0],
      escolhas: {
        ...combinacoes[0].escolhas,
        "p3#1": cand("p3", ACAI, "Açaí 500 ml sem lactose", 24.9, 0.9, "Açaí, como pediu, sem lactose", 40),
      },
      lojas: [KAIGAN.id, ACAI.id],
      explicacao: "Kaigan para Ana e Bruno; açaí sem lactose para Carla, como você pediu no ajuste.",
      afinidade: 91,
    },
    ...combinacoes.slice(1),
  ],
  leilao: leilaoAjustado,
};

export const salaAjustada: EstadoSala = {
  ...salaExemplo,
  resultado: resultadoAjustado,
  ajustes: [{ texto: "troca o sorvete da Carla por açaí", entendido: "Carla: açaí no lugar do sorvete", em: "2026-10-18T10:00:00Z" }],
};

function resposta(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });
}

/** Responde /api/salas/exemplo/{escolher,ajustar} sem backend (só em dev). Frases com "erro" -> 422, com "fora" -> 409. */
export function instalarApiFalsa(): () => void {
  const original = window.fetch;
  window.fetch = async (entrada, opc) => {
    const url = typeof entrada === "string" ? entrada : entrada instanceof URL ? entrada.href : entrada.url;
    if (url.includes("/api/salas/exemplo/escolher")) {
      console.info("[exemplo] escolher", opc?.body);
      return resposta(200, { ok: true });
    }
    if (url.includes("/api/salas/exemplo/ajustar")) {
      let texto = "";
      try {
        texto = String(JSON.parse(String(opc?.body ?? "{}")).texto ?? "");
      } catch {
        /* corpo inválido */
      }
      console.info("[exemplo] ajustar", texto);
      await new Promise((r) => setTimeout(r, 1300));
      if (/erro/i.test(texto)) {
        return resposta(422, { detail: "Não entendi esse ajuste. Tente algo como: troca o sorvete da Carla por açaí." });
      }
      if (/fora/i.test(texto)) {
        return resposta(409, { detail: "Não achei combinação com esse ajuste. Mantive o pedido anterior." });
      }
      return resposta(200, {
        entendido: [{ participante_id: "p3", nome: "Carla", resumo: "açaí no lugar do sorvete" }],
        resultado: resultadoAjustado,
      });
    }
    return original(entrada, opc);
  };
  return () => {
    window.fetch = original;
  };
}
