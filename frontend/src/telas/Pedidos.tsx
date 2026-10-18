import { useEffect, useState } from "react";
import { api, chaveEncerrada, gravarLocal } from "../api";
import type { Carrinho, EstadoSala } from "../tipos";
import { brl, rotuloItem } from "../componentes/CartaoPessoa";
import Avatar from "../componentes/Avatar";
import { Esqueleto } from "../componentes/Esqueleto";
import Rastro from "../componentes/Rastro";

const PASSOS = [
  { code: "CONFIRMED", rotulo: "Confirmado" },
  { code: "PREPARING", rotulo: "Em preparo" },
  { code: "DISPATCHED", rotulo: "Saiu para entrega" },
  { code: "CONCLUDED", rotulo: "Entregue" },
];
const FALHAS = ["falhou", "FAILED", "CANCELLED", "CANCELED", "REJECTED", "total_mudou"];

interface PedidoVis {
  orderId: string;
  lojaId: string;
  lojaNome: string;
  total: number | null;
  itens: unknown[];
  status: string;
  descricao: string;
  erro: string;
  falhou: boolean;
}

function txt(v: unknown): string {
  return typeof v === "string" ? v : "";
}

/** O formato do pedido é livre na API: aceita trackOrder cru ({status:{code}}) ou texto. */
function normalizar(p: Record<string, unknown>, carrinhos: Carrinho[]): PedidoVis {
  const st = p.status;
  const code = typeof st === "string" ? st : txt((st as Record<string, unknown> | undefined)?.code);
  const desc =
    txt((st as Record<string, unknown> | undefined)?.description) || txt(p.descricao) || txt(p.mensagem) || txt(p.message);
  const lojaId = txt(p.loja_id) || txt(p.merchantId);
  const cart = carrinhos.find((c) => c.loja_id === lojaId);
  const total = typeof p.total === "number" ? p.total : (cart?.total ?? null);
  const itens = Array.isArray(p.itens) ? p.itens : Array.isArray(p.items) ? p.items : (cart?.itens ?? []);
  return {
    orderId: txt(p.order_id) || txt(p.orderId) || txt(p.id),
    lojaId,
    lojaNome: txt(p.loja_nome) || txt(p.merchantName) || cart?.loja_nome || "Loja",
    total,
    itens,
    status: code,
    descricao: desc,
    erro: txt(p.erro) || txt(p.error),
    falhou: FALHAS.includes(code) || !!p.erro,
  };
}

const rank = (s: string) => PASSOS.findIndex((x) => x.code === s);

function Linha({ status }: { status: string }) {
  const atual = rank(status);
  const w = atual < 0 ? 6 : 8 + (atual / (PASSOS.length - 1)) * 92;
  return (
    <>
      <div className="bar" aria-hidden="true">
        <i style={{ width: `${w}%` }} />
        <b style={{ left: `${w}%` }}>🛵</b>
      </div>
      <ol className="stl" aria-label="Andamento do pedido">
        {PASSOS.map((p, i) => (
          <li key={p.code} className={i < atual ? "feito" : i === atual ? "on atual" : ""} aria-current={i === atual ? "step" : undefined}>
            {i <= atual ? "✓ " : ""}
            {p.rotulo}
          </li>
        ))}
      </ol>
    </>
  );
}

