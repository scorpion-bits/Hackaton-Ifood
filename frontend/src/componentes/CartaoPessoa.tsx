import type { Candidato } from "../tipos";

const FMT = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** Só formata: o valor sempre vem da API. */
export function brl(v: number | null | undefined): string {
  return typeof v === "number" && Number.isFinite(v) ? FMT.format(v) : "—";
}

/** Itens de carrinho/pedido têm formato livre na API: aceita texto ou objeto. */
export function rotuloItem(i: unknown): string {
  if (typeof i === "string") return i;
  if (i && typeof i === "object") {
    const o = i as Record<string, unknown>;
    const nome = o.name ?? o.nome ?? o.item_nome ?? o.itemName;
    const qtd = o.quantity ?? o.quantidade ?? o.qtd;
    if (typeof nome === "string") {
      return typeof qtd === "number" && qtd > 1 ? `${qtd}× ${nome}` : nome;
    }
  }
  return "Item";
}

export function precoItem(i: unknown): number | null {
  if (i && typeof i === "object") {
    const o = i as Record<string, unknown>;
    const v = o.totalPrice ?? o.total ?? o.preco ?? o.price;
    if (typeof v === "number") return v;
  }
  return null;
}

function fracao(nota: number): number {
  const n = nota > 1 ? nota / 100 : nota;
  return Math.max(0, Math.min(1, n));
}

const ALERGENO = /confirme com a loja/i;

export default function CartaoPessoa({
  nome,
  itens,
  destaque,
}: {
  nome: string;
  itens: Candidato[];
  destaque?: boolean;
}) {
  const subtotal = Math.round(itens.reduce((s, c) => s + c.preco, 0) * 100) / 100;
  return (
    <article className={`pessoa ${destaque ? "pessoa-eu" : ""}`}>
      <header className="pessoa-topo">
        <span className="avatar" aria-hidden>
          {nome.trim().charAt(0).toUpperCase() || "?"}
        </span>
        <strong>
          {nome}
          {destaque ? " (você)" : ""}
        </strong>
        {itens.length > 1 && <span className="pessoa-sub">{brl(subtotal)}</span>}
      </header>
      {itens.length === 0 && <p className="suave">Nenhum item coube nas restrições desta pessoa.</p>}
      <ul className="pessoa-itens">
        {itens.map((c, k) => {
          const pct = Math.round(fracao(c.nota) * 100);
          return (
            <li key={`${c.item_id}-${k}`}>
              <div className="item-linha">
                <span className="item-nome">{c.item_nome}</span>
                <span className="item-preco">{brl(c.preco)}</span>
              </div>
              <div className="item-loja">
                {c.loja_nome}
                {c.eta_min != null ? ` · ~${c.eta_min} min` : ""}
              </div>
              <div className="nota" role="img" aria-label={`Combina ${pct}%`}>
                <span className="nota-barra">
                  <span style={{ width: `${pct}%` }} />
                </span>
                <small>combina {pct}%</small>
              </div>
              {c.motivo && <p className="item-motivo">{c.motivo}</p>}
              {ALERGENO.test(c.motivo) && (
                <p className="alerta-alergeno">
                  Atenção: alergia ou restrição pode não estar informada no cardápio. Confirme com a loja.
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </article>
  );
}
