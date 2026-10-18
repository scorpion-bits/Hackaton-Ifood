import { useState } from "react";

/** Emoji e gradiente de uma loja (nada de logo ou foto do iFood). */
const GRADIENTES: [string, string][] = [
  ["#FF9A3D", "#E8412B"],
  ["#FFC23D", "#E8412B"],
  ["#3DB8C9", "#1B5E8C"],
  ["#7BD389", "#2E9E5B"],
  ["#F2A65A", "#B5651D"],
  ["#FFB703", "#FB5607"],
  ["#7FD8FF", "#4B8DF0"],
  ["#9B5DE5", "#5B2A9E"],
];

const POR_NOME: [RegExp, string][] = [
  [/sushi|japon|temaki|kaigan/i, "🍣"],
  [/gelato|sorvet/i, "🍦"],
  [/a[cç]a[ií]/i, "🍇"],
  [/burger|hamb[uú]rguer|smash|lanche/i, "🍔"],
  [/pizza|forno/i, "🍕"],
  [/poke|salada|saud[aá]vel|vegan/i, "🥗"],
  [/wrap/i, "🌯"],
  [/marmit|caseir/i, "🍛"],
  [/padaria|p[aã]o/i, "🥐"],
  [/doce|bolo|confeit|sobremesa/i, "🍰"],
  [/caf[eé]/i, "☕"],
  [/mercad|supermerc|mercearia/i, "🛒"],
  [/farm[aá]cia|drogaria/i, "💊"],
  [/pet/i, "🐾"],
  [/bebida|adega|cerveja/i, "🍻"],
];

const POR_VERTICAL: Record<string, string> = {
  RESTAURANT: "🍽️",
  GROCERIES: "🛒",
  MARKET: "🛒",
  PHARMACY: "💊",
  PET: "🐾",
  PETSHOP: "🐾",
  DRINKS: "🍻",
  CONVENIENCE: "🏪",
  SHOPPING: "🛍️",
};

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
}

export function emojiLoja(nome: string, vertical: string): string {
  for (const [re, e] of POR_NOME) if (re.test(nome)) return e;
  return POR_VERTICAL[vertical?.toUpperCase()] ?? "🍽️";
}

export function gradienteLoja(id: string): string {
  const [a, b] = GRADIENTES[hash(id) % GRADIENTES.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

export function AvatarLoja({
  id,
  nome,
  vertical,
  imagem,
  classe = "",
}: {
  id: string;
  nome: string;
  vertical: string;
  imagem?: string | null;
  classe?: string;
}) {
  const [falhou, setFalhou] = useState(false);
  return (
    <span className={`ld-ab ${classe}`} style={{ background: gradienteLoja(id) }} aria-hidden>
      {imagem && !falhou ? (
        <img src={imagem} alt="" loading="lazy" onError={() => setFalhou(true)} />
      ) : (
        emojiLoja(nome, vertical)
      )}
    </span>
  );
}

const CORES_PESSOA = ["#EA1D2C", "#2E7D6B", "#3B6EDB", "#B8641D", "#8A4FD1", "#C2185B"];

export const corPessoa = (indice: number) => CORES_PESSOA[Math.abs(indice) % CORES_PESSOA.length];

export function Rosto({ nome, cor, classe = "" }: { nome: string; cor: string; classe?: string }) {
  return (
    <span className={`ld-face ${classe}`} style={{ background: cor }} aria-hidden>
      {nome.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}

export function IconeCoracao({ tamanho = 20 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" aria-hidden="true" style={{ display: "block", flex: "none" }}>
      <path
        d="M12 21s-7.5-4.6-9.6-9.2C.8 8.2 2.9 4.5 6.5 4.5c2 0 3.7 1.1 5.5 3.2 1.8-2.1 3.5-3.2 5.5-3.2 3.6 0 5.7 3.7 4.1 7.3C19.5 16.4 12 21 12 21z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconeX({ tamanho = 26 }: { tamanho?: number }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      style={{ display: "block", flex: "none" }}
    >
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function IconeFaisca({ tamanho = 18 }: { tamanho?: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" aria-hidden="true" style={{ display: "block", flex: "none" }}>
      <path d="M12 2l1.9 5.6L19.5 9.5l-5.6 1.9L12 17l-1.9-5.6L4.5 9.5l5.6-1.9z" fill="currentColor" />
      <path d="M19 15l.9 2.6 2.6.9-2.6.9L19 22l-.9-2.6-2.6-.9 2.6-.9z" fill="currentColor" />
    </svg>
  );
}

export function IconeEnviar({ tamanho = 20 }: { tamanho?: number }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: "block", flex: "none" }}
    >
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}