export default function Pedidos({ salaId, sala }: { salaId: string; sala: EstadoSala; organizador: boolean }) {
  const carrinhos = sala.carrinhos ?? [];
  const [locais, setLocais] = useState<Record<string, PedidoVis>>({});
  const [ocupado, setOcupado] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});

  const pedidos = (sala.pedidos ?? []).map((p) => {
    const v = normalizar(p, carrinhos);
    const l = locais[v.orderId];
    // Usa a resposta local só se estiver mais adiantada que o polling.
    return l && rank(l.status) > rank(v.status) ? { ...v, status: l.status, descricao: l.descricao } : v;
  });
  const separado = sala.modo_pagamento === "separado";
  const partes = sala.partes ?? [];

  // Pedidos enviados = sala encerrada: a home deixa de mostrar "Sua sala está aberta" para ela.
  useEffect(() => {
    gravarLocal(chaveEncerrada(salaId), true);
  }, [salaId]);

  async function atualizar(orderId: string) {
    setOcupado(orderId);
    setErros((e) => ({ ...e, [orderId]: "" }));
    try {
      const r = await api.atualizarPedido(salaId, orderId);
      if (r && typeof r === "object") {
        setLocais((l) => ({ ...l, [orderId]: normalizar({ ...(r as Record<string, unknown>), orderId }, carrinhos) }));
      }
    } catch (x) {
      setErros((e) => ({ ...e, [orderId]: x instanceof Error ? x.message : "Não consegui atualizar." }));
    } finally {
      setOcupado("");
    }
  }

  const enviados = pedidos.filter((p) => !p.falhou).length;
  const falhas = pedidos.length - enviados;
  const tudoEntregue = pedidos.length > 0 && falhas === 0 && pedidos.every((p) => rank(p.status) === PASSOS.length - 1);
  const etas = carrinhos.map((c) => c.eta_min).filter((e): e is number => typeof e === "number");
  const previsto =
    etas.length && !tudoEntregue
      ? `Previsto: ~${Math.min(...etas)}${Math.max(...etas) !== Math.min(...etas) ? ` a ${Math.max(...etas)}` : ""} min${enviados > 1 ? ` · ${enviados} entregas` : ""}`
      : "";
  const titulo =
    pedidos.length === 0
      ? "Enviando os pedidos…"
      : falhas > 0
        ? enviados > 0
          ? `${enviados} de ${pedidos.length} pedidos saíram`
          : "Nenhum pedido saiu"
        : tudoEntregue
          ? "Tudo entregue"
          : "Pedidos enviados";

  return (
    <section className="tela">
      {pedidos.length > 0 && falhas === 0 && (
        <div className="feito-ic" aria-hidden="true">
          <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </div>
      )}
      <div className="tk-top">
        <h1 className="titulo">{titulo}</h1>
        <p className="sub" role="status">
          {tudoEntregue ? "Bom apetite!" : previsto || (pedidos.length ? "Acompanhe cada entrega aqui." : "Aguardando a resposta do iFood.")}
        </p>
      </div>

      {pedidos.length === 0 && (
        <div className="esqueleto-grupo" role="status" aria-busy="true">
          <span className="sr">Aguardando os pedidos…</span>
          <div className="cartao esqueleto-cartao" aria-hidden="true">
            <Esqueleto altura={20} largura="50%" />
            <Esqueleto altura={8} />
            <Esqueleto altura={12} largura="80%" />
          </div>
        </div>
      )}

      {pedidos.map((p, i) => {
        if (p.falhou) {
          return (
            <article key={p.orderId || `f${i}`} className="ord pedido-falha" role="alert">
              <header className="ord-h">
                <Avatar nome={p.lojaNome} tam="md" loja />
                <div>
                  <h2>{p.lojaNome}</h2>
                  <small className="lbl falha">Não saiu</small>
                </div>
              </header>
              <p>{p.erro || p.descricao || "O iFood recusou este pedido."}</p>
              <p className="aviso">O Match sugere: escolher outra loja para essa parte.</p>
            </article>
          );
        }
        const idx = rank(p.status);
        const rotulo = idx >= 0 ? PASSOS[idx].rotulo : p.descricao || "Pedido enviado";
        const concluido = idx === PASSOS.length - 1;
        return (
          <article key={p.orderId || i} className="ord pedido">
            <header className="ord-h">
              <Avatar nome={p.lojaNome} tam="md" loja />
              <div>
                <h2>{p.lojaNome}</h2>
                <small className="lbl">
                  {rotulo}
                  {idx >= 0 && p.descricao ? ` · ${p.descricao}` : ""}
                </small>
              </div>
              <strong className="ord-total">{brl(p.total)}</strong>
            </header>
            <Linha status={p.status} />
            {p.itens.length > 0 && (
              <ul className="itens-cart">
                {p.itens.map((it, k) => (
                  <li key={k}>{rotuloItem(it)}</li>
                ))}
              </ul>
            )}
            {erros[p.orderId] && <p className="erro" role="alert">{erros[p.orderId]}</p>}
            <button type="button" className="secundario" disabled={ocupado === p.orderId || concluido} onClick={() => atualizar(p.orderId)}>
              {ocupado === p.orderId ? "Atualizando…" : concluido ? "✓ Pedido concluído" : "Atualizar status"}
            </button>
          </article>
        );
      })}

      {separado && partes.length > 0 && (
        <div className="cartao">
          <h2>Acerto de contas</h2>
          <ul className="partes">
            {partes.map((p) => {
              const pag = sala.pagamentos?.[p.participante_id];
              return (
                <li key={p.participante_id} className="parte-linha">
                  <span>
                    {p.nome}
                    <small> · {pag?.status === "pago" ? "pago" : "pendente"}</small>
                  </span>
                  <strong>{brl(p.total)}</strong>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="rodape-acao">
        <a className="primario btn-link" href="#/">
          Fazer outro match
        </a>
      </div>

      <Rastro itens={sala.rastro} />
    </section>
  );
}
