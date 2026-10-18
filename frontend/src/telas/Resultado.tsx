import { useEffect, useRef, useState } from "react";
import { api, lerToken } from "../api";
import type { Combinacao, EstadoSala, Leilao as LeilaoDados, ModoPagamento, ResultadoMatch } from "../tipos";
import CartaoPessoa, { brl } from "../componentes/CartaoPessoa";
import Rastro from "../componentes/Rastro";
import {
  agruparPorPessoa,
  assinatura,
  juntarIguais,
  leilaoVisto,
  marcarLeilaoVisto,
  reduzirMovimento,
  resumoAjuste,
  textoEntendido,
} from "../componentes/leilao/util";
import Ajustar, { type ItemHistorico, type Troca } from "../componentes/leilao/Ajustar";
import { lerPid } from "./Convidado";
import Leilao from "./Leilao";
import Deck from "./Deck";
import "../leilao.css";

type Fase = "leilao" | "leilao-curto" | "pedido" | "escolha";

const MS_DESTAQUE = 8000;
const MS_FAIXA = 10000;
const ESPERA = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

/** Mensagem amigável: falha de rede vira texto claro; 422/409 já chegam com a frase do servidor. */
function mensagemAjuste(x: unknown): string {
  const m = x instanceof Error ? x.message : "";
  if (!m || /failed to fetch|networkerror|load failed|erro 5\d\d/i.test(m)) {
    return "Não consegui falar com o servidor agora. Tente de novo em instantes.";
  }
  if (/^erro 4\d\d$/i.test(m)) return "Não entendi esse ajuste. Tente algo como: troca o sorvete do Milan por açaí.";
  return m;
}

function textoModos(nPedidos: number): { id: ModoPagamento; titulo: string; texto: string; destaque?: string }[] {
  return [
    {
      id: "junto",
      titulo: "Pagar tudo de uma vez",
      texto: "Você paga o total no iFood e acerta com o pessoal depois.",
      destaque: nPedidos === 1 ? "É 1 pedido: 1 cobrança." : `São ${nPedidos} pedidos: ${nPedidos} cobranças.`,
    },
    {
      id: "separado",
      titulo: "Cada um paga a sua parte (vaquinha)",
      texto: "Cada pessoa paga a própria parte e os pedidos só saem quando todos pagarem.",
    },
  ];
}

/**
 * match_pronto (C13): avaliação das lojas (1 vez por aparelho) -> o pedido que o IBits escolheu -> como pagar.
 * Mudar o pedido = "Ajustar com o IBits"; não há outras opções para passar. Convidado vê tudo só para leitura.
 */
