import { lazy, Suspense, useEffect, useState } from "react";
import { api, lerLocal, ultimaSalaOrg } from "./api";
import type { EstadoSala } from "./tipos";
import StatusIfood from "./componentes/StatusIfood";
import Selo from "./componentes/Selo";
import Marca from "./componentes/Marca";
import Rastro from "./componentes/Rastro";
import Inicio from "./telas/Inicio";
import Organizador from "./telas/Organizador";
import Convidado from "./telas/Convidado";
import Resultado from "./telas/Resultado";
import Pagamento from "./telas/Pagamento";
import Pedidos from "./telas/Pedidos";

// Fixture do leilão: só existe em desenvolvimento (fica fora do pacote de produção).
const PaginaExemplo = import.meta.env.DEV ? lazy(() => import("./componentes/leilao/PaginaExemplo")) : null;

type Rota =
  | { tipo: "exemplo"; organizador: boolean }
  | { tipo: "inicio" }
  | { tipo: "conectado"; erro: string }
  | { tipo: "convidado"; id: string }
  | { tipo: "org"; id: string };

function lerRota(): Rota {
  const h0 = window.location.hash.replace(/^#/, "");
  const [h, consulta = ""] = h0.split("?");
  if (import.meta.env.DEV && /^\/leilao-exemplo(\/convidado)?\/?$/.test(h)) {
    return { tipo: "exemplo", organizador: !/convidado/.test(h) };
  }
  if (/^\/conectado\/?$/.test(h)) return { tipo: "conectado", erro: new URLSearchParams(consulta).get("erro") ?? "" };
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

function FaseSala({ salaId, sala, organizador }: { salaId: string; sala: EstadoSala; organizador: boolean }) {
  // Mudou a fase da sala: começa do topo (a rolagem da fase anterior não vale na nova tela).
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [sala.estado]);
  switch (sala.estado) {
    case "match_pronto":
      return <Resultado salaId={salaId} sala={sala} organizador={organizador} />;
    case "aguardando_pagamentos":
    case "pronto_para_enviar":
      return <Pagamento salaId={salaId} sala={sala} organizador={organizador} />;
    case "enviado":
      return <Pedidos salaId={salaId} sala={sala} organizador={organizador} />;
    default:
      return null;
  }
}

function TelaSala({ rota }: { rota: Extract<Rota, { tipo: "convidado" | "org" }> }) {
  const { sala, erro } = useSala(rota.id);
  const org = rota.tipo === "org";

  return (
    <div className="app-sala">
      <header className="topo-sala">
        <a href="#/" className="voltar" aria-label="Voltar ao início">‹</a>
        <strong className="topo-logo"><Marca altura={34} /></strong>
        <span />
      </header>
      <Selo ativo={!!sala?.demonstracao} contaTeste={!!sala?.conta_teste && !sala?.demonstracao} />
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
            <FaseSala salaId={rota.id} sala={sala} organizador={org} />
          )}
          {sala.estado === "coletando" && sala.rastro.length > 0 && <Rastro itens={sala.rastro} />}
        </>
      )}
      <p className="rodape">Protótipo de hackathon · não afiliado ao iFood</p>
    </div>
  );
}

function Conectado({ erro }: { erro: string }) {
  const sala = ultimaSalaOrg();
  return (
    <section className="tela tela-conectado">
      <div className="cartao centro">
        {erro ? (
          <>
            <h1>Não consegui conectar</h1>
            <p className="erro">{erro}</p>
            <StatusIfood />
          </>
        ) : (
          <>
            <div className="grande">✅</div>
            <h1>iFood conectado</h1>
            <p className="suave">Já pode voltar e rodar o Match.</p>
          </>
        )}
        <a className="primario" style={{ display: "block", textDecoration: "none", textAlign: "center" }}
          href={sala ? `#/s/${encodeURIComponent(sala)}/org` : "#/"}>
          Voltar
        </a>
      </div>
    </section>
  );
}

export default function App() {
  const rota = useRota();
  return (
    <div className="app">
      {rota.tipo === "exemplo" ? (
        PaginaExemplo && (
          <Suspense fallback={null}>
            <PaginaExemplo organizador={rota.organizador} />
          </Suspense>
        )
      ) : rota.tipo === "inicio" ? (
        <Inicio />
      ) : rota.tipo === "conectado" ? (
        <Conectado erro={rota.erro} />
      ) : (
        <TelaSala rota={rota} />
      )}
    </div>
  );
}
