import { useState } from "react";
import { api, lerToken } from "../api";
import type { Candidato, EstadoSala, ModoPagamento } from "../tipos";
import CartaoPessoa, { brl } from "../componentes/CartaoPessoa";
import Rastro from "../componentes/Rastro";
import { lerPid } from "./Convidado";

/** Slots "pid" e "pid#k" viram uma lista por pessoa. */
function agruparPorPessoa(escolhas: Record<string, Candidato>): Record<string, Candidato[]> {
  const g: Record<string, Candidato[]> = {};
  for (const [slot, c] of Object.entries(escolhas)) {
    const pid = slot.split("#")[0];
    (g[pid] ??= []).push(c);
  }
  return g;
}

const MODOS: { id: ModoPagamento; titulo: string; texto: string }[] = [
  { id: "junto", titulo: "Pagar tudo de uma vez", texto: "Você paga o total no iFood e acerta com o pessoal depois." },
  {
    id: "separado",
    titulo: "Cada um paga a sua parte (vaquinha)",
    texto: "Cada pessoa paga a própria parte e os pedidos só saem quando todos pagarem.",
  },
];

export default function Resultado({
  salaId,
  sala,
  organizador,
}: {
  salaId: string;
  sala: EstadoSala;
  organizador: boolean;
}) {
  const [idx, setIdx] = useState(0);
  const [modo, setModo] = useState<ModoPagamento>("junto");
  const [montando, setMontando] = useState(false);
  const [erro, setErro] = useState("");

  const res = sala.resultado;
  const combinacoes = res?.combinacoes ?? [];
  const comb = combinacoes[Math.min(idx, Math.max(combinacoes.length - 1, 0))];
  const meuPid = lerPid(salaId);

  async function montar() {
    const token = lerToken(salaId);
    if (!token) {
      setErro("Sem permissão de organizador neste aparelho.");
      return;
    }
    setMontando(true);
    setErro("");
    try {
      await api.escolher(salaId, token, idx, modo);
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui montar o pedido.");
    } finally {
      setMontando(false);
    }
  }

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

  const grupos = agruparPorPessoa(comb.escolhas);
  const nomeDe = (pid: string) => sala.participantes.find((p) => p.id === pid)?.nome ?? "Convidado";
  // Convidado: só a parte dele (se não sabemos quem é, mostra tudo em leitura).
  const pids = Object.keys(grupos).filter((pid) => organizador || !meuPid || pid === meuPid);
  const totalItens = Math.round(Object.values(comb.escolhas).reduce((s, c) => s + c.preco, 0) * 100) / 100;
  const nLojas = comb.lojas.length;

  return (
    <section className="tela">
      <h1>{organizador ? "Resultado do Match" : "Sua parte no Match"}</h1>

      {organizador && combinacoes.length > 1 && (
        <div className="segmentado" role="tablist" aria-label="Alternativas">
          {combinacoes.slice(0, 3).map((_, i) => (
            <button
              key={i}
              role="tab"
              aria-selected={i === idx}
              className={i === idx ? "on" : ""}
              onClick={() => setIdx(i)}
            >
              Opção {i + 1}
            </button>
          ))}
        </div>
      )}

      <div className="cartao">
        <h2>
          {nLojas} {nLojas === 1 ? "loja" : "lojas"} · itens {brl(totalItens)}
        </h2>
        <p className="suave">
          {comb.taxa_conhecida
            ? "A taxa de entrega já está considerada na escolha."
            : "Taxa de entrega: calculada ao montar o carrinho."}
        </p>
        {comb.explicacao && <p>{comb.explicacao}</p>}
        {res?.avisos.map((a, i) => (
          <p key={i} className="aviso">
            {a}
          </p>
        ))}
      </div>

      <div className="pessoas">
        {pids.map((pid) => (
          <CartaoPessoa key={pid} nome={nomeDe(pid)} itens={grupos[pid]} destaque={pid === meuPid && !!meuPid} />
        ))}
      </div>

      {organizador ? (
        <>
          <fieldset className="modos">
            <legend>Como pagar?</legend>
            {MODOS.map((m) => (
              <label key={m.id} className={`modo ${modo === m.id ? "on" : ""}`}>
                <input type="radio" name="modo" checked={modo === m.id} onChange={() => setModo(m.id)} />
                <span>
                  <strong>{m.titulo}</strong>
                  <small>{m.texto}</small>
                </span>
              </label>
            ))}
          </fieldset>
          {erro && <p className="erro">{erro}</p>}
          <button className="primario" disabled={montando} onClick={montar}>
            {montando ? "Montando carrinhos…" : "Montar pedido"}
          </button>
          <p className="suave centro-txt">Nada é enviado ao iFood ainda: você revisa antes.</p>
        </>
      ) : (
        <p className="suave centro-txt">O organizador está escolhendo a opção e o modo de pagamento.</p>
      )}

      <Rastro itens={sala.rastro} />
    </section>
  );
}