export default function Resultado({
  salaId,
  sala,
  organizador,
}: {
  salaId: string;
  sala: EstadoSala;
  organizador: boolean;
}) {
  const solo = sala.participantes.length === 1;
  const resSala = sala.resultado;
  const sigSala = assinatura(resSala);

  // C14: depois de "Ajustar", usa a resposta do servidor até a sala (polling de 2 s) trazer o mesmo resultado.
  const [local, setLocal] = useState<{ res: ResultadoMatch; base: string } | null>(null);
  // Enquanto o IBits refaz o pedido, o cartão não muda por baixo da pessoa.
  const [retido, setRetido] = useState<ResultadoMatch | null>(null);
  const res = retido ?? (local && sigSala === local.base ? local.res : resSala);
  const sig = assinatura(res);
  const leilao = res?.leilao;

  const [fase, setFase] = useState<Fase>(() => (leilao && !leilaoVisto(salaId, sig) ? "leilao" : "pedido"));
  const [modo, setModo] = useState<ModoPagamento>("junto");
  const [montando, setMontando] = useState(false);
  const [erro, setErro] = useState("");

  // C14: conversa com o IBits, opções de antes do ajuste (para marcar o que mudou) e destaques.
  const [troca, setTroca] = useState<Troca | null>(null);
  const [histLocal, setHistLocal] = useState<ItemHistorico[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [anteriores, setAnteriores] = useState<Combinacao[] | undefined>(undefined);
  const [leilaoCurto, setLeilaoCurto] = useState<LeilaoDados | null>(null);
  const [pendDestaque, setPendDestaque] = useState(false);
  const [atualizado, setAtualizado] = useState(false);
  const [faixa, setFaixa] = useState("");
  const tDestaque = useRef<number | undefined>(undefined);
  const tFaixa = useRef<number | undefined>(undefined);
  const anterior = useRef({ sig, res });

  // O servidor já trouxe o resultado novo (ou outro): a resposta local não vale mais.
  useEffect(() => {
    if (local && sigSala !== local.base) setLocal(null);
  }, [sigSala, local]);

  // Convidado: o organizador ajustou o pedido -> faixa e cartão atualizado (o leilão "visto" é por assinatura).
  useEffect(() => {
    const antes = anterior.current;
    anterior.current = { sig, res };
    if (organizador || !antes.sig || antes.sig === sig) return;
    setAnteriores(antes.res?.combinacoes);
    setFaixa("O organizador ajustou o pedido");
    setPendDestaque(true);
    marcarLeilaoVisto(salaId, sig);
    setFase((f) => (f === "leilao" ? "pedido" : f));
  }, [sig]); // eslint-disable-line react-hooks/exhaustive-deps

  // O destaque "Atualizado" só começa a contar quando o pedido está na tela.
  useEffect(() => {
    if (fase !== "pedido" || !pendDestaque) return;
    setPendDestaque(false);
    setAtualizado(true);
    window.clearTimeout(tDestaque.current);
    tDestaque.current = window.setTimeout(() => setAtualizado(false), MS_DESTAQUE);
    window.clearTimeout(tFaixa.current);
    tFaixa.current = window.setTimeout(() => setFaixa(""), MS_FAIXA);
  }, [fase, pendDestaque]);
  useEffect(
    () => () => {
      window.clearTimeout(tDestaque.current);
      window.clearTimeout(tFaixa.current);
    },
    [],
  );

  // Trocou de fase interna (avaliação -> pedido -> como pagar): volta ao topo, sem herdar a rolagem anterior.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [fase]);

  const combinacoes = res?.combinacoes ?? [];
  const meuPid = lerPid(salaId);

  function fimLeilao() {
    marcarLeilaoVisto(salaId, sig);
    setFase("pedido");
  }

  // C14: manda a frase ao servidor, mostra o que ele entendeu, toca a avaliação curta e volta ao pedido.
  async function ajustar(texto: string) {
    if (ocupado) return;
    const id = Date.now();
    const token = lerToken(salaId);
    if (!token) {
      setTroca({ id, texto, estado: "erro", erro: "Sem permissão de organizador neste aparelho." });
      return;
    }
    const antes = res;
    const base = sigSala;
    setOcupado(true);
    setRetido(antes ?? null);
    setTroca({ id, texto, estado: "pensando" });
    try {
      const r = await api.ajustar(salaId, token, texto);
      const entendido = textoEntendido(r.entendido);
      setTroca({ id, texto, estado: "refazendo", entendido });
      await ESPERA(reduzirMovimento() ? 500 : 1100);
      setAnteriores(antes?.combinacoes);
      setLocal({ res: r.resultado, base });
      setRetido(null);
      setPendDestaque(true);
      setHistLocal((h) => [...h, { texto, resumo: entendido }]);
      setTroca({ id, texto, estado: "pronto", entendido });
      if (r.resultado.leilao) {
        setLeilaoCurto(r.resultado.leilao);
        setFase("leilao-curto");
      } else {
        marcarLeilaoVisto(salaId, assinatura(r.resultado));
        setFase("pedido");
      }
    } catch (x) {
      setRetido(null);
      setTroca({ id, texto, estado: "erro", erro: mensagemAjuste(x) });
    } finally {
      setOcupado(false);
    }
  }

  function fimLeilaoCurto() {
    marcarLeilaoVisto(salaId, sig);
    setFase("pedido");
  }

  // A API continua recebendo o índice da combinação (C7); o resultado mostra só a melhor, a 0.
  async function montar(formaPag: ModoPagamento = modo) {
    const token = lerToken(salaId);
    if (!token) {
      setErro("Sem permissão de organizador neste aparelho.");
      return;
    }
    setMontando(true);
    setErro("");
    try {
      await api.escolher(salaId, token, 0, formaPag);
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui montar o pedido.");
    } finally {
      setMontando(false);
    }
  }

  if (fase === "leilao" && leilao) {
    return <Leilao leilao={leilao} rastro={sala.rastro} organizador={organizador} onFim={fimLeilao} />;
  }
  if (fase === "leilao-curto" && leilaoCurto) {
    return <Leilao leilao={leilaoCurto} rastro={[]} organizador={organizador} onFim={fimLeilaoCurto} compacto />;
  }

  const comb = combinacoes[0];
  if (!comb) {
    return (
      <section className="tela">
        <div className="cartao centro">
          <h1>Nenhuma combinação coube</h1>
          <p className="suave">As restrições e orçamentos deste grupo não encontraram opções no cardápio.</p>
          {res?.avisos.map((a, i) => (
            <p key={i} className="aviso">
              {a}
            </p>
          ))}
        </div>
        <Rastro itens={sala.rastro} />
      </section>
    );
  }

  if (fase === "pedido" || fase === "leilao-curto" || !organizador) {
    const servidor: ItemHistorico[] = (sala.ajustes ?? []).map((a) => ({ texto: a.texto, resumo: resumoAjuste(a) }));
    const todos = servidor.length >= histLocal.length ? servidor : histLocal;
    // A última troca já aparece em bolhas; o recolhível guarda só as anteriores.
    const historico = troca?.estado === "pronto" ? todos.slice(0, -1) : todos;
    return (
      <>
        <Deck
          key={sig}
          sala={sala}
          combinacoes={combinacoes}
          avisos={[...new Set(res?.avisos ?? [])]}
          organizador={organizador}
          meuPid={meuPid}
          solo={solo}
          fechando={solo && montando}
          erroFechar={solo ? erro : ""}
          onConfirmar={() => {
            // Sala de 1 pessoa: não há o que dividir, então fecha direto como "junto".
            if (solo) void montar("junto");
            else setFase("escolha");
          }}
          onVerLeilao={leilao ? () => setFase("leilao") : undefined}
          ocupado={ocupado}
          atualizado={atualizado}
          faixa={faixa}
          onFecharFaixa={() => setFaixa("")}
          anteriores={anteriores}
          rodape={
            organizador ? (
              <Ajustar
                participantes={sala.participantes}
                troca={troca}
                historico={historico}
                ocupado={ocupado}
                onEnviar={ajustar}
              />
            ) : undefined
          }
        />
        <Rastro itens={sala.rastro} />
      </>
    );
  }

  // Fase "escolha" (só organizador): resumo do pedido confirmado + junto/separado.
  const grupos = agruparPorPessoa(comb.escolhas);
  const nomeDe = (pid: string) => sala.participantes.find((p) => p.id === pid)?.nome ?? "Convidado";
  const pids = Object.keys(grupos);
  const totalItens = Math.round(Object.values(comb.escolhas).reduce((s, c) => s + c.preco, 0) * 100) / 100;
  const nLojas = comb.lojas.length;
  const explicacao = comb.explicacao ?? "";
  const avisos = [...new Set(res?.avisos ?? [])].filter((a) => !explicacao.includes(a));
  const modos = textoModos(nLojas);

  return (
    <section className="tela">
      <button type="button" className="link-btn ld-voltar" onClick={() => setFase("pedido")}>
        ‹ Voltar ao pedido
      </button>
      <h1>Como pagar?</h1>

      <div className="cartao">
        <h2>
          {nLojas} {nLojas === 1 ? "loja" : "lojas"} · itens {brl(totalItens)}
        </h2>
        {!/taxa/i.test(comb.explicacao ?? "") && !avisos.some((a) => /taxa/i.test(a)) && (
          <p className="suave">
            {comb.taxa_conhecida
              ? "A taxa de entrega já está considerada na escolha."
              : "Taxa de entrega: calculada ao montar o carrinho."}
          </p>
        )}
        {comb.explicacao && <p>{comb.explicacao}</p>}
        {avisos.map((a, i) => (
          <p key={i} className="aviso">
            {a}
          </p>
        ))}
      </div>

      <div className="pessoas">
        {pids.map((pid) => (
          <CartaoPessoa key={pid} nome={nomeDe(pid)} itens={juntarIguais(grupos[pid])} destaque={pid === meuPid && !!meuPid} />
        ))}
      </div>

      <fieldset className="modos">
        <legend>Como pagar?</legend>
        {modos.map((m) => (
          <label key={m.id} className={`modo ${modo === m.id ? "on" : ""}`}>
            <input type="radio" name="modo" checked={modo === m.id} onChange={() => setModo(m.id)} />
            <span>
              <strong>{m.titulo}</strong>
              <small>{m.texto}</small>
              {m.destaque && <small className="ld-cobrancas">{m.destaque}</small>}
            </span>
          </label>
        ))}
      </fieldset>
      {erro && <p className="erro">{erro}</p>}
      <button className="primario" disabled={montando} onClick={() => montar()}>
        {montando ? "Montando carrinhos…" : "Montar pedido"}
      </button>
      <p className="suave centro-txt">Nada é enviado ao iFood ainda: você revisa antes.</p>

      <Rastro itens={sala.rastro} />
    </section>
  );
}
