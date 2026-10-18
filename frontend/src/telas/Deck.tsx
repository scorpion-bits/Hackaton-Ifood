import { useRef, useState } from "react";
import type { Candidato, Combinacao, EstadoSala } from "../tipos";
import { brl } from "../componentes/CartaoPessoa";
import EhUmMatch from "../componentes/leilao/EhUmMatch";
import { IconeCoracao, IconeX, Rosto, corPessoa, emojiLoja, gradienteLoja } from "../componentes/leilao/visual";
import {
  afinidadeDe,
  agruparPorPessoa,
  felizesDe,
  juntarIguais,
  lojasDa,
  mediasPorPessoa,
  pessoasDoGrupo,
} from "../componentes/leilao/util";
import "../leilao.css";

const ALERGENO = /confirme com a loja/i;
const APROXIMADA = /^\s*op[cç][aã]o aproximada:/i;
const LIMITE_GESTO = 90;

function Motivo({ texto }: { texto: string }) {
  if (!texto) return null;
  return APROXIMADA.test(texto) ? (
    <em className="ld-motivo ld-aprox">{texto}</em>
  ) : (
    <em className="ld-motivo">{texto}</em>
  );
}

function Linhas({
  c,
  sala,
  pids,
  mostrarSem,
}: {
  c: Combinacao;
  sala: EstadoSala;
  pids: string[];
  mostrarSem: boolean;
}) {
  const grupos = agruparPorPessoa(c.escolhas);
  const nomeDe = (pid: string) => sala.participantes.find((p) => p.id === pid)?.nome ?? "Convidado";
  const corDe = (pid: string) => corPessoa(Math.max(0, sala.participantes.findIndex((p) => p.id === pid)));
  return (
    <ul className="ld-why">
      {pids.flatMap((pid) => {
        const itens = grupos[pid];
        if (!itens) {
          return mostrarSem
            ? [
                <li key={pid} className="sem">
                  <Rosto nome={nomeDe(pid)} cor={corDe(pid)} classe="ld-face-p" />
                  <div>
                    <b>{nomeDe(pid)}</b>
                    <span className="it">Sem opção nesta combinação</span>
                  </div>
                  <strong aria-label="sem preço">—</strong>
                </li>,
              ]
            : [];
        }
        return juntarIguais(itens).map((i: Candidato, k) => (
          <li key={`${pid}-${i.item_id}-${k}`}>
            <Rosto nome={nomeDe(pid)} cor={corDe(pid)} classe="ld-face-p" />
            <div>
              <b>{nomeDe(pid)}</b>
              <span className="it">
                {i.item_nome} · {i.loja_nome.replace(/\s*\(demo\)\s*$/i, "")}
              </span>
              <Motivo texto={i.motivo} />
              {ALERGENO.test(i.motivo) && (
                <small className="ld-aviso-mini">Alergia ou restrição pode não constar no cardápio. Confirme com a loja.</small>
              )}
            </div>
            <strong>{brl(i.preco)}</strong>
          </li>
        ));
      })}
    </ul>
  );
}

function Cartao({
  c,
  sala,
  avisos,
  pids,
  mostrarSem,
  totalPessoas,
  rotulo,
}: {
  c: Combinacao;
  sala: EstadoSala;
  avisos: string[];
  pids: string[];
  mostrarSem: boolean;
  totalPessoas: number;
  rotulo: string;
}) {
  const lojas = lojasDa(c);
  const n = lojas.length;
  const afin = afinidadeDe(c);
  const itens = Object.values(c.escolhas);
  const totalItens = Math.round(itens.reduce((s, i) => s + i.preco, 0) * 100) / 100;
  const etas = itens.map((i) => i.eta_min).filter((e): e is number => typeof e === "number");
  const eta = etas.length ? Math.max(...etas) : null;
  const explicacao = c.explicacao ?? "";
  const avs = avisos.filter((a) => !explicacao.includes(a));
  return (
    <>
      <div className="ld-foto" style={{ background: gradienteLoja(lojas[0]?.id ?? "x") }} aria-hidden="true">
        {lojas.map((l) => (
          <span key={l.id}>{emojiLoja(l.nome, l.vertical)}</span>
        ))}
        <span className="ld-bdg ld-pct">
          <IconeCoracao tamanho={14} /> {afin}% afinidade
        </span>
        <span className={`ld-bdg ${n > 1 ? "dois" : "um"}`}>{n > 1 ? `${n} pedidos` : "1 pedido"}</span>
      </div>
      <div className="ld-cbody">
        <p className="ld-legenda">Quanto os pratos combinam com o que cada um pediu, segundo a IA.</p>
        <h2 className="ld-cnome">{lojas.map((l) => l.nome).join(" + ") || rotulo}</h2>
        <div className="ld-cmeta">
          <span>
            {felizesDe(c)} de {Math.max(totalPessoas, 1)} bem atendidos
          </span>
          {eta !== null && <span>até {eta} min</span>}
        </div>
        <Linhas c={c} sala={sala} pids={pids} mostrarSem={mostrarSem} />
        <p className={`ld-note ${n > 1 ? "warn" : "ok"}`}>
          {n > 1 ? `Dividido em ${n} pedidos: ${n} entregas.` : "Um pedido só: uma entrega."} A taxa de cada entrega
          aparece no carrinho antes do seu ok.
        </p>
        {explicacao && <p className="ld-explica">{explicacao}</p>}
        {avs.map((a, i) => (
          <p key={i} className="ld-aviso">
            {a}
          </p>
        ))}
      </div>
      <div className="ld-cfoot">
        <div>
          <div className="ld-tot">{brl(totalItens)}</div>
          <small>{c.taxa_conhecida ? "itens · taxa já considerada na escolha" : "só itens · taxa no carrinho"}</small>
        </div>
        <span className={`ld-tx${n > 1 ? " w" : ""}`}>
          {n} {n > 1 ? "entregas" : "entrega"}
        </span>
      </div>
    </>
  );
}

