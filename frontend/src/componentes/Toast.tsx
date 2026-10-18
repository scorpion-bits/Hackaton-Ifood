import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

/** Aviso curto que some sozinho. Devolve [elemento, mostrar]; renderize o elemento uma vez na tela. */
export function useToast(ms = 2400): [ReactNode, (msg: string) => void] {
  const [msg, setMsg] = useState("");
  const [vis, setVis] = useState(false);
  const t = useRef<number | undefined>(undefined);
  const mostrar = useCallback(
    (m: string) => {
      setMsg(m);
      setVis(true);
      window.clearTimeout(t.current);
      t.current = window.setTimeout(() => setVis(false), ms);
    },
    [ms],
  );
  useEffect(() => () => window.clearTimeout(t.current), []);
  const el = (
    <div className={`toast ${vis ? "show" : ""}`} role="status" aria-live="polite">
      {vis ? msg : ""}
    </div>
  );
  return [el, mostrar];
}

export const MSG_FORA_PROTOTIPO = "Fora deste protótipo — use o Match";
