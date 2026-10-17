import { useEffect, useState } from "react";

/** Interpreta o ISO do servidor; sem fuso informado, assume UTC. */
export function paraMs(iso: string): number {
  const t = /(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`;
  return new Date(t).getTime();
}

/** Milissegundos restantes até o prazo (atualiza a cada segundo). */
export function useRestante(prazoFim?: string): number | null {
  const [agora, setAgora] = useState(() => Date.now());
  useEffect(() => {
    if (!prazoFim) return;
    const t = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(t);
  }, [prazoFim]);
  if (!prazoFim) return null;
  const fim = paraMs(prazoFim);
  return Number.isFinite(fim) ? fim - agora : null;
}

export default function ContadorPrazo({ prazoFim }: { prazoFim: string }) {
  const resta = useRestante(prazoFim);
  if (resta == null) return null;
  if (resta <= 0) {
    return (
      <div className="contador contador-fim" role="timer">
        <span>Prazo para pagar</span>
        <strong>Prazo encerrado</strong>
      </div>
    );
  }
  const seg = Math.ceil(resta / 1000);
  const mm = String(Math.floor(seg / 60)).padStart(2, "0");
  const ss = String(seg % 60).padStart(2, "0");
  return (
    <div className={`contador ${seg <= 60 ? "contador-urgente" : ""}`} role="timer" aria-live="off">
      <span>Prazo para pagar</span>
      <strong>
        {mm}:{ss}
      </strong>
    </div>
  );
}
