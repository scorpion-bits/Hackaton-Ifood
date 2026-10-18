import { useMemo, type ReactNode } from "react";
import type { Candidato, Combinacao, EstadoSala } from "../tipos";
import { brl } from "../componentes/CartaoPessoa";
import { IconeFaisca, IconeX, Rosto, corPessoa, emojiLoja, gradienteLoja } from "../componentes/leilao/visual";
import {
  afinidadeDe,
  agruparPorPessoa,
  felizesDe,
  chaveItem,
  juntarIguais,
  lojasDa,
  pessoasDoGrupo,
} from "../componentes/leilao/util";
import "../leilao.css";

const ALERGENO = /confirme com a loja/i;
const APROXIMADA = /^\s*op[cç][aã]o aproximada:/i;

function Motivo({ texto }: { texto: string }) {
  if (!texto) return null;
  return APROXIMADA.test(texto) ? (
    <em className="ld-motivo ld-aprox">{texto}</em>
  ) : (
    <em className="ld-motivo">{texto}</em>
  );
}

function Linhas({
  c,
  sala,
  pids,
  mostrarSem,
  antes,
}: {
  c: Combinacao;
  sala: EstadoSala;
  pids: string[];
  mostrarSem: boolean;
  /** Itens que a opção tinha antes do ajuste (chave `chaveItem`); o que não está aqui é "Novo". */
  antes: Set<string> | null;
}) {
  const grupos = agruparPorPessoa(c.escolhas);
  const nomeDe = (pid: string) => sala.participantes.find((p) => p.id === pid)?.nome ?? "Convidado";
  const corDe = (pid: string) => corPessoa(Math.max(0, sala.participantes.findIndex((p) => p.id === pid)));
  return (
    <ul className="ld-why">
      {pids.flatMap((pid) => {
        const itens = grupos[pid];
        if (!itens) {
          return mostrarSem
            ? [
                <li key={pid} className="sem">
                  <Rosto nome={nomeDe(pid)} cor={corDe(pid)} classe="ld-face-p" />
                  <div>
                    <b>{nomeDe(pid)}</b>
                    <span className="it">Sem opção nesta combinação</span>
                  </div>
                  <strong aria-label="sem preço">—</strong>
                </li>,
              ]
            : [];
        }
        return juntarIguais(itens).map((i: Candidato, k) => {
          const novo = !!antes && !antes.has(chaveItem(pid, i));
          return (
          <li key={`${pid}-${i.item_id}-${k}`} className={novo ? "novo" : undefined}>
            <Rosto nome={nomeDe(pid)} cor={corDe(pid)} classe="ld-face-p" />
            <div>
              <b>
                {nomeDe(pid)}
                {novo && <span className="ld-novo">Novo</span>}
              </b>
              <span className="it">
                {i.item_nome} · {i.loja_nome.replace(/\s*\(demo\)\s*$/i, "")}
              </span>
              <Motivo texto={i.motivo} />
              {ALERGENO.test(i.motivo) && (
                <small className="ld-aviso-mini">Alergia ou restrição pode não constar no cardápio. Confirme com a loja.</small>
              )}
            </div>
            <strong>{brl(i.preco)}</strong>
          </li>
          );
        });
      })}
    </ul>
  );
}

