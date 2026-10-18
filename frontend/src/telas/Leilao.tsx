import { useEffect, useRef, useState } from "react";
import type { ChamadaRastro, FalaLeilao, Leilao as LeilaoDados, LojaLeilao } from "../tipos";
import { brl } from "../componentes/CartaoPessoa";
import { AvatarLoja, IconeCoracao } from "../componentes/leilao/visual";
import { nomeCurto, reduzirMovimento } from "../componentes/leilao/util";
import "../leilao.css";

interface Linha {
  i: number;
  pronta: boolean;
}

const MAX_FALAS = 6; // orçamento de palco: o leilão todo cabe em ~8 s
const MS_FALA = 820; // intervalo entre falas
const MS_FECHAMENTO = 1400;
const MS_DIGITANDO = 520;
const MS_AUTO_CONVIDADO = 4000; // convidado segue sozinho; organizador toca em "Ver o pedido" (narra o fechamento)
// Versão curta (C14, depois de "Ajustar com o IBits"): ~4 s, abertura + 2 lances/passes + fechamento, segue sozinha.
const COMPACTO = { maxFalas: 4, lances: 2, msFala: 560, msFechamento: 900, msDigitando: 300, msAuto: 1200 };

/**
 * Se o roteiro for longo, mostra: abertura, até 4 lances/passes (vencedoras e patrocinadas primeiro),
 * 1 réplica e o fechamento. Só escolhe o que mostrar; não altera nenhum texto ou número.
 */
function selecionarFalas(L: LeilaoDados, compacto = false): FalaLeilao[] {
  const f = L.falas;
  const maxFalas = compacto ? COMPACTO.maxFalas : MAX_FALAS;
  const nLances = compacto ? COMPACTO.lances : 4;
  if (f.length <= maxFalas) return f;
  const venc = new Set(L.vencedoras);
  const patro = new Set(L.lojas.filter((l) => l.patrocinado).map((l) => l.loja_id));
  const prioridade = (x: FalaLeilao) =>
    x.tipo === "lance" ? (venc.has(x.quem) ? 0 : patro.has(x.quem) ? 1 : 2) : patro.has(x.quem) ? 1 : 3;
  const abertura = f.find((x) => x.tipo === "abertura");
  const fechamento = [...f].reverse().find((x) => x.tipo === "fechamento");
  const replica = f.find((x) => x.tipo === "replica");
  const escolhidas = f
    .filter((x) => x.tipo === "lance" || x.tipo === "passe")
    .map((x, i) => ({ x, i }))
    .sort((a, b) => prioridade(a.x) - prioridade(b.x) || a.i - b.i)
    .slice(0, nLances)
    .map((e) => e.x);
  const manter = new Set<FalaLeilao>([
    ...escolhidas,
    ...[abertura, compacto ? undefined : replica, fechamento].filter((x): x is FalaLeilao => !!x),
  ]);
  return f.filter((x) => manter.has(x));
}

function segundos(ms: number): string {
  return (ms / 1000).toFixed(1).replace(".", ",");
}

function EtiquetaPatrocinado({ demo }: { demo: boolean }) {
  return (
    <>
      <span className="ld-patro">Patrocinado</span>
      {demo && <span className="mini-selo">demonstração</span>}
    </>
  );
}

/**
 * Disputa entre as lojas (C13, leilão): só TOCA o roteiro de `leilao.falas`. Nada aqui calcula preço ou escolhe loja.
 * `onFim` é chamado ao tocar em Pular ou em "Ver o pedido". No aparelho do organizador a tela NUNCA avança sozinha
 * (ele narra o Patrocinado e o fechamento); no do convidado avança ~4 s depois do fechamento.
 */
