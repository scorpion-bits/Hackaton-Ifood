import { useEffect, useRef } from "react";
import { reduzirMovimento } from "./util";

const CORES = ["#ffffff", "#FFC83D", "#FFE1E3", "#FF7AA8", "#7CF0C0", "#B3101D"];

/** Confete em canvas; não roda com prefers-reduced-motion. */
export default function Confete() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    if (!cv || reduzirMovimento()) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    const larg = cv.clientWidth;
    const alt = cv.clientHeight;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = larg * dpr;
    cv.height = alt * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const ps = Array.from({ length: 140 }, () => ({
      x: larg / 2,
      y: alt * 0.42,
      vx: (Math.random() - 0.5) * 16,
      vy: -Math.random() * 15 - 4,
      g: 0.32 + Math.random() * 0.15,
      s: 5 + Math.random() * 7,
      c: CORES[Math.floor(Math.random() * CORES.length)],
      a: Math.random() * 6.28,
      va: (Math.random() - 0.5) * 0.4,
    }));
    let raf = 0;
    let t0 = 0;
    const atraso = window.setTimeout(() => {
      t0 = performance.now();
      const loop = (t: number) => {
        const dt = t - t0;
        ctx.clearRect(0, 0, larg, alt);
        for (const p of ps) {
          p.vy += p.g;
          p.vx *= 0.992;
          p.x += p.vx;
          p.y += p.vy;
          p.a += p.va;
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate(p.a);
          ctx.fillStyle = p.c;
          ctx.globalAlpha = Math.max(0, 1 - dt / 3200);
          ctx.fillRect(-p.s / 2, -p.s / 3, p.s, p.s * 0.6);
          ctx.restore();
        }
        if (dt < 3200) raf = requestAnimationFrame(loop);
        else ctx.clearRect(0, 0, larg, alt);
      };
      raf = requestAnimationFrame(loop);
    }, 600);
    return () => {
      clearTimeout(atraso);
      cancelAnimationFrame(raf);
    };
  }, []);
  return <canvas ref={ref} className="ld-confete" aria-hidden="true" />;
}
