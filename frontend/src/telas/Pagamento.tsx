import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api, lerToken } from "../api";
import type { Carrinho, EstadoSala, FormaPagamento, Parte } from "../tipos";
import { brl, rotuloItem } from "../componentes/CartaoPessoa";
import ContadorPrazo, { useRestante } from "../componentes/ContadorPrazo";
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
};

function PixQr({ codigo, organizadorNome }: { codigo: string; organizadorNome: string }) {
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
      {img ? <img className="qr" src={img} alt="QR code do Pix" width={200} height={200} /> : <div className="qr" />}
      <button className="secundario" onClick={copiar}>
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
  const [cartaoAberto, setCartaoAberto] = useState(false);

  const status = pag?.status ?? "pendente";
  const pago = status === "pago";
  const mostrarFormas = !pago && (!pag?.forma || trocando);
  const pix = pag?.pix ?? pixLocal;

  async function pagar(forma: FormaPagamento) {
    setOcupado(true);
    onErro("");
    try {
      const r = await api.pagar(salaId, parte.participante_id, forma);
      if (r.pix_copia_e_cola) setPixLocal(r.pix_copia_e_cola);
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
      <h2>Sua parte: {brl(parte.total)}</h2>
      <p className="suave">
        Itens {brl(parte.itens)} · taxa {brl(parte.taxa)} · desconto {brl(parte.desconto)}
      </p>

      {pago && (
        <p className="ok">
          Pago{pag?.forma ? ` · ${FORMA_ROTULO[pag.forma] ?? pag.forma}` : ""} ✓
          {pag?.forma === "cartao_simulado" && <span className="mini-selo"> DEMONSTRAÇÃO</span>}
        </p>
      )}

      {!pago && pag?.forma === "pix" && pix && !trocando && <PixQr codigo={pix} organizadorNome={nomeOrg} />}
      {!pago && pag?.forma === "dinheiro" && !trocando && (
        <p className="aviso">Entregue o dinheiro em mãos a {nomeOrg}. Ele confirma ao receber.</p>
      )}
      {!pago && pag?.forma && status === "aguardando_confirmacao" && !trocando && (
        <p className="suave">Aguardando {nomeOrg} confirmar o recebimento.</p>
      )}

      {!pago && pag?.forma && !trocando && (
        <button className="secundario" onClick={() => setTrocando(true)}>
          Trocar forma de pagamento
        </button>
      )}

      {mostrarFormas && (
        <div className="formas">
          <p>
            <strong>Como você quer pagar?</strong>
          </p>
          {!ehOrganizador && (
            <button className="forma" disabled={ocupado} onClick={() => pagar("pix")}>
              <span className="forma-ico" aria-hidden>
                ⚡
              </span>
              <span>
                <strong>Pix</strong>
                <small>Vai direto para {nomeOrg}</small>
              </span>
            </button>
          )}
          <button className="forma" disabled={ocupado} onClick={() => setCartaoAberto((v) => !v)}>
            <span className="forma-ico" aria-hidden>
              💳
            </span>
            <span>
              <strong>
                Cartão <span className="mini-selo">DEMONSTRAÇÃO</span>
              </strong>
              <small>Simulado: nenhuma cobrança real</small>
            </span>
          </button>
          {cartaoAberto && (
            <div className="aviso">
              <p>Isto é uma simulação de demonstração. Nenhuma cobrança real será feita.</p>
              <button className="primario" disabled={ocupado} onClick={() => pagar("cartao_simulado")}>
                {ocupado ? "Registrando…" : `Pagar ${brl(parte.total)} (simulado)`}
              </button>
            </div>
          )}
          {!ehOrganizador && (
            <button className="forma" disabled={ocupado} onClick={() => pagar("dinheiro")}>
              <span className="forma-ico" aria-hidden>
                💵
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

  return (
    <ul className="partes">
      {partes.map((p) => {
        const pag = sala.pagamentos?.[p.participante_id];
        const status = pag?.status ?? "pendente";
        const pago = status === "pago";
        const podeRecebi = organizador && !pago && (pag?.forma === "pix" || pag?.forma === "dinheiro");
        const podeResolver = organizador && !pago && prazoEncerrado;
        const conf = confirmando?.pid === p.participante_id ? confirmando : null;
        return (
          <li key={p.participante_id} className="parte">
            <div className="parte-linha">
              <strong>{p.nome}</strong>
              <span className={`status-pag ${pago ? "pago" : status === "pendente" ? "pend" : "aguard"}`}>
                {STATUS_ROTULO[status] ?? status}
              </span>
            </div>
            <p className="suave">
              Itens {brl(p.itens)} · taxa {brl(p.taxa)} · desconto {brl(p.desconto)}
            </p>
            <div className="parte-linha">
              <span className="suave">
                {pag?.forma ? FORMA_ROTULO[pag.forma] ?? pag.forma : "forma não escolhida"}
                {pag?.forma === "cartao_simulado" && <span className="mini-selo"> DEMONSTRAÇÃO</span>}
              </span>
              <strong>{brl(p.total)}</strong>
            </div>
            {podeRecebi && (
              <button
                className="secundario"
                disabled={!!ocupado}
                onClick={() => agir(`r-${p.participante_id}`, (t) => api.recebi(salaId, p.participante_id, t))}
              >
                {ocupado === `r-${p.participante_id}` ? "Confirmando…" : "Recebi"}
              </button>
            )}
            {podeResolver && !conf && (
              <div className="resolver">
                <p className="erro">O prazo acabou e {p.nome} não pagou.</p>
                <button className="secundario" onClick={() => setConfirmando({ pid: p.participante_id, acao: "organizador_cobre" })}>
                  Eu cubro
                </button>
                <button className="secundario" onClick={() => setConfirmando({ pid: p.participante_id, acao: "remover_itens" })}>
                  Tirar os itens dessa pessoa
                </button>
              </div>
            )}
            {conf && (
              <div className="aviso">
                <p>
                  {conf.acao === "organizador_cobre"
                    ? `Você assume a parte de ${p.nome} (${brl(p.total)}) e paga por ela.`
                    : `Os itens de ${p.nome} saem do pedido e os valores são recalculados.`}
                </p>
                <button
                  className="primario"
                  disabled={!!ocupado}
                  onClick={() => agir(`x-${p.participante_id}`, (t) => api.resolver(salaId, p.participante_id, t, conf.acao))}
                >
                  {ocupado ? "Aplicando…" : "Confirmar"}
                </button>
                <button className="secundario" disabled={!!ocupado} onClick={() => setConfirmando(null)}>
                  Cancelar
                </button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function CartaoLoja({ c }: { c: Carrinho }) {
  return (
    <div className="cartao loja-cart">
      <div className="parte-linha">
        <h2>{c.loja_nome}</h2>
        {c.eta_min != null && <span className="suave">~{c.eta_min} min</span>}
      </div>
      <ul className="itens-cart">
        {c.itens.map((i, k) => (
          <li key={k}>{rotuloItem(i)}</li>
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
        <div>
          <dt>Desconto</dt>
          <dd>{brl(c.desconto)}</dd>
        </div>
        <div className="total">
          <dt>Total</dt>
          <dd>{brl(c.total)}</dd>
        </div>
      </dl>
    </div>
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

  return (
    <section className="tela">
      <h1>Revisão e pagamento</h1>

      <div className="aviso-forte" role="note">
        {n === 1
          ? "É 1 pedido: na fatura aparece 1 cobrança e chega 1 entrega."
          : `São ${n} pedidos: na fatura aparecem ${n} cobranças e chegam ${n} entregas.`}
      </div>

      {carrinhos.map((c) => (
        <CartaoLoja key={c.cart_id} c={c} />
      ))}
      <div className="cartao total-geral">
        <span>Total geral</span>
        <strong>{brl(totalGeral)}</strong>
      </div>

      {separado && (
        <>
          <h2>Vaquinha</h2>
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
          <p className="suave">{organizador ? "Você paga o total no iFood e acerta com o grupo depois." : "O organizador paga tudo e acerta com o grupo."}</p>
        </div>
      )}

      {erro && <p className="erro" role="alert">{erro}</p>}

      {organizador ? (
        <>
          <button className="primario" disabled={!podeEnviar || enviando} onClick={() => setConfirmarEnvio(true)}>
            Enviar pedidos
          </button>
          {!podeEnviar && <p className="suave centro-txt">Libera quando todas as partes estiverem pagas.</p>}
        </>
      ) : (
        <p className="suave centro-txt">
          {sala.estado === "pronto_para_enviar"
            ? "Tudo pago! O organizador vai enviar os pedidos."
            : "O organizador envia os pedidos quando todos pagarem."}
        </p>
      )}

      {confirmarEnvio && (
        <div className="fundo-modal" role="presentation">
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="t-env">
            <h2 id="t-env">Confirmar envio</h2>
            {sala.demonstracao && <p className="mini-selo">DEMONSTRAÇÃO · nenhum pedido real</p>}
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
            <button className="primario" disabled={enviando} onClick={enviar}>
              {enviando ? "Enviando…" : `Confirmo enviar ${n} ${n === 1 ? "pedido" : "pedidos"} ao iFood`}
            </button>
            <button className="secundario" disabled={enviando} onClick={() => setConfirmarEnvio(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      <Rastro itens={sala.rastro} />
    </section>
  );
}
