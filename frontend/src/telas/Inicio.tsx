import { useState } from "react";
import { chaveOrg, chaveUltimaSala, gravarLocal, lerLocal, chaveEu, ultimaSalaOrg, api, type Eu } from "../api";
import BarraInferior from "../componentes/BarraInferior";
import StatusIfood, { RecarregarDemo } from "../componentes/StatusIfood";

const ABAS = ["Início", "Restaurantes", "Mercados", "Bebidas"];
const CATS = [
  ["🍔", "Lanches"],
  ["🍕", "Pizza"],
  ["🍱", "Japonesa"],
  ["🛒", "Mercado"],
  ["🥤", "Bebidas"],
  ["💊", "Farmácia"],
  ["🐶", "Pet"],
];
const LOJAS = [
  ["🍔", "Hamburgueria Demo", "Lanches"],
  ["🍕", "Pizzaria Demo", "Pizza"],
  ["🥗", "Saladas Demo", "Saudável"],
];

function Desab({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`desab ${className}`} aria-disabled="true">
      {children}
    </span>
  );
}

function CriarMatch({ onCancelar }: { onCancelar: () => void }) {
  const [nome, setNome] = useState(lerLocal<Eu>(chaveEu)?.nome ?? "");
  const [pix, setPix] = useState("");
  const [erro, setErro] = useState("");
  const [criando, setCriando] = useState(false);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setCriando(true);
    setErro("");
    try {
      const s = await api.criarSala(nome.trim(), pix.trim());
      gravarLocal(chaveOrg(s.sala_id), s.token_organizador);
      gravarLocal(chaveUltimaSala, s.sala_id);
      gravarLocal(`match.nome.${s.sala_id}`, nome.trim());
      // o organizador também é participante: guarda o id para não entrar duas vezes
      if (s.participante_id) gravarLocal(`match.pid.${s.sala_id}`, s.participante_id);
      window.location.hash = `#/s/${s.sala_id}/org`;
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui criar a sala.");
      setCriando(false);
    }
  }

  return (
    <section className="tela">
      <h1>Criar Match</h1>
      <StatusIfood />
      <form className="cartao form" onSubmit={criar}>
        <label>
          Seu nome (organizador)
          <input value={nome} onChange={(e) => setNome(e.target.value)} required placeholder="Como te chamam?" />
        </label>
        <label>
          Chave Pix (opcional)
          <input value={pix} onChange={(e) => setPix(e.target.value)} placeholder="CPF, e-mail, telefone ou chave aleatória" />
          <small>Usada só para gerar o QR da vaquinha; fica só neste computador.</small>
        </label>
        {erro && <p className="erro">{erro}</p>}
        <button className="primario" disabled={criando || !nome.trim()}>
          {criando ? "Criando…" : "Criar sala"}
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Voltar
        </button>
      </form>
    </section>
  );
}

export default function Inicio() {
  const [criando, setCriando] = useState(false);
  const salaSalva = ultimaSalaOrg();

  if (criando) return <CriarMatch onCancelar={() => setCriando(false)} />;

  return (
    <div className="home">
      <header className="home-topo">
        <div>
          <small>Entregar em</small>
          <br />
          <strong>Demonstração — São Carlos ▾</strong>
        </div>
      </header>
      <div className="busca" aria-disabled="true">
        🔍 Busque por item ou loja
      </div>
      <div className="abas-home">
        {ABAS.map((a, i) => (
          <Desab key={a} className={i === 0 ? "ativa" : ""}>
            {a}
          </Desab>
        ))}
      </div>
      <div className="chips-home">
        {["Ordenar ▾", "Pra retirar", "Entrega grátis"].map((c) => (
          <Desab key={c} className="chip-h">
            {c}
          </Desab>
        ))}
      </div>
      <div className="cats">
        {CATS.map(([e, r]) => (
          <Desab key={r} className="cat">
            <span className="cat-ico">{e}</span>
            <span>{r}</span>
          </Desab>
        ))}
      </div>

      <button className="banner-match" onClick={() => setCriando(true)}>
        <span className="banner-txt">
          <strong>Pedir em grupo? Dê um Match ✨</strong>
          <span>Cada um diz o que quer, a IA monta o pedido.</span>
        </span>
        <span className="banner-cta">Criar Match →</span>
      </button>

      {salaSalva && (
        <a className="voltar-sala" href={`#/s/${encodeURIComponent(salaSalva)}/org`}>
          Voltar para a sua sala ›
        </a>
      )}

      <h2 className="sec">Lojas perto de você</h2>
      <div className="lojas">
        {LOJAS.map(([e, nome, cat]) => (
          <div key={nome} className="loja" aria-disabled="true">
            <span className="loja-ico">{e}</span>
            <span className="loja-info">
              <strong>{nome}</strong>
              <small>{cat} · demo</small>
            </span>
            <span className="mini-selo">DEMONSTRAÇÃO</span>
          </div>
        ))}
      </div>
      <RecarregarDemo />
      <p className="rodape">Protótipo de hackathon · não é o app oficial do iFood</p>
      <BarraInferior atual="inicio" onIr={(a) => a === "match" && setCriando(true)} />
    </div>
  );
}
