import { useEffect, useRef, useState } from "react";
import { api, chaveEu, chaveOrg, chaveUltimaSala, gravarLocal, lerLocal, type Eu } from "../api";
import { Esqueleto } from "../componentes/Esqueleto";
import Icone from "../componentes/Icone";
import Selo from "../componentes/Selo";
import StatusIfood from "../componentes/StatusIfood";
import { PREFERENCIAS, RESTRICOES, chavePid } from "./Convidado";

/** Marca a sala como "de uma pessoa só": o organizador esconde o convite (QR/link). */
export const chaveSolo = (salaId: string) => `match.solo.${salaId}`;
export const salaSolo = (salaId: string) => lerLocal<boolean>(chaveSolo(salaId)) === true;

const EXEMPLOS = ["japonês até 40", "um lanche rápido e um sorvete", "pizza sem lactose", "algo leve e barato"];
const maiuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

interface SalaSolo {
  id: string;
  token: string;
  pid: string;
}

/**
 * "Só eu": tela única para pedir sozinho. Cria a sala, grava o desejo do organizador, roda o Match e
 * abre a sala (que já chega em `match_pronto`: disputa e deck). Sem vaquinha, sem QR, sem chave Pix.
 */
export default function SoEu({ onCancelar }: { onCancelar: () => void }) {
  const eu = lerLocal<Eu>(chaveEu);
  const [nome, setNome] = useState(eu?.nome ?? "");
  const [texto, setTexto] = useState("");
  const [orcamento, setOrcamento] = useState("");
  const [chips, setChips] = useState<string[]>(eu?.chips ?? []);
  const [fase, setFase] = useState<"form" | "buscando" | "erro">("form");
  const [erro, setErro] = useState("");
  const [demo, setDemo] = useState<boolean | null>(null);
  // se o Match falhar (ex.: nada combina), a sala criada é reaproveitada ao tentar de novo
  const sala = useRef<SalaSolo | null>(null);
  const campoTexto = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    let vivo = true;
    api
      .saude()
      .then((s) => vivo && typeof s.demonstracao === "boolean" && setDemo(s.demonstracao))
      .catch(() => {
        /* sem resposta: sem selo */
      });
    return () => {
      vivo = false;
    };
  }, []);

  const alternar = (c: string) => setChips((l) => (l.includes(c) ? l.filter((x) => x !== c) : [...l, c]));
  const pronto = nome.trim().length > 0 && texto.trim().length > 0;

  async function encontrar(e: React.FormEvent) {
    e.preventDefault();
    if (!pronto || fase === "buscando") return;
    setFase("buscando");
    setErro("");
    try {
      if (!sala.current) {
        const s = await api.criarSala(nome.trim());
        const pid = s.participante_id;
        if (!pid) throw new Error("A sala foi criada sem o seu cadastro. Tente de novo.");
        sala.current = { id: s.sala_id, token: s.token_organizador, pid };
        gravarLocal(chaveOrg(s.sala_id), s.token_organizador);
        gravarLocal(chaveUltimaSala, s.sala_id);
        gravarLocal(`match.nome.${s.sala_id}`, nome.trim());
        gravarLocal(chavePid(s.sala_id), pid);
        gravarLocal(chaveSolo(s.sala_id), true);
      }
      const { id, token, pid } = sala.current;
      const valor = parseFloat(orcamento.replace(",", "."));
      await api.desejo(id, pid, {
        texto: texto.trim(),
        orcamento_max: Number.isFinite(valor) && valor > 0 ? valor : null,
        chips,
      });
      gravarLocal(chaveEu, { nome: nome.trim(), chips });
      await api.rodar(id, token);
      window.location.hash = `#/s/${encodeURIComponent(id)}/org`;
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui montar o seu pedido.");
      setFase("erro");
    }
  }

  function mudarPedido() {
    setFase("form");
    setTimeout(() => campoTexto.current?.focus(), 0);
  }

  const grupo = (titulo: string, lista: string[]) => (
    <div className="chgrupo">
      <span className="chrotulo" id={`soeu-ch-${titulo}`}>
        {titulo}
      </span>
      <div className="grupo-chips" role="group" aria-labelledby={`soeu-ch-${titulo}`}>
        {lista.map((c) => (
          <button
            key={c}
            type="button"
            className={`chip ${chips.includes(c) ? "on" : ""}`}
            aria-pressed={chips.includes(c)}
            onClick={() => alternar(c)}
          >
            {maiuscula(c)}
          </button>
        ))}
      </div>
    </div>
  );

  if (fase === "buscando") {
    return (
      <div className="app-sala">
        <header className="topo-sala">
          <span />
          <strong>Só eu</strong>
          <span />
        </header>
        <Selo ativo={demo === true} />
        <section className="tela tela-centro soeu-busca">
          <div className="radar" aria-hidden="true">
            <i />
            <i />
            <i />
            <span className="radar-nucleo">
              <Icone nome="coracao" tamanho={44} />
            </span>
            <span className="orbita">
              <span>🍣</span>
            </span>
          </div>
          <div role="status" aria-live="polite">
            <h1 className="titulo">Procurando nas lojas perto de você…</h1>
            <p className="sub">A IA lê o seu pedido, consulta os cardápios e monta as melhores opções.</p>
          </div>
          <div className="soeu-esq" aria-hidden="true">
            <div className="soeu-esq-linha">
              <Esqueleto altura={44} largura="44px" />
              <div>
                <Esqueleto altura={14} largura="60%" />
                <Esqueleto altura={12} largura="85%" />
              </div>
            </div>
            <div className="soeu-esq-linha">
              <Esqueleto altura={44} largura="44px" />
              <div>
                <Esqueleto altura={14} largura="50%" />
                <Esqueleto altura={12} largura="70%" />
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="app-sala">
      <header className="topo-sala">
        <button type="button" className="voltar" aria-label="Voltar para o início" onClick={onCancelar}>
          ‹
        </button>
        <strong>Só eu</strong>
        <span />
      </header>
      <Selo ativo={demo === true} />
      <form className="tela" onSubmit={encontrar}>
        <h1 className="titulo">O que você quer?</h1>
        <p className="sub">Escreva do seu jeito. A IA entende preço, pressa, restrição e vontade e acha o melhor pedido.</p>
        <StatusIfood />

        {fase === "erro" && (
          <div className="alerta alerta-erro soeu-erro" role="alert">
            <span>{erro}</span>
            <button type="button" className="soeu-erro-btn" onClick={mudarPedido}>
              Mudar meu pedido
            </button>
          </div>
        )}

        <label className="campo">
          <span>Seu nome</span>
          <input
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Como te chamam?"
            maxLength={30}
            autoComplete="given-name"
            required
          />
        </label>

        <article className="pcard">
          <label className="campo" htmlFor="soeu-texto">
            <span>O que você quer comer?</span>
          </label>
          <textarea
            id="soeu-texto"
            ref={campoTexto}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={3}
            placeholder="Ex.: um lanche rápido e um sorvete, até R$ 40"
            required
          />
          <div className="soeu-exemplos" role="group" aria-label="Exemplos para preencher">
            {EXEMPLOS.map((x) => (
              <button key={x} type="button" className="chip chip-exemplo" onClick={() => setTexto(x)}>
                {x}
              </button>
            ))}
          </div>
          <div className="orcamento">
            <label htmlFor="soeu-orc">Orçamento máximo</label>
            <span className="rs">
              R$
              <input
                id="soeu-orc"
                type="text"
                inputMode="decimal"
                value={orcamento}
                onChange={(e) => setOrcamento(e.target.value)}
                placeholder="sem limite"
                autoComplete="off"
              />
            </span>
          </div>
          {grupo("Preferência", PREFERENCIAS)}
          {grupo("Restrição", RESTRICOES)}
        </article>

        <p className="dica">
          O cardápio nem sempre informa alergia e restrição. Quando o IBits não tiver certeza, ele avisa. Em caso de
          alergia, confirme com a loja.
        </p>

        <div className="rodape-acao">
          <button className="primario" disabled={!pronto}>
            {fase === "erro" ? "Tentar de novo" : "Encontrar meu pedido"}
          </button>
          <p className="consent">Você confere tudo antes de qualquer pedido sair.</p>
        </div>
      </form>
      <p className="rodape">Protótipo de hackathon · não afiliado ao iFood</p>
    </div>
  );
}
