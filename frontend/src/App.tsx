import { useEffect, useRef, useState } from "react";
import { api, type Acao, type Lado, type PassoAgente, type Saude } from "./api";

interface Mensagem {
  autor: "usuario" | "agente" | "erro";
  texto: string;
  passos?: PassoAgente[];
  acoes?: Acao[];
}

const SUGESTOES: Record<Lado, string[]> = {
  comprador: ["Quais lojas tem?", "Quero pedir um burger até R$ 40", "Tem sushi?"],
  vendedor: ["Mostre o cardápio", "Crie uma promoção de 15%", "Pausar a lasanha, acabou"],
};

const TITULO_LADO: Record<Lado, string> = { comprador: "Sou cliente", vendedor: "Sou lojista" };

// Renderiza **negrito** e quebras de linha sem injetar HTML.
function TextoRico({ texto }: { texto: string }) {
  return (
    <>
      {texto.split(/(\*\*[^*]+\*\*)/g).map((parte, i) =>
        parte.startsWith("**") && parte.endsWith("**") ? <strong key={i}>{parte.slice(2, -2)}</strong> : parte,
      )}
    </>
  );
}

function CartaoAcao({ acao, aoMudar }: { acao: Acao; aoMudar: (a: Acao) => void }) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  async function decidir(fn: (id: string) => Promise<Acao>) {
    setOcupado(true);
    setErro("");
    try {
      aoMudar(await fn(acao.id));
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className={`acao acao-${acao.status}`}>
      <div className="acao-rotulo">Ação proposta pelo agente</div>
      <div className="acao-resumo">{acao.resumo}</div>
      <div className="acao-motivo">Por quê: {acao.motivo}</div>
      {acao.status === "pendente" ? (
        <div className="acao-botoes">
          <button className="btn-primario" disabled={ocupado} onClick={() => decidir(api.confirmar)}>
            Confirmar
          </button>
          <button className="btn-secundario" disabled={ocupado} onClick={() => decidir(api.recusar)}>
            Recusar
          </button>
        </div>
      ) : (
        <div className="acao-status">
          {acao.status === "executada" && "✓ Executada"}
          {acao.status === "recusada" && "Recusada por você"}
          {acao.status === "erro" && `Não executada: ${String(acao.resultado?.erro ?? "")}`}
        </div>
      )}
      {erro && <div className="acao-status">{erro}</div>}
    </div>
  );
}

function Passos({ passos }: { passos: PassoAgente[] }) {
  if (!passos.length) return null;
  return (
    <details className="passos">
      <summary>Como o agente chegou nisso ({passos.length} ferramenta{passos.length > 1 ? "s" : ""} MCP)</summary>
      <ol>
        {passos.map((p, i) => (
          <li key={i}>
            <code>{p.ferramenta}</code> {p.ok ? "" : "— falhou"}
            <div className="passo-args">{JSON.stringify(p.argumentos)}</div>
          </li>
        ))}
      </ol>
    </details>
  );
}

export default function App() {
  const [lado, setLado] = useState<Lado>("comprador");
  const [mensagens, setMensagens] = useState<Record<Lado, Mensagem[]>>({ comprador: [], vendedor: [] });
  const [conversas, setConversas] = useState<Partial<Record<Lado, string>>>({});
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [saude, setSaude] = useState<Saude | null>(null);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.saude().then(setSaude).catch(() => setSaude(null));
  }, []);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, carregando, lado]);

  function adicionar(l: Lado, m: Mensagem) {
    setMensagens((atual) => ({ ...atual, [l]: [...atual[l], m] }));
  }

  function atualizarAcao(nova: Acao) {
    setMensagens((atual) => ({
      ...atual,
      [lado]: atual[lado].map((m) => ({ ...m, acoes: m.acoes?.map((a) => (a.id === nova.id ? nova : a)) })),
    }));
  }

  async function enviar(conteudo: string) {
    const msg = conteudo.trim();
    if (!msg || carregando) return;
    const l = lado;
    setTexto("");
    adicionar(l, { autor: "usuario", texto: msg });
    setCarregando(true);
    try {
      const r = await api.chat(msg, l, conversas[l]);
      setConversas((c) => ({ ...c, [l]: r.conversa_id }));
      adicionar(l, { autor: "agente", texto: r.texto, passos: r.passos, acoes: r.acoes });
    } catch (e) {
      adicionar(l, { autor: "erro", texto: (e as Error).message });
    } finally {
      setCarregando(false);
    }
  }

  async function recarregarDemo() {
    if (!window.confirm("Recarregar os dados de demonstração? Conversas e ações serão apagadas.")) return;
    await api.resetarDemo();
    setMensagens({ comprador: [], vendedor: [] });
    setConversas({});
  }

  const atuais = mensagens[lado];

  return (
    <div className="app">
      <header className="topo">
        <div className="topo-linha">
          <div>
            <h1>Agente de Comércio</h1>
            <p className="sub">Hackathon iFood × SEMCOMP 29</p>
          </div>
          {saude?.demonstracao && <span className="selo">DEMONSTRAÇÃO</span>}
        </div>
        <nav className="abas" role="tablist">
          {(["comprador", "vendedor"] as Lado[]).map((l) => (
            <button key={l} role="tab" aria-selected={lado === l} className={lado === l ? "aba ativa" : "aba"}
              onClick={() => setLado(l)}>
              {TITULO_LADO[l]}
            </button>
          ))}
        </nav>
      </header>

      <main className="chat">
        {atuais.length === 0 && (
          <div className="vazio">
            <p>{lado === "comprador" ? "Diga o que quer comer e quanto quer gastar." : "Peça ajuda com cardápio, estoque e promoções."}</p>
            <p className="vazio-nota">Nada com dinheiro acontece sem você confirmar.</p>
          </div>
        )}
        {atuais.map((m, i) => (
          <div key={i} className={`bolha bolha-${m.autor}`}>
            <div className="bolha-texto"><TextoRico texto={m.texto} /></div>
            {m.acoes?.map((a) => <CartaoAcao key={a.id} acao={a} aoMudar={atualizarAcao} />)}
            {m.passos && <Passos passos={m.passos} />}
          </div>
        ))}
        {carregando && <div className="bolha bolha-agente digitando">Pensando…</div>}
        <div ref={fim} />
      </main>

      <footer className="rodape">
        <div className="sugestoes">
          {SUGESTOES[lado].map((s) => (
            <button key={s} className="chip" onClick={() => enviar(s)} disabled={carregando}>{s}</button>
          ))}
        </div>
        <form className="entrada" onSubmit={(e) => { e.preventDefault(); enviar(texto); }}>
          <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escreva para o agente…"
            aria-label="Mensagem" />
          <button className="btn-primario" type="submit" disabled={carregando || !texto.trim()}>Enviar</button>
        </form>
        <div className="info">
          <span>IA: {saude ? `${saude.llm_provedor}${saude.llm_modelo ? ` · ${saude.llm_modelo}` : ""}` : "backend offline"}</span>
          <button className="link" onClick={recarregarDemo}>Recarregar demo</button>
        </div>
      </footer>
    </div>
  );
}
