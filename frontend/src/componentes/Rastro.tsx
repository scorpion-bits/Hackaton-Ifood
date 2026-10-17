import type { ChamadaRastro } from "../tipos";

export default function Rastro({ itens, aberto }: { itens: ChamadaRastro[]; aberto?: boolean }) {
  if (!itens.length) return null;
  return (
    <details className="rastro" open={aberto}>
      <summary>Como a IA chegou aqui ({itens.length} chamadas ao MCP)</summary>
      <ul>
        {itens.map((c, i) => (
          <li key={i} className={c.ok ? "" : "falhou"}>
            <span className="rastro-ico">{c.ok ? "✓" : "✗"}</span>
            <span className="rastro-tool">{c.tool}</span>
            <span className="rastro-ms">{c.ms} ms</span>
            <span className="rastro-resumo">{c.resumo}{c.erro ? ` — ${c.erro}` : ""}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