export default function Leilao({
  leilao,
  rastro,
  organizador,
  onFim,
  compacto = false,
}: {
  leilao: LeilaoDados;
  rastro: ChamadaRastro[];
  organizador: boolean;
  onFim: () => void;
  /** C14: disputa curta (~4 s) depois de um ajuste; segue sozinha para o pedido e tem "Pular". */
  compacto?: boolean;
}) {
  // O polling troca o objeto a cada 2 s: o roteiro usa só o que existia ao montar.
  const L = useRef(leilao).current;
  const R = useRef(rastro).current;
  const falas = useRef(selecionarFalas(leilao, compacto)).current;
  const fimRef = useRef(onFim);
  fimRef.current = onFim;

  const [linhas, setLinhas] = useState<Linha[]>([]);
  const [ativa, setAtiva] = useState<string | null>(null);
  const [passaram, setPassaram] = useState<string[]>([]);
  const [lance, setLance] = useState<{ quem: string; preco: number; k: number } | null>(null);
  const [fechou, setFechou] = useState(false);
  const [terminou, setTerminou] = useState(false);
  const [tick, setTick] = useState<number | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const lojaDe = (id: string): LojaLeilao | undefined => L.lojas.find((l) => l.loja_id === id);
  const vencedoras: string[] =
    [...falas].reverse().find((f) => f.tipo === "fechamento")?.vencedoras ??
    (L.vencedoras.length ? L.vencedoras : L.lojas.filter((l) => l.vencedora).map((l) => l.loja_id));

  useEffect(() => {
    const ts: number[] = [];
    const later = (fn: () => void, ms: number) => ts.push(window.setTimeout(fn, ms));

    setLinhas([]);
    setAtiva(null);
    setPassaram([]);
    setLance(null);
    setFechou(false);
    setTerminou(false);
    setTick(null);

    if (reduzirMovimento()) {
      // Sem animação: mostra tudo de uma vez; quem decide a hora de seguir é a pessoa.
      setLinhas(falas.map((_, i) => ({ i, pronta: true })));
      setPassaram(falas.filter((f) => f.tipo === "passe").map((f) => f.quem));
      setFechou(true);
      setTerminou(true);
      if (R.length) setTick(R.length - 1);
      return () => ts.forEach(clearTimeout);
    }

    // Ticker do rastro MCP, espalhado pela duração da animação.
    const passo = Math.max(90, Math.min(180, 4200 / Math.max(1, R.length)));
    R.forEach((_, j) => later(() => setTick(j), 200 + j * passo));

    const msFala = compacto ? COMPACTO.msFala : MS_FALA;
    const msFech = compacto ? COMPACTO.msFechamento : MS_FECHAMENTO;
    const msDig = compacto ? COMPACTO.msDigitando : MS_DIGITANDO;
    let t = compacto ? 200 : 350;
    falas.forEach((f, i) => {
      const comecar = () => {
        setLinhas((l) => [...l, { i, pronta: false }]);
        setAtiva(f.quem === "ibits" ? null : f.quem);
        if (f.tipo === "passe") setPassaram((p) => (p.includes(f.quem) ? p : [...p, f.quem]));
        if ((f.tipo === "lance" || f.tipo === "replica") && typeof f.preco === "number") {
          setLance({ quem: f.quem, preco: f.preco, k: i });
        }
        if (f.tipo === "fechamento") {
          setAtiva(null);
          setFechou(true);
        }
      };
      later(comecar, t);
      later(() => setLinhas((l) => l.map((x) => (x.i === i ? { ...x, pronta: true } : x))), t + msDig);
      t += f.tipo === "fechamento" ? msFech : msFala;
    });
    later(() => setTerminou(true), t);
    if (compacto) later(() => fimRef.current(), t + COMPACTO.msAuto);
    else if (!organizador) later(() => fimRef.current(), t + MS_AUTO_CONVIDADO);
    return () => ts.forEach(clearTimeout);
  }, [L, R, falas, organizador, compacto]);

  useEffect(() => {
    const el = feedRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [linhas]);

  const med = L.medicoes;
  const nMcp = R.length;
  // Só fala em "agentes com IA" se o roteiro realmente veio de IA (L.llm); senão a IA falhou e o texto é conferido.
  const nIa = L.llm === true && typeof med?.chamadas_llm === "number" ? med.chamadas_llm : 0;
  const rodapeMedicao =
    nMcp > 0 || (typeof med?.ms_total === "number" && med.ms_total >= 100)
      ? [
          nMcp > 0 ? `MCP · ${nMcp} ${nMcp === 1 ? "chamada" : "chamadas"}` : null,
          nIa > 0 ? `${nIa} ${nIa === 1 ? "agente com IA" : "agentes com IA"}` : null,
          typeof med?.ms_total === "number" && med.ms_total >= 100 ? `avaliação em ${segundos(med.ms_total)} s` : null,
        ]
          .filter(Boolean)
          .join(" · ")
      : "";
  const algumPatro = !compacto && L.lojas.some((l) => l.patrocinado);
  const rotuloTicker = tick !== null && R[tick] ? `${R[tick].tool} · ${R[tick].resumo}` : "aguardando";

  function bolha(f: FalaLeilao) {
    const tag =
      f.tipo === "lance" && typeof f.preco === "number"
        ? `${brl(f.preco)}${typeof f.afinidade === "number" ? ` · ${Math.round(f.afinidade)}%` : ""}`
        : null;
    return (
      <>
        {f.texto}
        {tag && <span className="ld-bt">{tag}</span>}
      </>
    );
  }

  return (
    <section className="tela ld-raiz ld-sala" aria-label="Como o IBits avaliou cada loja">
      <div className="ld-top">
        <span className="ld-step">
          {compacto ? "Refazendo o pedido" : "Avaliação das lojas"}
        </span>
        {R.length > 0 && (
          <span className="ld-mcp" title="Chamadas ao MCP do iFood neste match">
            MCP · <b>{R.length}</b>
          </span>
        )}
        {!terminou && (
          <button type="button" className="ld-skip" onClick={onFim}>
            Pular
          </button>
        )}
      </div>

      <div>
        <h1 className="ld-titulo">{compacto ? "O IBits avalia de novo" : "Como o IBits avaliou cada loja"}</h1>
        <p className="ld-subtitulo">
          {compacto
            ? "Com o seu ajuste, o IBits avaliou cada loja de novo, com dados do iFood."
            : "Um avaliador por loja, que só lê o cardápio dela. Preços e prazos vêm do iFood."}
        </p>
      </div>

      {L.lojas.length > 0 && (
        <div className="ld-arena" aria-hidden="true">
          {L.lojas.map((l) => {
            const fora = passaram.includes(l.loja_id) || (fechou && l.passou);
            const venceu = fechou && !fora && vencedoras.includes(l.loja_id);
            const classes = ["ld-ag", ativa === l.loja_id ? "talk" : "", fora ? "out" : "", venceu ? "win" : ""]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={l.loja_id} className={classes}>
                <AvatarLoja id={l.loja_id} nome={l.loja_nome} vertical={l.vertical} imagem={l.imagem_url} />
                <small>{nomeCurto(l.loja_nome)}</small>
                {l.patrocinado && <span className="ld-patro ld-patro-mini">Patrocinado</span>}
                {fechou && !fora && l.afinidade > 0 && <em className="ld-pc" title="Afinidade da loja">{Math.round(l.afinidade)}% · afinidade</em>}
                {lance && lance.quem === l.loja_id && (
                  <span key={lance.k} className="ld-bidtag">
                    {brl(lance.preco)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!compacto && fechou && L.lojas.some((l) => l.afinidade > 0) && (
        <p className="ld-patro-nota">
          % = afinidade da loja: quanto os pratos dela combinam com quem ela atende. A afinidade do pedido inteiro
          aparece no pedido.
        </p>
      )}

      {algumPatro && (
        <p className="ld-patro-nota">
          <EtiquetaPatrocinado demo={L.demonstracao} /> A loja paga para o lance aparecer primeiro. Não muda a nota nem a
          escolha do pedido.
        </p>
      )}

      {R.length > 0 && (
        <div className={`ld-ticker${tick !== null ? " ativo" : ""}`} aria-hidden="true">
          <span className="ld-tk-k">MCP</span>
          <span className="ld-tk-t" key={tick ?? -1}>
            {rotuloTicker}
          </span>
        </div>
      )}

      <div className="ld-feed" ref={feedRef} role="log" aria-live="polite" aria-label="Falas do leilão">
        {linhas.map(({ i, pronta }) => {
          const f = falas[i];
          const ia = f.quem === "ibits";
          const l = ia ? undefined : lojaDe(f.quem);
          return (
            <div key={i} className={`ld-msg${ia ? " ia" : ""}${f.tipo === "passe" ? " ld-passe" : ""}`}>
              {ia ? (
                <span className="ld-ab ld-iaav" aria-hidden>
                  <IconeCoracao tamanho={16} />
                </span>
              ) : (
                <AvatarLoja
                  id={f.quem}
                  nome={l?.loja_nome ?? ""}
                  vertical={l?.vertical ?? ""}
                  imagem={l?.imagem_url}
                  classe="ld-ab-msg"
                />
              )}
              <div>
                <span className="ld-who">
                  {ia ? "IBits" : (l?.loja_nome ?? "Loja")}
                  {l?.patrocinado && <EtiquetaPatrocinado demo={L.demonstracao} />}
                </span>
                {pronta ? (
                  <>
                    <div className="ld-bub">{bolha(f)}</div>
                    {l && (f.tipo === "lance" || f.tipo === "passe") && (
                      <span className="ld-origem">
                        {l.fonte_fala === "llm" ? "agente da loja (IA)" : "texto conferido"}
                      </span>
                    )}
                  </>
                ) : (
                  <div className="ld-bub ld-typing" role="img" aria-label="digitando">
                    <i />
                    <i />
                    <i />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {terminou && (
        <button type="button" className="primario ld-seguir" onClick={onFim} autoFocus>
          {compacto ? "Ver o pedido atualizado" : "Ver o pedido"}
        </button>
      )}

      <p className="ld-nota-rodape">
        Preços e prazos vêm do iFood; o comprador recusa qualquer número que não veio de lá.
        {rodapeMedicao && (
          <>
            <br />
            <b>{rodapeMedicao}</b>
          </>
        )}
      </p>
    </section>
  );
}
