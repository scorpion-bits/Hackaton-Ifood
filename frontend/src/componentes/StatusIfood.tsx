import { useEffect, useState } from "react";
import { api, limparMatchLocal } from "../api";
import type { StatusIfood as Status } from "../tipos";

/** Consulta /api/ifood/status. Se a rota falhar, assume demo (comportamento anterior). */
export function useStatusIfood(): { status: Status | null; recarregar: () => void } {
  const [status, setStatus] = useState<Status | null>(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    let vivo = true;
    api
      .ifoodStatus()
      .then((s) => vivo && setStatus(s))
      .catch(() => vivo && setStatus({ modo: "demo", conectado: false }));
    return () => {
      vivo = false;
    };
  }, [n]);
  return { status, recarregar: () => setN((x) => x + 1) };
}

/** Só aparece no modo real. No demo o selo já informa. */
export default function StatusIfood() {
  const { status, recarregar } = useStatusIfood();
  const [saindo, setSaindo] = useState(false);
  if (!status || status.modo !== "real") return null;

  async function sair() {
    setSaindo(true);
    try {
      await api.ifoodSair();
    } catch {
      /* mostra o estado real abaixo */
    }
    setSaindo(false);
    recarregar();
  }

  return (
    <div className="status-ifood">
      {status.conectado ? (
        <>
          <span className="chip-conectado">iFood conectado{status.conta ? ` · ${status.conta}` : ""}</span>
          <button type="button" className="link-btn" onClick={sair} disabled={saindo}>
            Sair
          </button>
        </>
      ) : (
        <a className="btn-conectar" href="/oauth/login">
          Conectar iFood
        </a>
      )}
    </div>
  );
}

/** Botão discreto, só no modo demo. */
export function RecarregarDemo() {
  const { status } = useStatusIfood();
  if (!status || status.modo !== "demo") return null;

  async function recarregar() {
    if (!window.confirm("Recarregar a demo? Salas e pedidos de teste serão apagados.")) return;
    try {
      await api.resetar();
    } catch {
      /* segue: limpa o aparelho de qualquer forma */
    }
    limparMatchLocal();
    window.location.hash = "#/";
    window.location.reload();
  }

  return (
    <button type="button" className="link-btn centro-btn" onClick={recarregar}>
      Recarregar demo
    </button>
  );
}
