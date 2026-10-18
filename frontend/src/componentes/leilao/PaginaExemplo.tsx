import { useEffect, useState } from "react";
import { gravarLocal, chaveOrg } from "../../api";
import Selo from "../Selo";
import Marca from "../Marca";
import Resultado from "../../telas/Resultado";
import { assinatura, leilaoVistoChave, leilaoVisto } from "./util";
import { instalarApiFalsa, salaAjustada, salaExemplo } from "./exemplo";

/** Página de desenvolvimento: #/leilao-exemplo (organizador) e #/leilao-exemplo/convidado. Não vai para a produção. */
export default function PaginaExemplo({ organizador }: { organizador: boolean }) {
  const [rodada, setRodada] = useState(0);
  const [sala, setSala] = useState(salaExemplo);
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
    setSala(salaExemplo);
    setRodada((r) => r + 1);
  }

  return (
    <div className="app-sala">
      <header className="topo-sala">
        <a href="#/" className="voltar" aria-label="Voltar ao início">‹</a>
        <strong className="topo-logo"><Marca altura={34} /></strong>
        <span />
      </header>
      <Selo ativo />
      <p className="centro-txt">
        Fixture de desenvolvimento ({organizador ? "organizador" : "convidado"}). Leilão {leilaoVisto("exemplo", assinatura(sala.resultado)) ? "já visto" : "ainda não visto"}.{" "}
        <button type="button" className="link-btn" onClick={rever}>
          Reiniciar
        </button>
        {!organizador && (
          <>
            {" "}
            <button type="button" className="link-btn" onClick={() => setSala(salaAjustada)}>
              Simular ajuste do organizador
            </button>
          </>
        )}
        {organizador && " Dica: digite uma frase com “erro” (422) ou “fora” (409) para ver as mensagens."}
      </p>
      <Resultado key={rodada} salaId="exemplo" sala={sala} organizador={organizador} />
    </div>
  );
}
