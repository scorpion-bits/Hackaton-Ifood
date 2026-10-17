import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, chaveBase, gravarLocal, lerLocal, lerToken } from "../api";
import type { EstadoSala } from "../tipos";
import Rastro from "../componentes/Rastro";
import { FormDesejo, lerPid } from "./Convidado";

function baseInicial(): string {
  return lerLocal<string>(chaveBase) ?? window.location.origin;
}

export default function Organizador({
  salaId,
  sala,
  nomeOrg,
}: {
  salaId: string;
  sala: EstadoSala | null;
  nomeOrg: string;
}) {
  const [base, setBase] = useState(baseInicial);
  const [qr, setQr] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [rodando, setRodando] = useState(false);
  const [erro, setErro] = useState("");
  const [editandoDesejo, setEditandoDesejo] = useState(false);

  const link = `${base.replace(/\/+$/, "")}/#/s/${salaId}`;
  const ehLocal = /^https?:\/\/(localhost|127\.|\[::1\])/.test(base);

  useEffect(() => {
    QRCode.toDataURL(link, { margin: 1, width: 240 })
      .then(setQr)
      .catch(() => setQr(""));
  }, [link]);

  const pid = lerPid(salaId);
  const eu = sala?.participantes.find((p) => p.id === pid);
  const respondeu = sala?.participantes.filter((p) => p.respondeu).length ?? 0;
  const total = sala?.participantes.length ?? 0;

  async function copiar() {
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1800);
    } catch {
      window.prompt("Copie o link:", link);
    }
  }

  async function rodar() {
    const token = lerToken(salaId);
    if (!token) {
      setErro("Sem permissão de organizador neste aparelho.");
      return;
    }
    setRodando(true);
    setErro("");
    try {
      await api.rodar(salaId, token);
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Falhou ao rodar o Match.");
    } finally {
      setRodando(false);
    }
  }

  if (rodando) {
    return (
      <section className="tela">
        <div className="cartao centro">
          <div className="girando" aria-hidden>✨</div>
          <h1>Procurando…</h1>
          <p className="suave">A IA está lendo os desejos e consultando as lojas.</p>
        </div>
        <Rastro itens={sala?.rastro ?? []} aberto />
      </section>
    );
  }

  return (
    <section className="tela">
      <h1>Sua sala de Match</h1>

      <div className="cartao centro">
        <p className="suave">Peça para o pessoal escanear ou abrir o link:</p>
        {qr ? <img className="qr" src={qr} alt="QR code do convite" width={200} height={200} /> : <div className="qr" />}
        <p className="link">{link}</p>
        <button className="secundario" onClick={copiar}>
          {copiado ? "Copiado ✓" : "Copiar link"}
        </button>
        {ehLocal && (
          <div className="aviso">
            <p>Para celulares, abra pelo IP do PC na mesma rede.</p>
            <label>
              Base do link
              <input
                value={base}
                onChange={(e) => {
                  setBase(e.target.value);
                  gravarLocal(chaveBase, e.target.value);
                }}
                placeholder="http://192.168.0.10:8000"
              />
            </label>
          </div>
        )}
      </div>

      <div className="cartao">
        <h2>
          {respondeu} de {total} responderam
        </h2>
        <ul className="lista-part">
          {sala?.participantes.map((p) => (
            <li key={p.id}>
              <span>{p.nome}</span>
              <span className={p.respondeu ? "ok" : "suave"}>{p.respondeu ? "✓ respondeu" : "⏳ aguardando"}</span>
            </li>
          ))}
          {total === 0 && <li className="suave">Ninguém entrou ainda.</li>}
        </ul>
      </div>

      {(!eu?.respondeu || editandoDesejo) && (
        <div>
          <h2>Seu desejo</h2>
          <FormDesejo
            salaId={salaId}
            nomeInicial={nomeOrg}
            rotuloBotao="Salvar meu desejo"
            onFeito={() => setEditandoDesejo(false)}
          />
        </div>
      )}
      {eu?.respondeu && !editandoDesejo && (
        <button className="secundario" onClick={() => setEditandoDesejo(true)}>
          Mudar meu desejo
        </button>
      )}

      {erro && <p className="erro">{erro}</p>}
      <button className="primario" disabled={respondeu < 1} onClick={rodar}>
        Rodar Match ✨
      </button>
      {respondeu < 1 && <p className="suave centro-txt">Precisa de pelo menos 1 resposta.</p>}
    </section>
  );
}
