import { useEffect, useId, useRef, useState } from "react";
import type { Participante } from "../../tipos";
import { IconeCoracao, IconeEnviar, IconeFaisca } from "./visual";
import { reduzirMovimento } from "./util";

/** Uma ida e volta com o IBits (C14). O estado vive em `Resultado`, para não se perder quando o deck some durante a disputa curta. */
export interface Troca {
  id: number;
  texto: string;
  estado: "pensando" | "refazendo" | "pronto" | "erro";
  /** "Milan: açaí no lugar do sorvete" (só depois que o servidor respondeu 200). */
  entendido?: string;
  erro?: string;
}

export interface ItemHistorico {
  texto: string;
  resumo: string;
}

const EXEMPLOS_PADRAO = ["troca o sorvete do Milan por açaí", "mais barato pro Antonio", "sem glúten pra Zenon"];

/** Exemplos com os nomes de quem está na sala; sem nomes suficientes, usa os exemplos padrão. */
function exemplosDa(nomes: string[], solo: boolean): string[] {
  if (solo) return ["troca o sorvete por açaí", "mais barato", "sem glúten"];
  const n = (i: number) => nomes[i % Math.max(nomes.length, 1)];
  if (nomes.length === 0) return EXEMPLOS_PADRAO;
  return [`troca o sorvete do ${n(0)} por açaí`, `mais barato pro ${n(1)}`, `sem glúten pra ${n(2)}`];
}

/** Bolha do IBits (esquerda) ou do organizador (direita). */
function Bolha({ de, children, digitando }: { de: "org" | "ibits"; children?: React.ReactNode; digitando?: boolean }) {
  if (de === "org") {
    return (
      <div className="aj-linha org">
        <div className="aj-bolha org">{children}</div>
      </div>
    );
  }
  return (
    <div className="aj-linha ia">
      <span className="aj-av" aria-hidden="true">
        <IconeCoracao tamanho={14} />
      </span>
      <div className="aj-bolha ia">
        {children}
        {digitando && (
          <span className="aj-digitando" role="img" aria-label="IBits está digitando">
            <i />
            <i />
            <i />
          </span>
        )}
      </div>
    </div>
  );
}

function TrocaBolhas({ t }: { t: Troca }) {
  const entendeu = t.entendido ? `Entendi: ${t.entendido}.` : "Entendi.";
  return (
    <>
      <Bolha de="org">{t.texto}</Bolha>
      {t.estado === "pensando" && <Bolha de="ibits" digitando>Entendendo o seu pedido…</Bolha>}
      {t.estado === "refazendo" && (
        <Bolha de="ibits" digitando>
          {entendeu} Refazendo o pedido…
        </Bolha>
      )}
      {t.estado === "pronto" && (
        <Bolha de="ibits">
          {entendeu} Pronto, atualizei as opções.
        </Bolha>
      )}
      {t.estado === "erro" && <Bolha de="ibits">{t.erro}</Bolha>}
    </>
  );
}

/**
 * "Ajustar com o IBits" (C14): campo em pílula + chips de sugestão + conversa em bolhas.
 * Só o organizador vê. Não decide nada: manda a frase ao servidor e mostra o que ele entendeu.
 */
export default function Ajustar({
  participantes,
  troca,
  historico,
  ocupado,
  onEnviar,
}: {
  participantes: Participante[];
  troca: Troca | null;
  historico: ItemHistorico[];
  ocupado: boolean;
  onEnviar: (texto: string) => void;
}) {
  const [texto, setTexto] = useState("");
  const [foco, setFoco] = useState(false);
  const [aberto, setAberto] = useState(false);
  const [ex, setEx] = useState(0);
  const idCampo = useId();
  const fimRef = useRef<HTMLDivElement>(null);

  const nomes = participantes.map((p) => p.nome).filter(Boolean);
  const solo = participantes.length === 1;
  const exemplos = exemplosDa(nomes, solo);
  const campoRef = useRef<HTMLInputElement>(null);

  // Placeholder rotativo: só enquanto o campo está vazio e sem foco (não distrai quem digita).
  useEffect(() => {
    if (foco || texto || reduzirMovimento()) return;
    const t = window.setInterval(() => setEx((i) => i + 1), 3200);
    return () => window.clearInterval(t);
  }, [foco, texto]);

  // Leva a conversa para a vista quando ela muda.
  useEffect(() => {
    if (!troca) return;
    fimRef.current?.scrollIntoView({ block: "nearest", behavior: reduzirMovimento() ? "auto" : "smooth" });
  }, [troca?.id, troca?.estado]);

  // Sala de 1 pessoa: chips só do próprio pedido (nada de "pra {outro}").
  const chips = solo ? ["Mais barato", "Mais rápido"] : [...nomes.slice(0, 3).map((n) => `Mais barato pra ${n}`), "Mais rápido"];

  function enviar(t: string) {
    const limpo = t.trim();
    if (!limpo || ocupado) return;
    onEnviar(limpo);
    setTexto("");
  }

  const placeholder = exemplos[ex % exemplos.length];
  const vazio = !texto.trim();

  return (
    <section className="aj" aria-labelledby={`${idCampo}-t`}>
      <div className="aj-cab">
        <span className="aj-ico" aria-hidden="true">
          <IconeFaisca tamanho={16} />
        </span>
        <h2 id={`${idCampo}-t`}>Ajustar com o IBits</h2>
        {historico.length > 0 && (
          <button
            type="button"
            className="aj-hist"
            aria-expanded={aberto}
            aria-controls={`${idCampo}-h`}
            onClick={() => setAberto((a) => !a)}
          >
            {historico.length} {historico.length === 1 ? "ajuste anterior" : "ajustes anteriores"} <span aria-hidden="true">{aberto ? "▴" : "▾"}</span>
          </button>
        )}
      </div>

      {aberto && historico.length > 0 && (
        <ol className="aj-lista" id={`${idCampo}-h`}>
          {historico.map((h, i) => (
            <li key={i}>
              <b>“{h.texto}”</b>
              {h.resumo && <span>{h.resumo}</span>}
            </li>
          ))}
        </ol>
      )}

      <div className="aj-conversa" role="log" aria-live="polite" aria-label="Conversa com o IBits">
        {troca && (
          <>
            <TrocaBolhas t={troca} />
            <div ref={fimRef} />
          </>
        )}
      </div>

      <div className="aj-chips" role="group" aria-label="Sugestões de ajuste">
        {chips.map((c) => (
          <button key={c} type="button" className="aj-chip" disabled={ocupado} onClick={() => enviar(c)}>
            {c}
          </button>
        ))}
        {solo && (
          <button type="button" className="aj-chip" disabled={ocupado} onClick={() => campoRef.current?.focus()}>
            Outra coisa…
          </button>
        )}
      </div>

      <form
        className="aj-pilula"
        onSubmit={(e) => {
          e.preventDefault();
          enviar(texto);
        }}
      >
        <span className="aj-av grande" aria-hidden="true">
          <IconeCoracao tamanho={16} />
        </span>
        <label htmlFor={idCampo} className="aj-sr">
          Diga ao IBits o que ajustar no pedido
        </label>
        <input
          id={idCampo}
          ref={campoRef}
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onFocus={() => setFoco(true)}
          onBlur={() => setFoco(false)}
          placeholder={placeholder}
          enterKeyHint="send"
          autoComplete="off"
          maxLength={280}
          aria-busy={ocupado}
        />
        <button type="submit" className="aj-enviar" disabled={ocupado || vazio} aria-label="Enviar ajuste ao IBits">
          <IconeEnviar tamanho={20} />
        </button>
      </form>
    </section>
  );
}
