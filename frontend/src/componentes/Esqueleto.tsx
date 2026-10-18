/** Estado de carregamento: blocos cinza que brilham (nunca spinner). */
export function Esqueleto({ altura = 96, largura }: { altura?: number; largura?: string }) {
  return <div className="esqueleto" style={{ height: altura, width: largura }} aria-hidden="true" />;
}

export default function EsqueletoCartoes({ n = 2, rotulo = "Carregando…" }: { n?: number; rotulo?: string }) {
  return (
    <div className="esqueleto-grupo" role="status" aria-live="polite" aria-busy="true">
      <span className="sr">{rotulo}</span>
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="cartao esqueleto-cartao" aria-hidden="true">
          <div className="esqueleto" style={{ height: 18, width: "55%" }} />
          <div className="esqueleto" style={{ height: 12, width: "90%" }} />
          <div className="esqueleto" style={{ height: 12, width: "70%" }} />
        </div>
      ))}
    </div>
  );
}
