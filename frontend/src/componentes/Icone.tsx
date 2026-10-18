import type { ReactNode } from "react";

/** Ícones de traço simples (desenho próprio, sem biblioteca nem marca do iFood). */
const DESENHOS: Record<string, ReactNode> = {
  coracao: (
    <path
      d="M12 21s-7.5-4.6-9.6-9.2C.8 8.2 2.9 4.5 6.5 4.5c2 0 3.7 1.1 5.5 3.2 1.8-2.1 3.5-3.2 5.5-3.2 3.6 0 5.7 3.7 4.1 7.3C19.5 16.4 12 21 12 21z"
      fill="currentColor"
      stroke="none"
    />
  ),
  voltar: <path d="M15 5l-7 7 7 7" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  pino: (
    <>
      <path d="M12 22s7-6.2 7-12a7 7 0 10-14 0c0 5.8 7 12 7 12z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  baixo: <path d="M6 9l6 6 6-6" />,
  direita: <path d="M9 5l7 7-7 7" />,
  busca: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </>
  ),
  casa: <path d="M3 11l9-8 9 8v10h-6v-6H9v6H3z" />,
  recibo: (
    <>
      <path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" />
      <path d="M9 8h6M9 12h6" />
    </>
  ),
  pessoa: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0116 0" />
    </>
  ),
  seta: <path d="M5 12h14M13 6l6 6-6 6" />,
  copiar: (
    <>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 012-2h10" />
    </>
  ),
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  relogio: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  trilha: <path d="M4 6h16M4 12h10M4 18h7" />,
  celular: (
    <>
      <rect x="7" y="2.5" width="10" height="19" rx="2.5" />
      <path d="M11 18.5h2" />
    </>
  ),
  raio: <path d="M13 2L4 14h7l-1 8 9-12h-7z" />,
  cartao: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="3" />
      <path d="M3 10h18M7 15h4" />
    </>
  ),
  dinheiro: (
    <>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
    </>
  ),
  mais: <path d="M12 5v14M5 12h14" />,
  aviso: (
    <>
      <path d="M12 3l10 18H2z" />
      <path d="M12 10v5M12 18h.01" />
    </>
  ),
};

export type NomeIcone = keyof typeof DESENHOS;

export default function Icone({ nome, tamanho = 22 }: { nome: NomeIcone; tamanho?: number }) {
  return (
    <svg
      className="ic"
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {DESENHOS[nome]}
    </svg>
  );
}
