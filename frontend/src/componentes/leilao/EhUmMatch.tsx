import { useEffect, useRef } from "react";
import { IconeCoracao, Rosto, AvatarLoja } from "./visual";
import type { LojaResumo } from "./util";
import Confete from "./Confete";
import { brl } from "../CartaoPessoa";

export interface PessoaMatch {
  id: string;
  nome: string;
  cor: string;
}

// Posições fixas (sem Math.random no render): 14 corações subindo.
const CORACOES = Array.from({ length: 14 }, (_, i) => ({
  esq: (i * 37 + 8) % 92,
  atraso: 0.5 + ((i * 53) % 24) / 10,
  tam: 14 + ((i * 7) % 22),
}));

/** Overlay "É um Match!" (visual do protótipo). */
export default function EhUmMatch({
  afinidade,
  pessoas,
  lojas,
  total,
  subtitulo,
  textoPrimario,
  onPrimario,
  onContinuar,
}: {
  afinidade: number;
  pessoas: PessoaMatch[];
  lojas: (LojaResumo & { imagem?: string | null })[];
  total: number;
  subtitulo: string;
  textoPrimario: string;
  onPrimario: () => void;
  onContinuar: () => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const raiz = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const antes = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    try {
      navigator.vibrate?.([40, 40, 80]);
    } catch {
      /* ignora */
    }
    const f = (e: KeyboardEvent) => {
      if (e.key === "Escape") onContinuar();
      if (e.key === "Tab") {
        // trava de foco: Tab e Shift+Tab ficam entre os botões do diálogo
        const bt = Array.from(raiz.current?.querySelectorAll<HTMLElement>("button:not([disabled])") ?? []);
        if (!bt.length) return;
        const primeiro = bt[0];
        const ultimo = bt[bt.length - 1];
        const atual = document.activeElement;
        if (!raiz.current?.contains(atual)) {
          e.preventDefault();
          primeiro.focus();
        } else if (e.shiftKey && atual === primeiro) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && atual === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    };
    window.addEventListener("keydown", f);
    return () => {
      window.removeEventListener("keydown", f);
      if (antes && document.contains(antes)) antes.focus?.();
    };
  }, [onContinuar]);

  return (
    <div ref={raiz} className="ld-raiz ld-match" role="dialog" aria-modal="true" aria-labelledby="ld-match-titulo">
      <div className="ld-coracoes" aria-hidden="true">
        {CORACOES.map((c, i) => (
          <span key={i} className="ld-fh" style={{ left: `${c.esq}%`, animationDelay: `${c.atraso}s` }}>
            <IconeCoracao tamanho={c.tam} />
          </span>
        ))}
      </div>
      <Confete />
      <div className="ld-mwrap">
        <p className="ld-eyebrow">{afinidade}% de afinidade</p>
        <h1 className="ld-mtitle" id="ld-match-titulo">
          É um Match!
        </h1>
        <div className="ld-par" aria-hidden="true">
          <div className="ld-pgrupo">
            {pessoas.map((p) => (
              <Rosto key={p.id} nome={p.nome} cor={p.cor} classe="ld-face-g" />
            ))}
          </div>
          <div className="ld-mcoracao">
            <IconeCoracao tamanho={28} />
          </div>
          <div className="ld-prest">
            {lojas.map((l) => (
              <AvatarLoja key={l.id} id={l.id} nome={l.nome} vertical={l.vertical} imagem={l.imagem} classe="ld-rt" />
            ))}
          </div>
        </div>
        <p className="ld-mtexto">
          {lojas.map((l) => l.nome).join(" + ")} · itens {brl(total)}
        </p>
        <p className="ld-msub">{subtitulo}</p>
      </div>
      <div className="ld-mfoot">
        <button ref={ref} type="button" className="ld-btn-branco" onClick={onPrimario}>
          {textoPrimario}
        </button>
        <button type="button" className="ld-btn-claro" onClick={onContinuar}>
          Seguir deslizando
        </button>
      </div>
    </div>
  );
}
