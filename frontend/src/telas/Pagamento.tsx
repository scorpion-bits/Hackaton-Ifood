import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, lerToken } from "../api";
import type { Carrinho, EstadoSala, FormaPagamento, Parte } from "../tipos";
import { brl, precoItem, rotuloItem } from "../componentes/CartaoPessoa";
import Avatar from "../componentes/Avatar";
import ContadorPrazo, { useRestante } from "../componentes/ContadorPrazo";
import Deslizar from "../componentes/Deslizar";
import EsqueletoCartoes from "../componentes/Esqueleto";
import Folha from "../componentes/Folha";
import Icone from "../componentes/Icone";
import Rastro from "../componentes/Rastro";
import { lerPid } from "./Convidado";

const STATUS_ROTULO: Record<string, string> = {
  pendente: "Pendente",
  aguardando_confirmacao: "Aguardando confirmação",
  pago: "Pago",
};
const FORMA_ROTULO: Record<string, string> = {
  pix: "Pix",
  cartao_simulado: "Cartão (simulado)",
  dinheiro: "Dinheiro",
  organizador: "Organizador cobre",
};
/** Mesmo prefixo de `PREFIXO_LOJA_FORA` em `rotas_match.py` (bug 21: loja que o iFood recusou no escolher). */
const PREFIXO_LOJA_FORA = "Não consegui montar o carrinho em ";

function juntarNomes(nomes: string[]): string {
  return nomes.length <= 1 ? (nomes[0] ?? "") : `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}`;
}

function PixQr({ codigo, organizadorNome, demo }: { codigo: string; organizadorNome: string; demo: boolean }) {
  const [img, setImg] = useState("");
  const [copiado, setCopiado] = useState(false);
  useEffect(() => {
    QRCode.toDataURL(codigo, { margin: 1, width: 240 })
      .then(setImg)
      .catch(() => setImg(""));
  }, [codigo]);
  async function copiar() {
    try {
      await navigator.clipboard.writeText(codigo);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1800);
    } catch {
      window.prompt("Copie o código Pix:", codigo);
    }
  }
  return (
    <div className="pix centro">
      {demo && (
        <p className="alerta alerta-demo" role="alert">
          <strong>Demonstração — não pague:</strong> o pedido é fictício. Este código Pix é real e pagável, use só para
          mostrar como a vaquinha funciona.
        </p>
      )}
      {img ? (
        <img className="qr" src={img} alt="QR code do Pix" width={200} height={200} />
      ) : (
        <div className="qr esqueleto" role="img" aria-label="Gerando o QR code do Pix" />
      )}
      <button type="button" className="secundario" onClick={copiar}>
        <Icone nome="copiar" tamanho={16} />
        {copiado ? "Copiado ✓" : "Copiar Pix copia e cola"}
      </button>
      <p className="suave">
        O dinheiro vai direto para {organizadorNome}; ele confirma ao receber.
      </p>
    </div>
  );
}

