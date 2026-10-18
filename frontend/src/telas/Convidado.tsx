import { useState } from "react";
import { api, apagarLocal, chaveEu, gravarLocal, lerLocal, type Eu } from "../api";
import type { EstadoSala } from "../tipos";
import Icone from "../componentes/Icone";

// Os valores seguem iguais aos de antes (a API recebe exatamente estas palavras); só foram agrupados na tela.
export const PREFERENCIAS = ["barato", "rápido", "leve", "apimentado"];
export const RESTRICOES = ["vegetariano", "vegano", "sem lactose", "sem glúten"];
export const CHIPS = [...PREFERENCIAS, ...RESTRICOES];
const maiuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export const chavePid = (salaId: string) => `match.pid.${salaId}`;
export const lerPid = (salaId: string) => lerLocal<string>(chavePid(salaId));

/**
 * `resp`/`total`: todos que contam para rodar (o organizador só entra se já respondeu). Serve ao convidado.
 * `convResp`/`convTotal`: só os convidados (sem o organizador); `euResp`: o organizador já respondeu.
 * `pidOrg` desconhecido: o 1º da lista é o organizador.
 */
export function contagemRespostas(
  sala: EstadoSala,
  pidOrg?: string | null,
): { resp: number; total: number; convResp: number; convTotal: number; euResp: boolean } {
  const orgId = pidOrg ?? sala.participantes[0]?.id;
  const lista = sala.participantes.filter((p) => p.respondeu || p.id !== orgId);
  const convidados = sala.participantes.filter((p) => p.id !== orgId);
  return {
    resp: lista.filter((p) => p.respondeu).length,
    total: lista.length,
    convResp: convidados.filter((p) => p.respondeu).length,
    convTotal: convidados.length,
    euResp: sala.participantes.some((p) => p.id === orgId && p.respondeu),
  };
}

/** Formulário curto (nome, desejo, orçamento, chips). Usado pelo convidado e pelo organizador. */
export function FormDesejo({
  salaId,
  nomeInicial,
  rotuloBotao,
  onFeito,
  rodapeFixo = false,
}: {
  salaId: string;
  nomeInicial?: string;
  rotuloBotao: string;
  onFeito: () => void;
  /** Botão grudado no pé da tela (convidado). No organizador fica junto do formulário. */
  rodapeFixo?: boolean;
}) {
  const eu = lerLocal<Eu>(chaveEu);
  const [nome, setNome] = useState(nomeInicial ?? eu?.nome ?? "");
  const [texto, setTexto] = useState("");
  const [orcamento, setOrcamento] = useState("");
  const [chips, setChips] = useState<string[]>(eu?.chips ?? []);
  const [lembrar, setLembrar] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  const alternar = (c: string) =>
    setChips((l) => (l.includes(c) ? l.filter((x) => x !== c) : [...l, c]));

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!nome.trim() || !texto.trim()) return;
    setEnviando(true);
    setErro("");
    try {
      let pid = lerPid(salaId);
      if (!pid) {
        pid = (await api.entrar(salaId, nome.trim())).participante_id;
        gravarLocal(chavePid(salaId), pid);
      }
      const valor = parseFloat(orcamento.replace(",", "."));
      await api.desejo(salaId, pid, {
        texto: texto.trim(),
        orcamento_max: Number.isFinite(valor) && valor > 0 ? valor : null,
        chips,
      });
      if (lembrar) gravarLocal(chaveEu, { nome: nome.trim(), chips });
      onFeito();
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui enviar.");
    } finally {
      setEnviando(false);
    }
  }

  const grupo = (titulo: string, lista: string[]) => (
    <div className="chgrupo">
      <span className="chrotulo" id={`ch-${titulo}`}>{titulo}</span>
      <div className="grupo-chips" role="group" aria-labelledby={`ch-${titulo}`}>
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

  const botao = (
    <div className={rodapeFixo ? "rodape-acao" : "form-acao"}>
      {erro && (
        <div className="alerta alerta-erro" role="alert">
          {erro}
        </div>
      )}
      <button className="primario" disabled={enviando || !nome.trim() || !texto.trim()}>
        {enviando ? "Enviando…" : rotuloBotao}
      </button>
      <label className="lembrar">
        <input type="checkbox" checked={lembrar} onChange={(e) => setLembrar(e.target.checked)} />
        Lembrar de mim neste aparelho
      </label>
    </div>
  );

  return (
    <form className={rodapeFixo ? "form-desejo form-fixo" : "form-desejo"} onSubmit={enviar}>
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
        <label className="campo" htmlFor={`texto-${salaId}`}>
          <span>O que você quer comer?</span>
        </label>
        <textarea
          id={`texto-${salaId}`}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={3}
          placeholder="Ex.: um lanche rápido e um sorvete, até R$ 40"
          required
        />
        <div className="orcamento">
          <label htmlFor={`orc-${salaId}`}>Orçamento máximo</label>
          <span className="rs">
            R$
            <input
              id={`orc-${salaId}`}
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
      {botao}
    </form>
  );
}

export default function Convidado({ salaId, sala }: { salaId: string; sala: EstadoSala | null }) {
  const [enviado, setEnviado] = useState(() => {
    const pid = lerPid(salaId);
    return !!pid && !!sala?.participantes.find((p) => p.id === pid)?.respondeu;
  });
  const [editando, setEditando] = useState(false);
  const [, setTick] = useState(0);
  const pid = lerPid(salaId);
  const meuNome = sala?.participantes.find((p) => p.id === pid)?.nome;

  function naoSou() {
    apagarLocal(chavePid(salaId));
    setEnviado(false);
    setEditando(false);
    setTick((t) => t + 1);
  }
  const botaoNaoSou = pid ? (
    <button type="button" className="link-btn centro-btn" onClick={naoSou}>
      Não sou {meuNome ?? "essa pessoa"}
    </button>
  ) : null;
  const nomeOrg = sala?.participantes[0]?.nome;
  const respondeu = !!pid && (enviado || !!sala?.participantes.find((p) => p.id === pid)?.respondeu);

  if (!respondeu || editando) {
    return (
      <section className="tela">
        {nomeOrg && (
          <div className="guestbar">
            <Icone nome="celular" tamanho={16} />
            Você entrou na sala de {nomeOrg}. Sem cadastro.
          </div>
        )}
        <h1 className="titulo">O que você quer?</h1>
        <p className="sub">Escreva do seu jeito. O IBits entende preço, pressa, restrição e vontade. Leva menos de 30 segundos.</p>
        <FormDesejo
          salaId={salaId}
          rodapeFixo
          rotuloBotao={editando ? "Atualizar meu pedido" : "Enviar meu pedido"}
          onFeito={() => {
            setEnviado(true);
            setEditando(false);
          }}
        />
        {botaoNaoSou}
      </section>
    );
  }

  const cont = sala ? contagemRespostas(sala) : null;
  return (
    <section className="tela">
      <div className="cartao centro pronto">
        <div className="feito-ic" aria-hidden="true">
          <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </div>
        <h1 className="titulo">Pronto{meuNome ? `, ${meuNome}` : ""}!</h1>
        <p>Seu pedido foi para a sala. Aguarde o organizador rodar o Match.</p>
        <p className="aguardando" role="status">
          <span className="digitando" aria-hidden="true"><i /><i /><i /></span>
          {cont ? `${cont.resp} de ${cont.total} responderam` : "Aguardando a turma"}
        </p>
        <button className="secundario" onClick={() => setEditando(true)}>
          Mudar meu pedido
        </button>
        {botaoNaoSou}
      </div>
    </section>
  );
}
