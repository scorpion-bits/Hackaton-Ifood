import type { CSSProperties } from "react";

// Todas com contraste >= 4,5:1 contra o texto branco.
const CORES = ["#c2410c", "#1d6f5a", "#2b5fc7", "#7c3aed", "#b0125f", "#0f766e", "#a16207", "#4f46e5"];

export function corDe(nome: string): string {
  let h = 0;
  for (const ch of nome) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return CORES[h % CORES.length];
}

/** Círculo (pessoa) ou quadrado arredondado (loja) com a inicial. Decorativo. */
export default function Avatar({
  nome,
  tam = "md",
  loja = false,
}: {
  nome: string;
  tam?: "xs" | "sm" | "md" | "lg";
  loja?: boolean;
}) {
  return (
    <span
      className={`face face-${tam} ${loja ? "face-loja" : ""}`}
      style={{ "--c": corDe(nome) } as CSSProperties}
      aria-hidden="true"
    >
      {nome.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}
