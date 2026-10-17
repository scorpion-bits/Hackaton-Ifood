import { useEffect, useState } from "react";
import { api, lerLocal } from "./api";
import type { EstadoSala } from "./tipos";
import Selo from "./componentes/Selo";
import Rastro from "./componentes/Rastro";
import Inicio from "./telas/Inicio";
import Organizador from "./telas/Organizador";
import Convidado from "./telas/Convidado";

type Rota =
  | { tipo: "inicio" }
  | { tipo: "convidado"; id: string }
  | { tipo: "org"; id: string };

function lerRota(): Rota {
  const h = window.location.hash.replace(/^#/, "");
  const m = h.match(/^\/s\/([^/]+)(\/org)?\/?$/);
  if (m) return m[2] ? { tipo: "org", id: decodeURIComponent(m[1]) } : { tipo: "convidado", id: decodeURIComponent(m[1]) };
  return { tipo: "inicio" };
}

function useRota(): Rota {
  const [r, setR] = useState<Rota>(lerRota);
  useEffect(() => {
    const f = () => setR(lerRota());
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return r;
}

/** Polling de 2 s em GET /api/salas/{id}. */
function useSala(id: string): { sala: EstadoSala | null; erro: string } {
  const [sala, setSala] = useState<EstadoSala | null>(null);
  const [erro, setErro] = useState("");
  useEffect(() => {
    let vivo = true;
    setSala(null);
    const tick = async () => {
      try {
        const s = await api.estado(id);
        if (vivo) {
          setSala(s);
          setErro("");
        }
      } catch (x) {
        if (vivo) setErro(x instanceof Error ? x.message : "Sem conexão.");
      }
    };
    tick();
    const t = setInterval(tick, 2000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, [id]);
  return { sala, erro };
}

const ROTULO_FASE: Record<string, string> = {
  match_pronto: "Resultado do Match",
  aguardando_pagamentos: "Revisão e pagamento",
  pronto_para_enviar: "Pronto para enviar",
  enviado: "Pedidos",
};

// Placeholder: Resultado, Pagamento e Pedidos serão telas próprias (outra tarefa).
function PlaceholderFase({ sala, organizador }: { sala: EstadoSala; organizador: boolean }) {
  return (
    <section className="tela">
      <div className="cartao centro">
        <h1>{ROTULO_FASE[sala.estado] ?? sala.estado}</h1>
        <p className="suave">
          {organizador
            ? "Esta etapa ainda está em construção."
            : sala.estado === "match_pronto"
              ? "O organizador está escolhendo a melhor combinação."
              : "O organizador está cuidando do pedido."}
        </p>
        {sala.resultado && (
          <p>
            {sala.resultado.combinacoes.length} combinação(ões) encontrada(s).
          </p>
        )}
      </div>
      <Rastro itens={sala.rastro} />
    </section>
  );
}

function TelaSala({ rota }: { rota: Extract<Rota, { tipo: "convidado" | "org" }> }) {
  const { sala, erro } = useSala(rota.id);
  const org = rota.tipo === "org";

  return (
    <div className="app-sala">
      <header className="topo-sala">
        <a href="#/" className="voltar" aria-label="Voltar ao início">‹</a>
        <strong>Match</strong>
        <span />
      </header>
      <Selo ativo={!!sala?.demonstracao} />
      {erro && !sala && (
        <div className="cartao centro">
          <p className="erro">{erro}</p>
          <a href="#/">Voltar ao início</a>
        </div>
      )}
      {!sala && !erro && <p className="suave centro-txt">Carregando…</p>}
      {sala && (
        <>
          {sala.estado === "coletando" ? (
            org ? (
              <Organizador salaId={rota.id} sala={sala} nomeOrg={lerLocal<string>(`match.nome.${rota.id}`) ?? ""} />
            ) : (
              <Convidado salaId={rota.id} sala={sala} />
            )
          ) : (
            <PlaceholderFase sala={sala} organizador={org} />
          )}
          {sala.estado === "coletando" && sala.rastro.length > 0 && <Rastro itens={sala.rastro} />}
        </>
      )}
      <p className="rodape">Protótipo de hackathon · não é o app oficial do iFood</p>
    </div>
  );
}

export default function App() {
  const rota = useRota();
  return (
    <div className="app">
      {rota.tipo === "inicio" ? <Inicio /> : <TelaSala rota={rota} />}
    </div>
  );
}
