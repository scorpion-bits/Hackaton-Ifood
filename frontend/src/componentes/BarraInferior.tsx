export type AbaBarra = "inicio" | "busca" | "match" | "pedidos" | "perfil";

const ABAS: { id: AbaBarra; rotulo: string; icone: string; ativo: boolean }[] = [
  { id: "inicio", rotulo: "Início", icone: "🏠", ativo: true },
  { id: "busca", rotulo: "Busca", icone: "🔍", ativo: false },
  { id: "match", rotulo: "Match", icone: "✨", ativo: true },
  { id: "pedidos", rotulo: "Pedidos", icone: "🧾", ativo: false },
  { id: "perfil", rotulo: "Perfil", icone: "👤", ativo: false },
];

export default function BarraInferior({
  atual,
  onIr,
}: {
  atual: AbaBarra;
  onIr: (a: AbaBarra) => void;
}) {
  return (
    <nav className="barra-inferior" aria-label="Navegação">
      {ABAS.map((a) => (
        <button
          key={a.id}
          type="button"
          className={`aba-barra ${a.id === "match" ? "central" : ""} ${a.id === atual ? "atual" : ""}`}
          aria-disabled={!a.ativo}
          aria-current={a.id === atual ? "page" : undefined}
          onClick={a.ativo ? () => onIr(a.id) : undefined}
        >
          <span className="ico">{a.icone}</span>
          <span>{a.rotulo}</span>
        </button>
      ))}
    </nav>
  );
}