/**
 * Deck (C13): 1 cartão por combinação. Organizador desliza/aperta para dar match; convidado só lê.
 * Gesto e botões fazem a mesma coisa.
 */
export default function Deck({
  sala,
  combinacoes,
  avisos,
  organizador,
  meuPid,
  onEscolher,
  onVerLeilao,
}: {
  sala: EstadoSala;
  combinacoes: Combinacao[];
  avisos: string[];
  organizador: boolean;
  meuPid: string | null;
  onEscolher: (idx: number) => void;
  onVerLeilao?: () => void;
}) {
  const lista = combinacoes.slice(0, 3);
  const n = lista.length;
  const [idx, setIdx] = useState(0);
  const [reinicio, setReinicio] = useState(0);
  const [casou, setCasou] = useState<number | null>(null);
  const cartao = useRef<HTMLElement>(null);
  const g = useRef({ sx: 0, dx: 0, arrastando: false, voando: false });
  const sim = useRef<HTMLSpanElement>(null);
  const nao = useRef<HTMLSpanElement>(null);

  const podeMatch = organizador;
  const podeProxima = n > 1;
  const c = lista[Math.min(idx, n - 1)];
  const pidsTodos = pessoasDoGrupo(sala, c);
  // Convidado vê só a própria parte (se não sabemos quem é, mostra tudo em leitura).
  const pids = pidsTodos.filter((pid) => organizador || !meuPid || pid === meuPid);

  function estampas(dx: number) {
    if (sim.current) sim.current.style.opacity = podeMatch ? String(Math.max(0, Math.min(1, dx / 110))) : "0";
    if (nao.current) nao.current.style.opacity = podeProxima ? String(Math.max(0, Math.min(1, -dx / 110))) : "0";
  }

  function voltar() {
    const el = cartao.current;
    if (el) el.style.transform = "";
    estampas(0);
  }

  function voar(dir: 1 | -1) {
    const el = cartao.current;
    const e = g.current;
    if (!el || e.voando) return;
    if ((dir > 0 && !podeMatch) || (dir < 0 && !podeProxima)) {
      voltar();
      return;
    }
    e.voando = true;
    el.classList.remove("drag");
    el.style.transition = "transform .5s cubic-bezier(.4,0,.9,.6), opacity .5s ease";
    el.style.transform = `translate(${dir * 560}px, -40px) rotate(${dir * 26}deg)`;
    el.style.opacity = "0";
    const marca = dir > 0 ? sim.current : nao.current;
    if (marca) marca.style.opacity = "1";
    window.setTimeout(() => {
      e.voando = false;
      if (dir > 0) setCasou(idx);
      else {
        setIdx((i) => (i + 1) % n);
        setReinicio((r) => r + 1);
      }
    }, 380);
  }

  function aoPressionar(ev: React.PointerEvent<HTMLElement>) {
    const e = g.current;
    if (e.voando) return;
    e.arrastando = true;
    e.dx = 0;
    e.sx = ev.clientX;
    ev.currentTarget.setPointerCapture(ev.pointerId);
    ev.currentTarget.classList.add("drag");
  }
  function aoMover(ev: React.PointerEvent<HTMLElement>) {
    const e = g.current;
    if (!e.arrastando) return;
    e.dx = ev.clientX - e.sx;
    ev.currentTarget.style.transform = `translateX(${e.dx}px) rotate(${e.dx / 18}deg)`;
    estampas(e.dx);
  }
  function aoSoltar(ev: React.PointerEvent<HTMLElement>) {
    const e = g.current;
    if (!e.arrastando) return;
    e.arrastando = false;
    ev.currentTarget.classList.remove("drag");
    if (Math.abs(e.dx) > LIMITE_GESTO) voar(e.dx > 0 ? 1 : -1);
    else voltar();
  }

  function continuar() {
    setCasou(null);
    setIdx((i) => (n > 1 ? (i + 1) % n : i));
    setReinicio((r) => r + 1);
  }

  const casada = casou !== null ? lista[casou] : null;
  let overlay = null;
  if (casada) {
    const medias = mediasPorPessoa(casada);
    const ids = pessoasDoGrupo(sala, casada);
    const nomeDe = (pid: string) => sala.participantes.find((p) => p.id === pid)?.nome ?? "Convidado";
    const felizes = felizesDe(casada);
    const semOpcao = ids.find((pid) => !(pid in medias));
    const pior = Object.entries(medias).sort((a, b) => a[1] - b[1])[0];
    const sub =
      ids.length > 1
        ? semOpcao
          ? `${nomeDe(semOpcao)} ficou sem opção nesta combinação.`
          : felizes >= ids.length
            ? "Todo mundo ficou perto do que pediu."
            : pior
              ? `Quem ficou mais longe do ideal: ${nomeDe(pior[0])}.`
              : ""
        : afinidadeDe(casada) >= 85
          ? "É a cara do que você pediu."
          : "É o mais perto do que você pediu agora.";
    const total = Math.round(Object.values(casada.escolhas).reduce((s, i) => s + i.preco, 0) * 100) / 100;
    overlay = (
      <EhUmMatch
        afinidade={afinidadeDe(casada)}
        pessoas={ids.map((pid) => ({
          id: pid,
          nome: nomeDe(pid),
          cor: corPessoa(Math.max(0, sala.participantes.findIndex((p) => p.id === pid))),
        }))}
        lojas={lojasDa(casada)}
        total={total}
        subtitulo={sub}
        textoPrimario="Escolher como pagar"
        onPrimario={() => onEscolher(casou!)}
        onContinuar={continuar}
      />
    );
  }

  return (
    <section className="tela ld-raiz ld-deckbody" aria-label="Opções de pedido">
      {/* Com o overlay "É um Match!" aberto, o fundo fica inerte (sem foco e fora do leitor de tela). */}
      <div className="ld-conteudo" inert={casada ? true : undefined}>
      <div className="ld-top">
        <span className="ld-step">
          Resultado · {idx + 1} de {n}
        </span>
        {onVerLeilao && (
          <button type="button" className="ld-skip" onClick={onVerLeilao}>
            Rever a disputa
          </button>
        )}
      </div>
      <p className="ld-sr" role="status" aria-live="polite">
        Opção {idx + 1} de {n}: {afinidadeDe(c)}% de afinidade.
      </p>

      <div className="ld-deck">
        {n > 2 && <div className="ld-cartao b2" aria-hidden="true" />}
        {n > 1 && <div className="ld-cartao b1" aria-hidden="true" />}
        <article
          key={`${idx}-${reinicio}`}
          ref={cartao}
          className="ld-cartao front"
          aria-label={`Opção ${idx + 1} de ${n}`}
          onPointerDown={aoPressionar}
          onPointerMove={aoMover}
          onPointerUp={aoSoltar}
          onPointerCancel={aoSoltar}
        >
          <Cartao
            c={c}
            sala={sala}
            avisos={avisos}
            pids={pids}
            mostrarSem={organizador}
            totalPessoas={pidsTodos.length}
            rotulo={`Opção ${idx + 1}`}
          />
          {podeMatch && (
            <span ref={sim} className="ld-estampa sim" aria-hidden="true">
              MATCH
            </span>
          )}
          {podeProxima && (
            <span ref={nao} className="ld-estampa nao" aria-hidden="true">
              PRÓXIMA
            </span>
          )}
        </article>
      </div>

      {(podeProxima || podeMatch) && (
        <div className="ld-acoes">
          {podeProxima && (
            <div className="ld-acao">
              <button type="button" className="ld-redondo passa" onClick={() => voar(-1)} aria-label="Ver próxima opção">
                <IconeX tamanho={28} />
              </button>
              <span aria-hidden="true">Ver próxima</span>
            </div>
          )}
          {podeMatch && (
            <div className="ld-acao">
              <button type="button" className="ld-redondo gosta" onClick={() => voar(1)} aria-label="Dar match nesta opção">
                <IconeCoracao tamanho={34} />
              </button>
              <span aria-hidden="true">Dar match</span>
            </div>
          )}
        </div>
      )}

      <p className="ld-dica">
        {organizador
          ? n > 1
            ? "Deslize para a direita para dar match ou para a esquerda para ver a próxima opção."
            : "Deslize para a direita ou toque em Dar match."
          : `O organizador está escolhendo a opção e o modo de pagamento.${n > 1 ? " Deslize para a esquerda para ver as outras opções." : ""}`}
      </p>
      </div>
      {overlay}
    </section>
  );
}