function Cartao({
  c,
  sala,
  avisos,
  pids,
  mostrarSem,
  totalPessoas,
  rotulo,
  antes,
  atualizado,
}: {
  c: Combinacao;
  sala: EstadoSala;
  avisos: string[];
  pids: string[];
  mostrarSem: boolean;
  totalPessoas: number;
  rotulo: string;
  antes: Set<string> | null;
  atualizado: boolean;
}) {
  const lojas = lojasDa(c);
  const n = lojas.length;
  const afin = afinidadeDe(c);
  const itens = Object.values(c.escolhas);
  // convidado vê só a parte dele (o smoke achou "Esta é a sua parte" com o total do grupo embaixo)
  const so = pids.length < totalPessoas;
  const meus = so ? Object.entries(c.escolhas).filter(([slot]) => pids.includes(slot.split("#")[0])).map(([, i]) => i) : itens;
  const totalItens = Math.round(meus.reduce((s, i) => s + i.preco, 0) * 100) / 100;
  const etas = itens.map((i) => i.eta_min).filter((e): e is number => typeof e === "number");
  const eta = etas.length ? Math.max(...etas) : null;
  const explicacao = c.explicacao ?? "";
  const avs = avisos.filter((a) => !explicacao.includes(a));
  return (
    <>
      <div className="ld-foto" style={{ background: gradienteLoja(lojas[0]?.id ?? "x") }} aria-hidden="true">
        {lojas.map((l) => (
          <span key={l.id}>{emojiLoja(l.nome, l.vertical)}</span>
        ))}
        <span className="ld-bdg ld-pct">{afin}% afinidade</span>
        <span className={`ld-bdg ${n > 1 ? "dois" : "um"}`}>{n > 1 ? `${n} pedidos` : "1 pedido"}</span>
        {atualizado && (
          <span className="ld-bdg ld-atualizado">
            <IconeFaisca tamanho={14} /> Atualizado
          </span>
        )}
      </div>
      <div className="ld-cbody">
        <p className="ld-legenda">Quanto os pratos combinam com o que cada um pediu, segundo a IA.</p>
        <h2 className="ld-cnome">{lojas.map((l) => l.nome).join(" + ") || rotulo}</h2>
        <div className="ld-cmeta">
          <span>
            {felizesDe(c)} de {Math.max(totalPessoas, 1)} bem atendidos
          </span>
          {eta !== null && <span>até {eta} min</span>}
        </div>
        <Linhas c={c} sala={sala} pids={pids} mostrarSem={mostrarSem} antes={antes} />
        <p className={`ld-note ${n > 1 ? "warn" : "ok"}`}>
          {n > 1 ? `Dividido em ${n} pedidos: ${n} entregas.` : "Um pedido só: uma entrega."}{" "}
          {c.taxa_conhecida
            ? "A taxa de entrega estimada pela busca do iFood já entrou na escolha; o valor final aparece no carrinho antes do seu ok."
            : "A taxa de cada entrega aparece no carrinho antes do seu ok."}
        </p>
        {explicacao && <p className="ld-explica">{explicacao}</p>}
        {avs.map((a, i) => (
          <p key={i} className="ld-aviso">
            {a}
          </p>
        ))}
      </div>
      <div className="ld-cfoot">
        <div>
          <div className="ld-tot">{brl(totalItens)}</div>
          <small>
            {so ? "seus itens · a taxa é dividida no pagamento" : c.taxa_conhecida ? "itens · taxa já considerada na escolha" : "só itens · taxa no carrinho"}
          </small>
        </div>
        <span className={`ld-tx${n > 1 ? " w" : ""}`}>
          {n} {n > 1 ? "entregas" : "entrega"}
        </span>
      </div>
    </>
  );
}

/**
 * Resultado (C13, sem "deck"): o IBits já escolheu a melhor combinação e ela aparece direto, num cartão só.
 * Mudar = "Ajustar com o IBits" (rodapé, só organizador); "Confirmar pedido" segue para como pagar.
 * Convidado vê só a própria parte, em leitura.
 */
