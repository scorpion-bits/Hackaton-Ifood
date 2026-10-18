import { useEffect, useState } from "react";
import { gravarLocal, chaveOrg } from "../../api";
import Selo from "../Selo";
import Resultado from "../../telas/Resultado";
import { leilaoVistoChave, leilaoVisto } from "./util";
import { instalarApiFalsa, salaExemplo } from "./exemplo";

/** Página de desenvolvimento: #/leilao-exemplo (organizador) e #/leilao-exemplo/convidado. Não vai para a produção. */
export default function PaginaExemplo({ organizador }: { organizador: boolean }) {
  const [rodada, setRodada] = useState(0);
  useEffect(() => {
    if (organizador) gravarLocal(chaveOrg("exemplo"), "token-exemplo");
    return instalarApiFalsa();
  }, [organizador]);

  function rever() {
    try {
      localStorage.removeItem(leilaoVistoChave("exemplo"));
    } catch {
      /* ignora */
    }
    setRodada((r) => r + 1);
  }

  return (
    <div className="app-sala">
      <header className="topo-sala">
        <a href="#/" className="voltar" aria-label="Voltar ao início">‹</a>
        <strong>Match</strong>
        <span />
      </header>
      <Selo ativo />
      <p className="centro-txt">
        Fixture de desenvolvimento ({organizador ? "organizador" : "convidado"}). Leilão {leilaoVisto("exemplo") ? "já visto" : "ainda não visto"}.{" "}
        <button type="button" className="link-btn" onClick={rever}>
          Reiniciar
        </button>
      </p>
      <Resultado key={rodada} salaId="exemplo" sala={salaExemplo} organizador={organizador} />
    </div>
  );
}
