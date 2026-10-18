import { useEffect, useState } from "react";
import { chaveOrg, chaveUltimaSala, gravarLocal, lerLocal, chaveEu, ultimaSalaOrg, api, type Eu } from "../api";
import BarraInferior from "../componentes/BarraInferior";
import Icone from "../componentes/Icone";
import StatusIfood, { RecarregarDemo } from "../componentes/StatusIfood";
import { MSG_FORA_PROTOTIPO, useToast } from "../componentes/Toast";

// Itens decorativos da home: aparecem apagados e não são botões.
const CATS = [
  ["🍽️", "Restaurantes"],
  ["🛒", "Mercado"],
  ["💊", "Farmácia"],
  ["🥤", "Bebidas"],
  ["🐶", "Pet"],
  ["🎁", "Shopping"],
];
const LOJAS = [
  ["🍔", "Hamburgueria Demo", "Lanches", "#ffe3d6"],
  ["🍕", "Pizzaria Demo", "Pizza", "#ffeec2"],
  ["🥗", "Saladas Demo", "Saudável", "#dff3e4"],
];

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
    <div className="app-sala">
      <header className="topo-sala">
        <button type="button" className="voltar" aria-label="Voltar para o início" onClick={onCancelar}>
          ‹
        </button>
        <strong>Novo match</strong>
        <span />
      </header>
      <form className="tela" onSubmit={criar}>
        <h1 className="titulo">Quem vai comer?</h1>
        <p className="sub">
          Pode ser só você ou a turma toda. Só você usa o iFood: a turma entra por link ou QR, sem login.
        </p>
        <StatusIfood />
        <ol className="passos" aria-label="Como funciona">
          <li>
            <span className="passo-n">1</span>Crie a sala
          </li>
          <li>
            <span className="passo-n">2</span>Chame a turma
          </li>
          <li>
            <span className="passo-n">3</span>A IA monta o pedido
          </li>
        </ol>
        <label className="campo">
          <span>Seu nome (organizador)</span>
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            required
            maxLength={30}
            autoComplete="given-name"
            placeholder="Como te chamam?"
          />
        </label>
        <label className="campo">
          <span>
            Chave Pix <em>(opcional, para a vaquinha)</em>
          </span>
          <input
            value={pix}
            onChange={(e) => setPix(e.target.value)}
            autoComplete="off"
            placeholder="CPF, e-mail, telefone ou chave aleatória"
          />
          <small>Usada só para gerar o QR da vaquinha; fica só neste computador.</small>
        </label>
        {erro && (
          <div className="alerta alerta-erro" role="alert">
            {erro}
          </div>
        )}
        <div className="rodape-acao">
          <button className="primario" disabled={criando || !nome.trim()}>
            {criando ? "Criando…" : "Criar sala"}
          </button>
        </div>
      </form>
      <p className="rodape">Protótipo de hackathon · não afiliado ao iFood</p>
    </div>
  );
}

export default function Inicio() {
  const [criando, setCriando] = useState(false);
  // null = ainda não sei (a resposta de /api/saude não chegou ou falhou); só afirmo "Demonstração" quando o servidor diz.
  const [demo, setDemo] = useState<boolean | null>(null);
  useEffect(() => {
    let vivo = true;
    api
      .saude()
      .then((s) => {
        if (vivo && typeof s.demonstracao === "boolean") setDemo(s.demonstracao);
      })
      .catch(() => {
        /* sem resposta: o endereço fica genérico */
      });
    return () => {
      vivo = false;
    };
  }, []);
  const salaSalva = ultimaSalaOrg();
  const [toast, avisar] = useToast();
  const fora = () => avisar(MSG_FORA_PROTOTIPO);
  const inicial = (lerLocal<Eu>(chaveEu)?.nome ?? "").trim().charAt(0).toUpperCase();

  if (criando) return <CriarMatch onCancelar={() => setCriando(false)} />;

  return (
    <div className="home">
      <div className="home-corpo">
        <header className="addr">
          <div className="addr-info" aria-disabled="true">
            <span className="addr-pino">
              <Icone nome="pino" tamanho={24} />
            </span>
            <span>
              <small>Entregar em</small>
              <b>
                {demo === true ? "Demonstração — São Carlos" : demo === false ? "Endereço da sua conta iFood" : "Endereço de entrega"}{" "}
                <Icone nome="baixo" tamanho={16} />
              </b>
            </span>
          </div>
          <div className="eu" aria-hidden="true">
            {inicial || <Icone nome="pessoa" tamanho={20} />}
          </div>
        </header>

        <button type="button" className="busca desab" aria-disabled="true" onClick={fora}>
          <Icone nome="busca" tamanho={20} />
          Busque por item ou loja
        </button>

        <div className="cats" aria-label="Categorias">
          <button type="button" className="cat cat-match" onClick={() => setCriando(true)}>
            <i>
              <Icone nome="coracao" tamanho={26} />
              <em>novo</em>
            </i>
            Match
          </button>
          {CATS.map(([e, r]) => (
            <button key={r} type="button" className="cat desab" aria-disabled="true" onClick={fora}>
              <i aria-hidden="true">{e}</i>
              {r}
            </button>
          ))}
        </div>

        <button type="button" className="hero" onClick={() => setCriando(true)} aria-label="Fazer um match">
          <span className="hero-marca">
            <Icone nome="coracao" tamanho={30} />
            match
          </span>
          <span className="hero-texto">Cada um quer uma coisa? A gente acha o pedido que agrada todo mundo.</span>
          <span className="hero-cta">
            Fazer um match <Icone nome="seta" tamanho={18} />
          </span>
          <span className="hero-fl f1" aria-hidden="true">🍕</span>
          <span className="hero-fl f2" aria-hidden="true">🍔</span>
          <span className="hero-fl f3" aria-hidden="true">🍣</span>
        </button>

        {salaSalva && (
          <a className="sala-salva" href={`#/s/${encodeURIComponent(salaSalva)}/org`}>
            <span>
              <strong>Sua sala está aberta</strong>
              <small>Voltar para o Match em andamento</small>
            </span>
            <Icone nome="direita" tamanho={20} />
          </a>
        )}

        <h2 className="sec">Perto de você</h2>
        <div className="lojas">
          {LOJAS.map(([e, nome, cat, cor]) => (
            <button key={nome} type="button" className="rcard desab" aria-disabled="true" onClick={fora}>
              <span className="rtile" style={{ background: cor }} aria-hidden="true">
                {e}
              </span>
              <span className="rinfo">
                <strong>{nome}</strong>
                <small>{cat} · ilustrativa</small>
              </span>
              <span className="mini-selo">DEMONSTRAÇÃO</span>
            </button>
          ))}
        </div>
        <RecarregarDemo />
        <p className="rodape">Protótipo de hackathon · não afiliado ao iFood</p>
      </div>
      <BarraInferior atual="inicio" onIr={(a) => a === "match" && setCriando(true)} onInerte={fora} />
      {toast}
    </div>
  );
}