export default function Deck({
  sala,
  combinacoes,
  avisos,
  organizador,
  meuPid,
  onConfirmar,
  onVerLeilao,
  rodape,
  ocupado = false,
  atualizado = false,
  faixa,
  onFecharFaixa,
  anteriores,
  solo = false,
  fechando = false,
  erroFechar = "",
}: {
  sala: EstadoSala;
  combinacoes: Combinacao[];
  avisos: string[];
  organizador: boolean;
  meuPid: string | null;
  onConfirmar: () => void;
  onVerLeilao?: () => void;
  /** C14: bloco abaixo do cartão (só o organizador recebe: "Ajustar com o IBits"). */
  rodape?: ReactNode;
  /** C14: um ajuste está sendo refeito; "Confirmar pedido" fica travado até terminar. */
  ocupado?: boolean;
  /** C14: destaque "Atualizado" no cartão logo depois de um ajuste. */
  atualizado?: boolean;
  /** C14: faixa no topo (convidado: "O organizador ajustou o pedido"). */
  faixa?: string;
  onFecharFaixa?: () => void;
  /** C14: opções de antes do ajuste, para marcar os itens novos. */
  anteriores?: Combinacao[];
  /** Sala de 1 pessoa: "Confirmar pedido" já monta o carrinho (não há o que dividir). */
  solo?: boolean;
  /** O botão principal já está montando o pedido (sala de 1 pessoa). */
  fechando?: boolean;
  erroFechar?: string;
}) {
  const c = combinacoes[0];
  const pidsTodos = pessoasDoGrupo(sala, c);
  // Convidado vê só a própria parte (se não sabemos quem é, mostra tudo em leitura).
  const pids = pidsTodos.filter((pid) => organizador || !meuPid || pid === meuPid);
  const antes = anteriores?.[0];
  const existiam = useMemo(() => {
    if (!antes) return null;
    const s = new Set<string>();
    for (const [slot, i] of Object.entries(antes.escolhas)) s.add(chaveItem(slot.split("#")[0], i));
    return s;
  }, [antes]);

  const titulo = solo ? "Seu pedido" : "O pedido do grupo";
  const sub = !organizador
    ? "Esta é a sua parte. O organizador confirma o pedido e escolhe como pagar."
    : solo
      ? "O IBits escolheu o que mais combina com o que você pediu."
      : "O IBits juntou o que cada um pediu e escolheu a melhor combinação.";

  return (
    <section className="tela ld-raiz ld-resultado" aria-label="Pedido montado pelo IBits">
      <div className="ld-top">
        <span className="ld-step">Resultado</span>
        {onVerLeilao && (
          <button type="button" className="ld-skip" onClick={onVerLeilao}>
            Rever a avaliação
          </button>
        )}
      </div>
      <p className="ld-sr" role="status" aria-live="polite">
        {atualizado ? "Pedido atualizado." : ""}
      </p>
      {faixa && (
        <div className="ld-faixa" role="status">
          <IconeFaisca tamanho={16} />
          <span>{faixa}</span>
          {onFecharFaixa && (
            <button type="button" onClick={onFecharFaixa} aria-label="Fechar aviso">
              <IconeX tamanho={16} />
            </button>
          )}
        </div>
      )}

      <div className="ld-cab">
        <h1>{titulo}</h1>
        <p>{sub}</p>
      </div>

      <article className={`ld-cartao${atualizado ? " ld-atual" : ""}`} aria-label="Pedido escolhido pelo IBits">
        <Cartao
          c={c}
          sala={sala}
          avisos={avisos}
          pids={pids}
          mostrarSem={organizador}
          totalPessoas={pidsTodos.length}
          rotulo="Pedido"
          antes={existiam}
          atualizado={atualizado}
        />
      </article>

      {!organizador && <p className="ld-dica">O organizador está confirmando o pedido e o modo de pagamento.</p>}
      {rodape}
      {/* Fixo embaixo: o pedido é longo e o "Confirmar" precisa estar sempre à mão. */}
      {organizador && (
        <div className="rodape-acao ld-confirmar">
          {erroFechar && (
            <p className="erro" role="alert">
              {erroFechar}
            </p>
          )}
          <button type="button" className="primario" onClick={onConfirmar} disabled={ocupado || fechando}>
            {fechando ? "Montando o carrinho…" : "Confirmar pedido"}
          </button>
          <p className="ld-dica">
            {ocupado
              ? "O IBits está refazendo o pedido. Já já ele aparece atualizado."
              : solo
                ? "Você revisa o carrinho antes de qualquer envio ao iFood."
                : "Depois você escolhe como pagar. Nada vai ao iFood sem o seu ok."}
          </p>
        </div>
      )}
    </section>
  );
}
