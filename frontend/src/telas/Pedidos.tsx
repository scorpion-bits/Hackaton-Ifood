import { useState } from "react";
import { api } from "../api";
import type { Carrinho, EstadoSala } from "../tipos";
import { brl, rotuloItem } from "../componentes/CartaoPessoa";
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
  return (
    <ol className="linha-tempo" aria-label="Andamento do pedido">
      {PASSOS.map((p, i) => (
        <li key={p.code} className={i < atual ? "feito" : i === atual ? "atual" : ""}>
          <span className="bolinha" aria-hidden />
          <span>{p.rotulo}</span>
        </li>
      ))}
    </ol>
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

  return (
    <section className="tela">
      <h1>Pedidos</h1>
      <p className="suave">
        {enviados} {enviados === 1 ? "pedido enviado" : "pedidos enviados"} ao iFood.
      </p>

      {pedidos.length === 0 && <div className="cartao centro suave">Aguardando os pedidos…</div>}

      {pedidos.map((p, i) => {
        if (p.falhou) {
          return (
            <div key={p.orderId || `f${i}`} className="cartao pedido-falha" role="alert">
              <h2>{p.lojaNome}: o pedido não foi enviado</h2>
              <p>{p.erro || p.descricao || "O iFood recusou este pedido."}</p>
              <p className="aviso">O Match sugere: escolher outra loja para essa parte.</p>
            </div>
          );
        }
        const idx = rank(p.status);
        const rotulo = idx >= 0 ? PASSOS[idx].rotulo : "Pedido enviado";
        return (
          <div key={p.orderId || i} className="cartao pedido">
            <div className="parte-linha">
              <h2>{p.lojaNome}</h2>
              <strong>{brl(p.total)}</strong>
            </div>
            <ul className="itens-cart">
              {p.itens.map((it, k) => (
                <li key={k}>{rotuloItem(it)}</li>
              ))}
            </ul>
            <p className="status-atual">
              <strong>{rotulo}</strong>
              {p.descricao && <small> · {p.descricao}</small>}
            </p>
            <Linha status={p.status} />
            {erros[p.orderId] && <p className="erro">{erros[p.orderId]}</p>}
            <button className="secundario" disabled={ocupado === p.orderId || idx === PASSOS.length - 1} onClick={() => atualizar(p.orderId)}>
              {ocupado === p.orderId ? "Atualizando…" : idx === PASSOS.length - 1 ? "Pedido concluído" : "Atualizar status"}
            </button>
          </div>
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

      <Rastro itens={sala.rastro} />
    </section>
  );
}
