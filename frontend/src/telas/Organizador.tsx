import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, chaveBase, gravarLocal, lerLocal, lerToken } from "../api";
import type { EstadoSala } from "../tipos";
import Avatar from "../componentes/Avatar";
import EsqueletoCartoes from "../componentes/Esqueleto";
import Icone from "../componentes/Icone";
import Rastro from "../componentes/Rastro";
import { FormDesejo, contagemRespostas, lerPid } from "./Convidado";
import StatusIfood from "../componentes/StatusIfood";

const ENDERECO_LOCAL = /^https?:\/\/(localhost|127\.|\[::1\])/;

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
  const [abrirDesejo, setAbrirDesejo] = useState(false);

  const link = `${base.replace(/\/+$/, "")}/#/s/${salaId}`;
  const ehLocal = ENDERECO_LOCAL.test(base);

  // Sem base escolhida pelo usuário e página aberta em localhost: usa o IP do PC na rede (vem do backend).
  useEffect(() => {
    if (lerLocal<string>(chaveBase) != null || !ENDERECO_LOCAL.test(window.location.origin)) return;
    let vivo = true;
    api
      .saude()
      .then((s) => {
        if (vivo && s.ip_local) setBase(s.ip_local);
      })
      .catch(() => {
        /* sem IP: o campo "Base do link" continua disponível */
      });
    return () => {
      vivo = false;
    };
  }, []);

  useEffect(() => {
    QRCode.toDataURL(link, { margin: 1, width: 280 })
      .then(setQr)
      .catch(() => setQr(""));
  }, [link]);

  const pid = lerPid(salaId);
  const eu = sala?.participantes.find((p) => p.id === pid);
  const { resp: respondeu, total } = sala ? contagemRespostas(sala, pid) : { resp: 0, total: 0 };

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
      <section className="tela tela-centro">
        <div className="radar" aria-hidden="true">
          <i />
          <i />
          <i />
          <span className="radar-nucleo">
            <Icone nome="coracao" tamanho={44} />
          </span>
          <span className="orbita">
            <span>🍕</span>
          </span>
        </div>
        <div role="status" aria-live="polite">
          <h1 className="titulo">Procurando…</h1>
          <p className="sub">A IA está lendo os desejos e consultando as lojas.</p>
        </div>
        <Rastro itens={sala?.rastro ?? []} aberto />
      </section>
    );
  }

  return (
    <section className="tela">
      <StatusIfood />

      <div className="qrcard">
        {qr ? (
          <img className="qr" src={qr} alt="QR code do convite da sala" width={132} height={132} />
        ) : (
          <div className="qr esqueleto" role="img" aria-label="Gerando o QR code" />
        )}
        <div className="qrinfo">
          <b>Chame a turma</b>
          <small>Escaneie ou mande o link. Responder leva menos de 30 segundos, sem login.</small>
          <button type="button" className="link-chip" onClick={copiar} aria-label="Copiar o link da sala">
            <span>{link.replace(/^https?:\/\//, "")}</span>
            <span className="link-chip-ic">{copiado ? <Icone nome="check" tamanho={14} /> : <Icone nome="copiar" tamanho={14} />}</span>
          </button>
          <span className="copiado" role="status">{copiado ? "Link copiado" : ""}</span>
        </div>
      </div>
      <p className="dica">Os celulares precisam estar no mesmo Wi-Fi do computador.</p>
      <details className="avancado" open={ehLocal}>
        <summary>O link não abre no celular?</summary>
        <label className="campo">
          <span>Base do link</span>
          <input
            value={base}
            onChange={(e) => {
              setBase(e.target.value);
              gravarLocal(chaveBase, e.target.value);
            }}
            placeholder="http://192.168.0.10:8000"
            inputMode="url"
            autoComplete="off"
          />
          <small>
            {ehLocal
              ? "Está apontando para este computador. Use o IP do Wi-Fi do PC (ex.: 192.168.x.x); evite 172.x (adaptador virtual)."
              : "Use o IP do Wi-Fi do PC (ex.: 192.168.x.x). Evite 172.x (adaptador virtual)."}
          </small>
        </label>
      </details>

      <h2 className="sec2">
        Quem entrou
        <span>
          {respondeu} de {total} {total === 1 ? "convidado respondeu" : "convidados responderam"}
        </span>
      </h2>
      {!sala ? (
        <EsqueletoCartoes n={2} rotulo="Carregando a sala…" />
      ) : (
        <ul className="roster">
          {sala.participantes.map((p) => (
            <li key={p.id} className={`rrow ${p.respondeu ? "resp" : ""}`}>
              <Avatar nome={p.nome} tam="sm" />
              <span className="rtxt">
                <b>
                  {p.nome}
                  {p.id === pid && <span className="voce">você</span>}
                </b>
              </span>
              <span className={`status-pag ${p.respondeu ? "pago" : "pend"}`}>
                {p.respondeu ? "✓ respondeu" : "aguardando"}
              </span>
            </li>
          ))}
        </ul>
      )}
      {sala && total === 0 && (
        <div className="vazio">
          <strong>Ninguém entrou ainda</strong>
          <p>Mostre o QR ou mande o link no grupo. Quem responder aparece aqui na hora.</p>
        </div>
      )}

      <button
        type="button"
        className="rrow add"
        aria-expanded={abrirDesejo}
        onClick={() => setAbrirDesejo((a) => !a)}
      >
        <Icone nome={abrirDesejo ? "x" : "mais"} tamanho={18} />
        {abrirDesejo ? "Fechar" : eu?.respondeu ? "Mudar meu desejo" : "Também quero pedir"}
      </button>
      {abrirDesejo && (
        <div>
          <h2 className="sec2">Seu desejo</h2>
          <FormDesejo
            salaId={salaId}
            nomeInicial={nomeOrg}
            rotuloBotao="Salvar meu desejo"
            onFeito={() => setAbrirDesejo(false)}
          />
        </div>
      )}

      <div className="rodape-acao">
        {erro && (
          <div className="alerta alerta-erro" role="alert">
            {erro}
          </div>
        )}
        <button className="primario" disabled={respondeu < 1} onClick={rodar}>
          {erro ? "Tentar de novo" : "Rodar Match"}
        </button>
        {respondeu < 1 && <p className="dica">Precisa de pelo menos 1 resposta para rodar.</p>}
      </div>
    </section>
  );
}
