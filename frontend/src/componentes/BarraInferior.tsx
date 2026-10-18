import Icone, { type NomeIcone } from "./Icone";

export type AbaBarra = "inicio" | "busca" | "match" | "pedidos" | "perfil";

const ABAS: { id: AbaBarra; rotulo: string; icone: NomeIcone; ativo: boolean }[] = [
  { id: "inicio", rotulo: "Início", icone: "casa", ativo: true },
  { id: "busca", rotulo: "Busca", icone: "busca", ativo: false },
  { id: "match", rotulo: "Match", icone: "coracao", ativo: true },
  { id: "pedidos", rotulo: "Pedidos", icone: "recibo", ativo: false },
  { id: "perfil", rotulo: "Perfil", icone: "pessoa", ativo: false },
];

export default function BarraInferior({
  atual,
  onIr,
  onInerte,
}: {
  atual: AbaBarra;
  onIr: (a: AbaBarra) => void;
  /** Toque em aba que não existe neste protótipo (mostra um aviso curto). */
  onInerte?: () => void;
}) {
  return (
    <nav className="barra-inferior" aria-label="Navegação">
      {ABAS.map((a) => (
        <button
          key={a.id}
          type="button"
          className={`aba-barra ${a.id === "match" ? "central" : ""} ${a.id === atual ? "atual" : ""}`}
          aria-disabled={!a.ativo || undefined}
          aria-current={a.id === atual ? "page" : undefined}
          aria-label={a.id === "match" ? "Match: criar um pedido em grupo" : undefined}
          onClick={a.ativo ? () => onIr(a.id) : onInerte}
        >
          <span className="ico">
            <Icone nome={a.icone} tamanho={a.id === "match" ? 26 : 24} />
          </span>
          <span>{a.rotulo}</span>
        </button>
      ))}
    </nav>
  );
}
