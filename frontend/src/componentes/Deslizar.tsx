import { useEffect, useRef, useState, type CSSProperties, type PointerEvent } from "react";
import Icone from "./Icone";

/**
 * "Deslize para enviar". Só pede a confirmação (onConfirmar); quem envia é a folha de resumo.
 * Alternativas sem gesto: Enter/Espaço no botão redondo e o botão "Enviar sem deslizar" (feito pela tela).
 * `emEspera`: enquanto a folha de resumo está aberta; ao fechar, o botão volta ao início.
 */
export default function Deslizar({
  bloqueado,
  rotulo,
  rotuloBloqueado,
  emEspera,
  onConfirmar,
}: {
  bloqueado: boolean;
  rotulo: string;
  rotuloBloqueado: string;
  emEspera: boolean;
  onConfirmar: () => void;
}) {
  const trilho = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const arrasto = useRef({ x0: 0, max: 1 });
  const [x, setX] = useState(0);
  const [arrastando, setArrastando] = useState(false);
  const [feito, setFeito] = useState(false);

  const medir = () =>
    trilho.current && botao.current ? Math.max(1, trilho.current.clientWidth - botao.current.offsetWidth - 8) : 1;

  useEffect(() => {
    if (!emEspera && feito) {
      setFeito(false);
      setX(0);
    }
  }, [emEspera, feito]);

  useEffect(() => {
    if (bloqueado) setX(0);
  }, [bloqueado]);

  function concluir() {
    if (bloqueado || feito) return;
    setX(medir());
    setFeito(true);
    onConfirmar();
  }

  function descer(e: PointerEvent<HTMLButtonElement>) {
    if (bloqueado || feito) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    arrasto.current = { x0: e.clientX, max: medir() };
    setArrastando(true);
  }
  function mover(e: PointerEvent<HTMLButtonElement>) {
    if (!arrastando) return;
    setX(Math.min(arrasto.current.max, Math.max(0, e.clientX - arrasto.current.x0)));
  }
  function soltar() {
    if (!arrastando) return;
    setArrastando(false);
    if (x >= arrasto.current.max * 0.9) concluir();
    else setX(0);
  }

  const p = feito ? 1 : Math.min(1, x / arrasto.current.max || 0);
  return (
    <div
      ref={trilho}
      className={`deslizar ${bloqueado ? "travado" : ""} ${feito ? "feito" : ""}`}
      style={{ "--p": p } as CSSProperties}
    >
      <button
        ref={botao}
        type="button"
        className="deslizar-botao"
        style={{ transform: `translateX(${x}px)`, transition: arrastando ? "none" : undefined }}
        disabled={bloqueado}
        aria-label={bloqueado ? rotuloBloqueado : "Enviar os pedidos: deslize para a direita ou aperte Enter"}
        onPointerDown={descer}
        onPointerMove={mover}
        onPointerUp={soltar}
        onPointerCancel={soltar}
        onClick={(e) => {
          if (e.detail === 0) concluir(); // clique vindo do teclado (Enter/Espaço)
        }}
      >
        <Icone nome="seta" tamanho={26} />
      </button>
      <span className="deslizar-texto" aria-hidden="true">
        {bloqueado ? rotuloBloqueado : rotulo}
      </span>
    </div>
  );
}
