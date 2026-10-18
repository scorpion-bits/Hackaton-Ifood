import { useEffect, useState } from "react";
import { api, lerToken } from "../api";
import type { EstadoSala, ModoPagamento } from "../tipos";
import CartaoPessoa, { brl } from "../componentes/CartaoPessoa";
import Rastro from "../componentes/Rastro";
import { agruparPorPessoa, juntarIguais, leilaoVisto, marcarLeilaoVisto } from "../componentes/leilao/util";
import { lerPid } from "./Convidado";
import Leilao from "./Leilao";
import Deck from "./Deck";
import "../leilao.css";

type Fase = "leilao" | "deck" | "escolha";

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
 * match_pronto (C13): disputa das lojas (1 vez por aparelho) -> deck -> "É um Match!" -> escolha de pagamento.
 * Convidado vê a disputa e o deck só para leitura.
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
  const res = sala.resultado;
  const leilao = res?.leilao;
  const [fase, setFase] = useState<Fase>(() => (leilao && !leilaoVisto(salaId) ? "leilao" : "deck"));
  const [escolhida, setEscolhida] = useState(0);
  const [modo, setModo] = useState<ModoPagamento>("junto");
  const [montando, setMontando] = useState(false);
  const [erro, setErro] = useState("");

  // Trocou de fase interna (disputa -> opções -> como pagar): volta ao topo, sem herdar a rolagem anterior.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [fase]);

  const combinacoes = res?.combinacoes ?? [];
  const meuPid = lerPid(salaId);

  function fimLeilao() {
    marcarLeilaoVisto(salaId);
    setFase("deck");
  }

  async function montar() {
    const token = lerToken(salaId);
    if (!token) {
      setErro("Sem permissão de organizador neste aparelho.");
      return;
    }
    setMontando(true);
    setErro("");
    try {
      await api.escolher(salaId, token, escolhida, modo);
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui montar o pedido.");
    } finally {
      setMontando(false);
    }
  }

  if (fase === "leilao" && leilao) {
    return <Leilao leilao={leilao} rastro={sala.rastro} organizador={organizador} onFim={fimLeilao} />;
  }

  const comb = combinacoes[Math.min(escolhida, Math.max(combinacoes.length - 1, 0))];
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

  if (fase === "deck" || !organizador) {
    return (
      <>
        <Deck
          sala={sala}
          combinacoes={combinacoes}
          avisos={[...new Set(res?.avisos ?? [])]}
          organizador={organizador}
          meuPid={meuPid}
          onEscolher={(i) => {
            setEscolhida(i);
            setFase("escolha");
          }}
          onVerLeilao={leilao ? () => setFase("leilao") : undefined}
        />
        <Rastro itens={sala.rastro} />
      </>
    );
  }

  // Fase "escolha" (só organizador): detalhe da opção que deu match + junto/separado.
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
      <button type="button" className="link-btn ld-voltar" onClick={() => setFase("deck")}>
        ‹ Voltar às opções
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
      <button className="primario" disabled={montando} onClick={montar}>
        {montando ? "Montando carrinhos…" : "Montar pedido"}
      </button>
      <p className="suave centro-txt">Nada é enviado ao iFood ainda: você revisa antes.</p>

      <Rastro itens={sala.rastro} />
    </section>
  );
}
