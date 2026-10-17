import { useState } from "react";
import { api, apagarLocal, chaveEu, gravarLocal, lerLocal, type Eu } from "../api";
import type { EstadoSala } from "../tipos";

export const CHIPS = [
  "vegetariano",
  "vegano",
  "sem lactose",
  "sem glúten",
  "apimentado",
  "leve",
  "barato",
  "rápido",
];

export const chavePid = (salaId: string) => `match.pid.${salaId}`;
export const lerPid = (salaId: string) => lerLocal<string>(chavePid(salaId));

/** Convidados = todos, menos o organizador que ainda não respondeu. `pidOrg` desconhecido: o 1º da lista é o organizador. */
export function contagemRespostas(sala: EstadoSala, pidOrg?: string | null): { resp: number; total: number } {
  const orgId = pidOrg ?? sala.participantes[0]?.id;
  const lista = sala.participantes.filter((p) => p.respondeu || p.id !== orgId);
  return { resp: lista.filter((p) => p.respondeu).length, total: lista.length };
}

/** Formulário curto (nome, desejo, orçamento, chips). Usado pelo convidado e pelo organizador. */
export function FormDesejo({
  salaId,
  nomeInicial,
  rotuloBotao,
  onFeito,
}: {
  salaId: string;
  nomeInicial?: string;
  rotuloBotao: string;
  onFeito: () => void;
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

  return (
    <form className="cartao form" onSubmit={enviar}>
      <label>
        Seu nome
        <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Como te chamam?" required />
      </label>
      <label>
        O que você quer?
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={3}
          placeholder="Ex.: um lanche sem cebola · algo leve com salada · pizza de calabresa"
          required
        />
      </label>
      <label>
        Orçamento (R$, opcional)
        <input
          type="text"
          inputMode="decimal"
          value={orcamento}
          onChange={(e) => setOrcamento(e.target.value)}
          placeholder="Ex.: 45,50"
        />
      </label>
      <div className="grupo-chips" role="group" aria-label="Preferências">
        {CHIPS.map((c) => (
          <button
            key={c}
            type="button"
            className={`chip ${chips.includes(c) ? "on" : ""}`}
            aria-pressed={chips.includes(c)}
            onClick={() => alternar(c)}
          >
            {c}
          </button>
        ))}
      </div>
      <label className="check">
        <input type="checkbox" checked={lembrar} onChange={(e) => setLembrar(e.target.checked)} />
        Lembrar de mim neste aparelho
      </label>
      {erro && <p className="erro">{erro}</p>}
      <button className="primario" disabled={enviando || !nome.trim() || !texto.trim()}>
        {enviando ? "Enviando…" : rotuloBotao}
      </button>
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
  const respondeu = !!pid && (enviado || !!sala?.participantes.find((p) => p.id === pid)?.respondeu);

  if (!respondeu || editando) {
    return (
      <section className="tela">
        <h1>Entrar no Match</h1>
        <p className="suave">Leva menos de 30 segundos. Sem cadastro.</p>
        <FormDesejo
          salaId={salaId}
          rotuloBotao={editando ? "Atualizar meu pedido" : "Enviar meu desejo"}
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
      <div className="cartao centro">
        <div className="grande">✅</div>
        <h1>Pronto!</h1>
        <p>Aguarde o organizador rodar o Match.</p>
        {cont && (
          <p className="suave">
            {cont.resp} de {cont.total} responderam
          </p>
        )}
        <button className="secundario" onClick={() => setEditando(true)}>
          Mudar meu pedido
        </button>
        {botaoNaoSou}
      </div>
    </section>
  );
}
