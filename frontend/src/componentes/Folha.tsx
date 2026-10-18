import { useEffect, useId, useRef, type ReactNode } from "react";
import Icone from "./Icone";

const FOCAVEIS = 'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Folha inferior (bottom sheet) para confirmações. Esc, toque no fundo e botão X fecham (a menos que `travada`). */
export default function Folha({
  titulo,
  onFechar,
  travada = false,
  children,
}: {
  titulo: string;
  onFechar: () => void;
  travada?: boolean;
  children: ReactNode;
}) {
  const idTitulo = useId();
  const painel = useRef<HTMLDivElement>(null);
  const fechar = useRef(onFechar);
  fechar.current = onFechar;
  const bloqueada = useRef(travada);
  bloqueada.current = travada;

  useEffect(() => {
    const antes = document.activeElement as HTMLElement | null;
    const corpo = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const p = painel.current;
    // foca o 1º botão de ação; se não houver, o próprio painel
    (p?.querySelector<HTMLElement>(".folha-acoes " + FOCAVEIS) ?? p)?.focus();

    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape" && !bloqueada.current) {
        e.stopPropagation();
        fechar.current();
      }
      if (e.key === "Tab" && p) {
        const itens = Array.from(p.querySelectorAll<HTMLElement>(FOCAVEIS));
        if (!itens.length) return;
        const primeiro = itens[0];
        const ultimo = itens[itens.length - 1];
        if (e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    }
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("keydown", tecla);
      document.body.style.overflow = corpo;
      antes?.focus?.();
    };
  }, []);

  return (
    <div
      className="fundo-modal"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !travada) onFechar();
      }}
    >
      <div className="modal folha" role="dialog" aria-modal="true" aria-labelledby={idTitulo} tabIndex={-1} ref={painel}>
        <div className="folha-alca" aria-hidden="true" />
        <div className="folha-topo">
          <h2 id={idTitulo}>{titulo}</h2>
          <button type="button" className="folha-x" aria-label="Fechar" disabled={travada} onClick={onFechar}>
            <Icone nome="x" tamanho={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