function MinhaParte({
  salaId,
  sala,
  parte,
  ehOrganizador,
  nomeOrg,
  onErro,
}: {
  salaId: string;
  sala: EstadoSala;
  parte: Parte;
  ehOrganizador: boolean;
  nomeOrg: string;
  onErro: (m: string) => void;
}) {
  const pag = sala.pagamentos?.[parte.participante_id];
  const [ocupado, setOcupado] = useState(false);
  const [trocando, setTrocando] = useState(false);
  const [pixLocal, setPixLocal] = useState("");
  // Forma escolhida agora neste aparelho: aparece na hora, sem esperar o próximo polling (2 s).
  const [formaLocal, setFormaLocal] = useState<FormaPagamento | null>(null);
  const [cartaoAberto, setCartaoAberto] = useState(false);

  const status = pag?.status ?? "pendente";
  const pago = status === "pago";
  const forma = formaLocal ?? pag?.forma;
  const mostrarFormas = !pago && (!forma || trocando);
  const pix = pag?.pix ?? pixLocal;
  // Sem chave do organizador o servidor recusa o Pix (409); a opção já aparece desabilitada. Sem o campo, nada muda.
  const semChavePix = sala.tem_chave_pix === false;
  // O cartão simulado só existe no modo de demonstração; no modo real o servidor recusa (409, bug 27).
  const semCartao = !sala.demonstracao;

  async function pagar(escolhida: FormaPagamento) {
    setOcupado(true);
    onErro("");
    try {
      const r = await api.pagar(salaId, parte.participante_id, escolhida);
      if (r.pix_copia_e_cola) setPixLocal(r.pix_copia_e_cola);
      setFormaLocal(escolhida);
      setTrocando(false);
      setCartaoAberto(false);
    } catch (x) {
      onErro(x instanceof Error ? x.message : "Não consegui registrar o pagamento.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="cartao minha-parte">
      <div className="parte-linha">
        <h2>Sua parte</h2>
        <strong className="valor-grande">{brl(parte.total)}</strong>
      </div>
      <p className="suave">
        Itens {brl(parte.itens)} · taxa {brl(parte.taxa)} · desconto {brl(parte.desconto)}
      </p>

      {pago && (
        <p className="ok">
          ✓ Pago{pag?.forma ? ` · ${FORMA_ROTULO[pag.forma] ?? pag.forma}` : ""}{" "}
          {pag?.forma === "cartao_simulado" && <span className="mini-selo">DEMONSTRAÇÃO</span>}
        </p>
      )}

      {!pago && forma === "pix" && pix && !trocando && (
        <PixQr codigo={pix} organizadorNome={nomeOrg} demo={sala.demonstracao} />
      )}
      {!pago && forma === "dinheiro" && !trocando && (
        <p className="aviso">Entregue o dinheiro em mãos a {nomeOrg}. Ele confirma ao receber.</p>
      )}
      {!pago && forma && status === "aguardando_confirmacao" && !trocando && (
        <p className="suave">Aguardando {nomeOrg} confirmar o recebimento.</p>
      )}

      {!pago && forma && !trocando && (
        <button type="button" className="secundario" onClick={() => setTrocando(true)}>
          Trocar forma de pagamento
        </button>
      )}

      {mostrarFormas && (
        <div className="formas">
          <p className="formas-titulo">Como você quer pagar?</p>
          {!ehOrganizador && (
            <button type="button" className="forma" disabled={ocupado || semChavePix} onClick={() => pagar("pix")}>
              <span className="forma-ico" aria-hidden>
                <Icone nome="raio" tamanho={22} />
              </span>
              <span>
                <strong>Pix</strong>
                <small>{semChavePix ? `${nomeOrg} não cadastrou chave Pix` : `Vai direto para ${nomeOrg}`}</small>
              </span>
            </button>
          )}
          <button
            type="button"
            className="forma"
            disabled={ocupado || semCartao}
            aria-expanded={cartaoAberto && !semCartao}
            onClick={() => setCartaoAberto((v) => !v)}
          >
            <span className="forma-ico" aria-hidden>
              <Icone nome="cartao" tamanho={22} />
            </span>
            <span>
              <strong>
                Cartão <span className="mini-selo">DEMONSTRAÇÃO</span>
              </strong>
              <small>{semCartao ? "Só no modo de demonstração: use Pix ou dinheiro" : "Simulado: nenhuma cobrança real"}</small>
            </span>
          </button>
          {cartaoAberto && !semCartao && (
            <div className="aviso">
              <p>Isto é uma simulação de demonstração. Nenhuma cobrança real será feita.</p>
              <button type="button" className="primario" disabled={ocupado} onClick={() => pagar("cartao_simulado")}>
                {ocupado ? "Registrando…" : `Pagar ${brl(parte.total)} (simulado)`}
              </button>
            </div>
          )}
          {!ehOrganizador && (
            <button type="button" className="forma" disabled={ocupado} onClick={() => pagar("dinheiro")}>
              <span className="forma-ico" aria-hidden>
                <Icone nome="dinheiro" tamanho={22} />
              </span>
              <span>
                <strong>Dinheiro</strong>
                <small>Entrega em mãos a {nomeOrg}</small>
              </span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ListaPartes({
  salaId,
  sala,
  partes,
  organizador,
  prazoEncerrado,
  onErro,
}: {
  salaId: string;
  sala: EstadoSala;
  partes: Parte[];
  organizador: boolean;
  prazoEncerrado: boolean;
  onErro: (m: string) => void;
}) {
  const [ocupado, setOcupado] = useState("");
  const [confirmando, setConfirmando] = useState<{ pid: string; acao: "organizador_cobre" | "remover_itens" } | null>(null);

  async function agir(chave: string, fn: (token: string) => Promise<unknown>) {
    const token = lerToken(salaId);
    if (!token) {
      onErro("Sem permissão de organizador neste aparelho.");
      return;
    }
    setOcupado(chave);
    onErro("");
    try {
      await fn(token);
      setConfirmando(null);
    } catch (x) {
      onErro(x instanceof Error ? x.message : "A ação falhou.");
    } finally {
      setOcupado("");
    }
  }

  const confParte = confirmando ? partes.find((p) => p.participante_id === confirmando.pid) : undefined;
  return (
    <>
      <ul className="partes">
        {partes.map((p) => {
          const pag = sala.pagamentos?.[p.participante_id];
          const status = pag?.status ?? "pendente";
          const pago = status === "pago";
          const podeRecebi = organizador && !pago && (pag?.forma === "pix" || pag?.forma === "dinheiro");
          const podeResolver = organizador && !pago && prazoEncerrado;
          return (
            <li key={p.participante_id} className={`parte prow ${pago ? "paga" : ""}`}>
              <div className="parte-linha">
                <Avatar nome={p.nome} tam="sm" />
                <span className="parte-nome">
                  <strong>{p.nome}</strong>
                  <small>
                    itens {brl(p.itens)} + taxa {brl(p.taxa)} − desconto {brl(p.desconto)}
                  </small>
                </span>
                <strong className="valor-parte">{brl(p.total)}</strong>
              </div>
              <div className="parte-linha">
                <span className={`status-pag ${pago ? "pago" : status === "pendente" ? "pend" : "aguard"}`}>
                  {pago ? "✓ " : ""}
                  {STATUS_ROTULO[status] ?? status}
                </span>
                <span className="suave forma-escolhida">
                  {pag?.forma ? FORMA_ROTULO[pag.forma] ?? pag.forma : "forma não escolhida"}
                  {pag?.forma === "cartao_simulado" && <span className="mini-selo"> DEMONSTRAÇÃO</span>}
                </span>
              </div>
              {podeRecebi && (
                <button
                  type="button"
                  className="secundario"
                  disabled={!!ocupado}
                  onClick={() => agir(`r-${p.participante_id}`, (t) => api.recebi(salaId, p.participante_id, t))}
                >
                  {ocupado === `r-${p.participante_id}` ? "Confirmando…" : "Recebi"}
                </button>
              )}
              {podeResolver && (
                <div className="resolver">
                  <p className="erro">O prazo acabou e {p.nome} não pagou.</p>
                  <button type="button" className="secundario" onClick={() => setConfirmando({ pid: p.participante_id, acao: "organizador_cobre" })}>
                    Eu cubro
                  </button>
                  <button type="button" className="secundario" onClick={() => setConfirmando({ pid: p.participante_id, acao: "remover_itens" })}>
                    Tirar os itens dessa pessoa
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {confirmando && confParte && (
        <Folha
          titulo={confirmando.acao === "organizador_cobre" ? `Cobrir a parte de ${confParte.nome}?` : `Tirar os itens de ${confParte.nome}?`}
          onFechar={() => setConfirmando(null)}
          travada={!!ocupado}
        >
          <p>
            {confirmando.acao === "organizador_cobre"
              ? `Você assume a parte de ${confParte.nome} (${brl(confParte.total)}) e paga por ela.`
              : `Os itens de ${confParte.nome} saem do pedido e os valores são recalculados.`}
          </p>
          <div className="folha-acoes">
            <button
              type="button"
              className="primario"
              disabled={!!ocupado}
              onClick={() => agir(`x-${confParte.participante_id}`, (t) => api.resolver(salaId, confParte.participante_id, t, confirmando.acao))}
            >
              {ocupado ? "Aplicando…" : "Confirmar"}
            </button>
            <button type="button" className="secundario" disabled={!!ocupado} onClick={() => setConfirmando(null)}>
              Recusar
            </button>
          </div>
        </Folha>
      )}
    </>
  );
}

function CartaoLoja({ c }: { c: Carrinho }) {
  return (
    <article className="ord loja-cart">
      <header className="ord-h">
        <Avatar nome={c.loja_nome} tam="md" loja />
        <div>
          <h2>{c.loja_nome}</h2>
          {c.eta_min != null && <small>~{c.eta_min} min</small>}
        </div>
      </header>
      <ul className="linhas">
        {c.itens.map((i, k) => (
          <li key={k} className="line">
            <span>{rotuloItem(i)}</span>
            {precoItem(i) != null && <b>{brl(precoItem(i))}</b>}
          </li>
        ))}
      </ul>
      <dl className="valores">
        <div>
          <dt>Subtotal</dt>
          <dd>{brl(c.subtotal)}</dd>
        </div>
        <div>
          <dt>Taxa de entrega</dt>
          <dd>{brl(c.taxa)}</dd>
        </div>
        {!!c.servico && (
          <div>
            <dt>Taxa de serviço</dt>
            <dd>{brl(c.servico)}</dd>
          </div>
        )}
        <div>
          <dt>Desconto</dt>
          <dd>{brl(c.desconto)}</dd>
        </div>
        <div className="total">
          <dt>Total</dt>
          <dd>{brl(c.total)}</dd>
        </div>
      </dl>
      {c.pagamento && (
        <p className="loja-pagamento">
          <span>Pagamento</span>
          <b>{c.pagamento.nome}</b>
          {c.pagamento.offline && <em className="loja-pagamento-selo">na entrega · nada é cobrado pelo app</em>}
        </p>
      )}
    </article>
  );
}

export default function Pagamento({
  salaId,
  sala,
  organizador,
}: {
  salaId: string;
  sala: EstadoSala;
  organizador: boolean;
}) {
  const [erro, setErro] = useState("");
  const [confirmarEnvio, setConfirmarEnvio] = useState(false);
  const [enviando, setEnviando] = useState(false);
  // Conta de teste no modo real: o servidor avisa que o envio real está desligado (o pedido para no carrinho).
  // Só `=== false` muda a tela; se o campo não vier, tudo segue como antes.
  const [envioDesligado, setEnvioDesligado] = useState(false);
  useEffect(() => {
    if (!organizador || sala.demonstracao) return;
    let vivo = true;
    api
      .saude()
      .then((s) => {
        if (vivo) setEnvioDesligado(s.envio_real_permitido === false);
      })
      .catch(() => {
        /* sem resposta: não muda nada */
      });
    return () => {
      vivo = false;
    };
  }, [organizador, sala.demonstracao]);

  const carrinhos = sala.carrinhos ?? [];
  const n = carrinhos.length;
  const separado = sala.modo_pagamento === "separado";
  const partes = sala.partes ?? [];
  const meuPid = lerPid(salaId);
  const minhaParte = separado ? partes.find((p) => p.participante_id === meuPid) : undefined;
  const nomeOrg = sala.participantes[0]?.nome ?? "o organizador";
  const resta = useRestante(separado ? sala.prazo_fim : undefined);
  const prazoEncerrado = resta != null && resta <= 0;
  const totalGeral = Math.round(carrinhos.reduce((s, c) => s + c.total, 0) * 100) / 100;
  const pagos = partes.filter((p) => sala.pagamentos?.[p.participante_id]?.status === "pago").length;
  // No modo "junto" o servidor aceita enviar assim que os carrinhos existem.
  const podeEnviar = sala.estado === "pronto_para_enviar" || (!separado && sala.estado === "aguardando_pagamentos");

  async function enviar() {
    const token = lerToken(salaId);
    if (!token) {
      setErro("Sem permissão de organizador neste aparelho.");
      setConfirmarEnvio(false);
      return;
    }
    setEnviando(true);
    setErro("");
    try {
      await api.enviar(salaId, token);
      setConfirmarEnvio(false);
    } catch (x) {
      setErro(x instanceof Error ? x.message : "Não consegui enviar os pedidos.");
      setConfirmarEnvio(false);
    } finally {
      setEnviando(false);
    }
  }

  // Bugs 21 e 26: a loja que falhou saiu do pedido; quem só tinha itens nela fica sem parte e precisa aparecer aqui.
  const lojasFora = (sala.avisos ?? []).filter((a) => a.startsWith(PREFIXO_LOJA_FORA));
  const comParte = new Set(partes.map((p) => p.participante_id));
  const semPedido = n > 0 ? sala.participantes.filter((p) => p.respondeu && !comParte.has(p.id)).map((p) => p.nome) : [];

  const falta = partes.filter((p) => sala.pagamentos?.[p.participante_id]?.status !== "pago").length;
  const rotuloTrava = falta > 0 ? `Falta pagar ${falta} de ${partes.length}` : "Aguardando liberação";

  return (
    <section className="tela">
      <h1 className="titulo">Confira antes do ok</h1>

      <div className={`aviso-nota ${n > 1 ? "warn" : "ok"}`} role="note">
        {n === 1
          ? "É 1 pedido: na fatura aparece 1 cobrança e chega 1 entrega."
          : `São ${n} pedidos: na fatura aparecem ${n} cobranças e chegam ${n} entregas.`}
      </div>

      {lojasFora.length > 0 && (
        <div className="aviso" role="status">
          {lojasFora.map((a) => (
            <p key={a}>{a}</p>
          ))}
          {semPedido.length > 0 && (
            <p>
              <strong>
                {juntarNomes(semPedido)} {semPedido.length === 1 ? "ficou" : "ficaram"} sem pedido nesta rodada.
              </strong>
            </p>
          )}
        </div>
      )}

      {n === 0 && <EsqueletoCartoes n={2} rotulo="Montando os carrinhos…" />}
      {carrinhos.map((c) => (
        <CartaoLoja key={c.cart_id} c={c} />
      ))}
      {n > 0 && (
        <div className="sum total-geral">
          <span>Total geral</span>
          <strong>{brl(totalGeral)}</strong>
        </div>
      )}

      {separado && (
        <>
          <h2 className="sec2">Vaquinha</h2>
          {sala.estado === "aguardando_pagamentos" && sala.prazo_fim && <ContadorPrazo prazoFim={sala.prazo_fim} />}
          <p className="progresso">
            <strong>
              {pagos} de {partes.length}
            </strong>{" "}
            pagos
            <span className="barra-prog" aria-hidden>
              <span style={{ width: `${partes.length ? (pagos / partes.length) * 100 : 0}%` }} />
            </span>
          </p>
          {minhaParte && (
            <MinhaParte
              salaId={salaId}
              sala={sala}
              parte={minhaParte}
              ehOrganizador={organizador}
              nomeOrg={nomeOrg}
              onErro={setErro}
            />
          )}
          <ListaPartes
            salaId={salaId}
            sala={sala}
            partes={partes}
            organizador={organizador}
            prazoEncerrado={prazoEncerrado}
            onErro={setErro}
          />
        </>
      )}

      {!separado && (
        <div className="cartao">
          <h2>Pagamento único</h2>
          <p className="suave">
            {sala.participantes.length === 1
              ? "Você paga o total no iFood."
              : organizador
                ? "Você paga o total no iFood e acerta com o grupo depois."
                : "O organizador paga tudo e acerta com o grupo."}
          </p>
        </div>
      )}

      {erro && (
        <div className="alerta alerta-erro" role="alert">
          {erro}
        </div>
      )}

      {organizador ? (
        <div className="rodape-acao">
          <Deslizar
            bloqueado={!podeEnviar || enviando}
            rotulo="Deslize para enviar"
            rotuloBloqueado={rotuloTrava}
            emEspera={confirmarEnvio}
            onConfirmar={() => setConfirmarEnvio(true)}
          />
          <p className="consent">
            {podeEnviar
              ? envioDesligado
                ? "Conta de teste: o envio real está desligado; o pedido para no carrinho."
                : "Ao deslizar, você abre o resumo final. Nada é enviado antes do seu ok."
              : "O pedido só sai depois que 100% estiver pago."}
          </p>
          {podeEnviar && (
            <button type="button" className="link-btn centro-btn" disabled={enviando} onClick={() => setConfirmarEnvio(true)}>
              Enviar sem deslizar
            </button>
          )}
        </div>
      ) : (
        <p className="dica centro-txt" role="status">
          {sala.estado === "pronto_para_enviar"
            ? "Tudo pago! O organizador vai enviar os pedidos."
            : "O organizador envia os pedidos quando todos pagarem."}
        </p>
      )}

      {confirmarEnvio && (
        <Folha titulo="Confirmar envio" onFechar={() => setConfirmarEnvio(false)} travada={enviando}>
          {sala.demonstracao && <p className="mini-selo selo-folha">DEMONSTRAÇÃO · nenhum pedido real</p>}
          {envioDesligado && (
            <p className="alerta alerta-demo" role="note">
              <strong>Conta de teste</strong> O envio real está desligado; o pedido para no carrinho.
            </p>
          )}
          <ul className="resumo-env">
            {carrinhos.map((c) => (
              <li key={c.cart_id}>
                <span>{c.loja_nome}</span>
                <strong>{brl(c.total)}</strong>
              </li>
            ))}
            <li className="total">
              <span>Total</span>
              <strong>{brl(totalGeral)}</strong>
            </li>
          </ul>
          <div className="folha-acoes">
            <button type="button" className="primario" disabled={enviando} onClick={enviar}>
              {envioDesligado
                ? enviando
                  ? "Montando…"
                  : "Ver como ficaria"
                : enviando
                  ? "Enviando…"
                  : `Confirmo enviar ${n} ${n === 1 ? "pedido" : "pedidos"} ao iFood`}
            </button>
            <button type="button" className="secundario" disabled={enviando} onClick={() => setConfirmarEnvio(false)}>
              Recusar
            </button>
          </div>
        </Folha>
      )}

      <Rastro itens={sala.rastro} />
    </section>
  );
}
