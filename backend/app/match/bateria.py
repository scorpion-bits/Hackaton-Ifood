"""Bateria automática do Match: frases e salas inteiras pela API, do desejo até os carrinhos, sem enviar pedido.

Uso (na pasta backend):
    .venv/bin/python -m app.match.bateria            # modo demonstração (qualquer máquina, sem internet)
    .venv/bin/python -m app.match.bateria --real     # MCP real (precisa do .env e do login do iFood feito no app)
    .venv/bin/python -m app.match.bateria --sem-ia   # força o intérprete/juiz determinísticos (sem LLM)

Grava `docs/testes/bateria/<modo>-<ddhhmm>.md` com invariantes (✅/❌) e métricas medidas — os números do pitch saem
daqui, nunca de cabeça. Sai com código 1 se algum invariante falhar (dá para usar em CI e nos agentes).
Nunca chama `submitOrder`: para no `escolher` (carrinhos montados), com `IFOOD_MCP_PERMITIR_ENVIO` desligado.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[3]
PASTA = Path(os.environ.get("BATERIA_PASTA") or RAIZ / "docs" / "testes" / "bateria")


@dataclass
class Caso:
    nome: str
    desejos: list[tuple[str, dict]]  # (nome da pessoa, corpo do desejo)
    # só no demo (no real as lojas mudam): loja esperada na 1ª combinação e itens esperados (ids do demo)
    lojas: list[str] | None = None
    itens: set[str] | None = None
    sem_resultado: bool = False  # o certo é não achar (aviso honesto)
    ajuste: str | None = None  # frase do "Ajustar com o IBits" depois do Match


CASOS: list[Caso] = [
    Caso("pizza + coca", [("Ana", {"texto": "uma pizza e uma coca"})], ["loja-demo-pizza"], {"pz-refri"}),
    Caso("pizza + refri genérico", [("Ana", {"texto": "pizza e um refri, até 60"})], ["loja-demo-pizza"], {"pz-refri"}),
    Caso("combo", [("Ana", {"texto": "hambúrguer com batata e refri"})], ["loja-demo-burger"], {"bg-combo"}),
    Caso("japonês com teto", [("Ana", {"texto": "japonês até 40"})], ["loja-demo-japones"]),
    Caso("vegetariano barato", [("Ana", {"texto": "algo barato e vegetariano", "chips": ["vegetariano"]})]),
    Caso("farmácia", [("Ana", {"texto": "dipirona e protetor solar"})], ["loja-demo-farmacia"],
         {"fm-dipirona", "fm-protetor"}),
    Caso("pet shop", [("Ana", {"texto": "ração de cachorro e um petisco"})], ["loja-demo-pet"],
         {"pt-racao-cao", "pt-petisco"}),
    Caso("mercado", [("Ana", {"texto": "preciso fazer compras: arroz, feijão e detergente"})], ["loja-demo-mercado"],
         {"mc-arroz", "mc-feijao", "mc-detergente"}),
    Caso("fora do cardápio", [("Ana", {"texto": "lagosta com champanhe"})], sem_resultado=True),
    Caso("2 pizzas e 2 cocas", [("Ana", {"texto": "2 pizzas e 2 cocas"})], ["loja-demo-pizza"], {"pz-refri"}),
    Caso("x-salada com fritas", [("Ana", {"texto": "quero um x-salada com fritas"})], ["loja-demo-burger"]),
    Caso("açaí e água", [("Ana", {"texto": "um açaí e uma água"})], ["loja-demo-acai"], {"ac-agua"}),
    Caso("orçamento curto", [("Ana", {"texto": "pizza, até R$ 5"})], sem_resultado=True),
    # T16 / bug 40: prato feito é restaurante, não compra de mercado; "Onde pedir?" vai nos chips
    Caso("marmita", [("Ana", {"texto": "arroz, feijão, salada e guarnição"})], ["loja-demo-caseira"]),
    Caso("onde pedir: restaurante", [("Ana", {"texto": "arroz e feijão", "chips": ["onde:RESTAURANT"]})],
         ["loja-demo-caseira"]),
    Caso("roteiro do grupo", [
        ("Milan", {"texto": "japonês e um sorvete, até R$ 45", "orcamento_max": 45}),
        ("Zenon", {"texto": "hambúrguer e sorvete, até R$ 50", "orcamento_max": 50}),
        ("Antonio", {"texto": "algo barato e vegetariano, até R$ 25", "orcamento_max": 25, "chips": ["vegetariano"]}),
    ], ajuste="troca o sorvete do Milan por açaí"),
    Caso("grupo com combo e 2 itens", [
        ("Ana", {"texto": "pizza e um refri"}),
        ("Bia", {"texto": "japonês e um sorvete, até 45", "orcamento_max": 45}),
        ("Caio", {"texto": "hambúrguer com batata e refri"}),
    ]),
]


@dataclass
class Linha:
    caso: str
    status: int = 0
    ms: int = 0
    chamadas_mcp: int = 0
    itens_pedidos: int = 0
    itens_atendidos: int = 0
    lojas: int = 0
    pessoas_multi: int = 0  # pessoas com 2+ itens atendidos
    pessoas_multi_uma_loja: int = 0  # dessas, quantas receberam tudo de 1 loja só
    combos: int = 0
    economia: str = ""
    carrinhos: int = 0
    partes_ok: bool | None = None
    taxa_busca_x_carrinho: list[str] = field(default_factory=list)
    estimado_x_carrinho: tuple[float, float] | None = None  # (custo com taxa da busca, itens + entrega do carrinho)
    indisponivel: bool = False  # iFood respondeu 503 (fora do ar): fica fora das métricas
    ms_mcp: int = 0  # tempo somado das chamadas MCP do /rodar (o resto é IA + nosso código)
    por_tool: dict[str, int] = field(default_factory=dict)
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _centavos(v) -> int:
    return round(float(v or 0) * 100)


def _checar_resultado(caso: Caso, r: dict, linha: Linha, real: bool) -> None:
    combos = r.get("combinacoes") or []
    linha.avisos = r.get("avisos") or []
    if not combos:
        if not caso.sem_resultado:
            linha.falhas.append("sem combinação")
        return
    melhor = combos[0]
    escolhas, cobertos = melhor.get("escolhas") or {}, melhor.get("cobertos") or {}
    slots = [s for p in r.get("pessoas") or [] for s in p.get("slots") or []]
    linha.itens_pedidos = len(slots)
    linha.itens_atendidos = sum(1 for s in slots if s in escolhas or s in cobertos)
    linha.lojas = len(melhor.get("lojas") or [])
    linha.combos = sum(1 for c in escolhas.values() if c.get("cobre"))
    linha.economia = next((a for a in linha.avisos if a.startswith("Juntando os itens")), "")
    for p in r.get("pessoas") or []:
        dele = [escolhas[s] for s in p.get("slots") or [] if s in escolhas]
        atendidos = sum(1 for s in p.get("slots") or [] if s in escolhas or s in cobertos)
        if atendidos >= 2:
            linha.pessoas_multi += 1
            linha.pessoas_multi_uma_loja += len({c["loja_id"] for c in dele}) == 1
    # invariantes (valem no demo e no real)
    for comb in combos:
        if set(comb.get("escolhas") or {}) & set(comb.get("cobertos") or {}):
            linha.falhas.append("combo e item avulso no mesmo slot")
        cobertos_por = {s for c in (comb.get("escolhas") or {}).values() for s in c.get("cobre") or []}
        if cobertos_por != set(comb.get("cobertos") or {}):
            linha.falhas.append("cobertos não bate com o cobre dos combos")
    if linha.itens_atendidos < linha.itens_pedidos and not any(
            ("ficou de fora" in a or "Não achei" in a or "fechadas agora" in a or "mais de 4 itens" in a)
            for a in linha.avisos):
        linha.falhas.append("item de fora sem aviso")
    if any("aumentar o orçamento" in a for a in linha.avisos) and any("fechadas agora" in a for a in linha.avisos):
        linha.falhas.append("culpa o orçamento com loja fechada")
    # expectativas do demo
    if not real:
        if caso.lojas is not None and melhor.get("lojas") != caso.lojas:
            linha.falhas.append(f"lojas {melhor.get('lojas')} ≠ {caso.lojas}")
        ids = {c["item_id"] for c in escolhas.values()}
        if caso.itens is not None and not caso.itens <= ids:
            linha.falhas.append(f"itens {sorted(ids)} sem {sorted(caso.itens - ids)}")


def _rodar_caso(cliente, caso: Caso, real: bool) -> Linha:
    linha = Linha(caso.nome)
    sala = cliente.post("/api/salas", json={"organizador_nome": "Bateria", "chave_pix": "bateria@exemplo.com"}).json()
    base, org = f"/api/salas/{sala['sala_id']}", {"X-Organizador": sala["token_organizador"]}
    for nome, desejo in caso.desejos:
        pid = cliente.post(f"{base}/participantes", json={"nome": nome}).json()["participante_id"]
        cliente.put(f"{base}/participantes/{pid}/desejo", json=desejo)
    inicio = time.perf_counter()
    resp = cliente.post(f"{base}/rodar", headers=org)
    linha.ms = int((time.perf_counter() - inicio) * 1000)
    linha.status = resp.status_code
    corpo = resp.json()
    if resp.status_code == 503:  # iFood fora do ar: o app avisou certo; não é falha nossa, o caso fica de fora
        linha.indisponivel = True
        linha.avisos = [str(corpo.get("detail", ""))]
        if "{" in linha.avisos[0] or "INTERNAL" in linha.avisos[0]:
            linha.falhas.append("mensagem do 503 mostra o erro cru do iFood")
        return linha
    if resp.status_code != 200:
        linha.avisos = [str(corpo.get("detail", ""))]
        if not caso.sem_resultado:
            linha.falhas.append(f"/rodar {resp.status_code}: {str(corpo.get('detail', ''))[:120]}")
        elif "aumentar o orçamento" in linha.avisos[0] and "orçamento" not in caso.nome:
            linha.falhas.append("pedido fora do cardápio sugere aumentar o orçamento")
        return linha
    rastro = corpo.get("rastro") or []
    linha.chamadas_mcp = len(rastro)
    linha.ms_mcp = sum(int(c.get("ms") or 0) for c in rastro)
    for c in rastro:
        linha.por_tool[c["tool"]] = linha.por_tool.get(c["tool"], 0) + 1
    _checar_resultado(caso, corpo, linha, real)
    if caso.sem_resultado:
        linha.falhas.append("devia avisar que não achou, mas montou combinação")
    if caso.ajuste:
        aj = cliente.post(f"{base}/ajustar", json={"texto": caso.ajuste}, headers=org)
        if aj.status_code != 200:
            linha.falhas.append(f"/ajustar {aj.status_code}: {str(aj.json().get('detail', ''))[:120]}")
    esc = cliente.post(f"{base}/escolher", json={"combinacao": 0, "modo_pagamento": "separado"}, headers=org)
    if esc.status_code != 200:
        linha.falhas.append(f"/escolher {esc.status_code}: {str(esc.json().get('detail', ''))[:120]}")
        return linha
    estado = cliente.get(base).json()
    carrinhos, partes = estado.get("carrinhos") or [], estado.get("partes") or []
    linha.carrinhos = len(carrinhos)
    soma_partes = sum(_centavos(p["total"]) for p in partes)
    soma_carrinhos = sum(_centavos(c["total"]) for c in carrinhos)
    linha.partes_ok = soma_partes == soma_carrinhos
    if not linha.partes_ok:
        linha.falhas.append(f"partes {soma_partes / 100:.2f} ≠ carrinhos {soma_carrinhos / 100:.2f}")
    # estimativa da escolha (itens + taxa da busca) × carrinho real (itens + entrega), sem serviço nem desconto
    escolhida = estado.get("combinacao_escolhida") or {}
    estimado = (escolhida.get("componentes") or {}).get("custo_total")
    if estimado is not None and escolhida.get("taxa_conhecida"):
        no_carrinho = sum(float(k.get("subtotal") or 0) + float(k.get("taxa") or 0) for k in carrinhos)
        linha.estimado_x_carrinho = (float(estimado), round(no_carrinho, 2))
    for k in carrinhos:
        linha.taxa_busca_x_carrinho.append(f"{k.get('loja_nome')}: carrinho R$ {float(k.get('taxa') or 0):.2f}"
                                           + (f" + serviço R$ {float(k['servico']):.2f}" if k.get("servico") else ""))
    return linha


def _commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(RAIZ), "log", "-1", "--format=%h"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
    except Exception:
        return "?"


def _relatorio(linhas: list[Linha], modo: str, provedor: str, agora: datetime) -> str:
    pedidos = sum(l.itens_pedidos for l in linhas)
    atendidos = sum(l.itens_atendidos for l in linhas)
    multi = sum(l.pessoas_multi for l in linhas)
    multi_uma = sum(l.pessoas_multi_uma_loja for l in linhas)
    ok_partes = [l for l in linhas if l.partes_ok is not None]
    tempos = sorted(l.ms for l in linhas if l.status == 200)
    fora_do_ar = [l.caso for l in linhas if l.indisponivel]
    medidos = [l for l in linhas if l.status == 200]
    falhas = [(l.caso, f) for l in linhas for f in l.falhas]
    def pct(a, b):
        return f"{a}/{b} ({round(100 * a / b)}%)" if b else "—"
    out = [
        f"# Bateria automática — {modo} — {agora:%d/%m %Hh%M}",
        "",
        f"Commit `{_commit()}` · IA: `{provedor}` · {len(linhas)} casos · gerado por `python -m app.match.bateria"
        f"{' --real' if modo == 'real' else ''}` (nenhum pedido enviado).",
        "",
        f"**Invariantes:** {'✅ todos ok' if not falhas else f'❌ {len(falhas)} falha(s)'}",
        "",
        "## Métricas medidas",
        f"- Itens pedidos que entraram no pedido: {pct(atendidos, pedidos)}",
        f"- Pessoas com 2+ itens que receberam tudo de 1 loja só: {pct(multi_uma, multi)}",
        f"- Combos usados (1 item no lugar de vários): {sum(l.combos for l in linhas)}",
        f"- Partes da vaquinha = total dos carrinhos (ao centavo): {pct(sum(l.partes_ok for l in ok_partes), len(ok_partes))}",
        f"- Tempo do Match (/rodar): mediana {tempos[len(tempos) // 2] / 1000:.1f} s, máximo {tempos[-1] / 1000:.1f} s"
        if tempos else "- Tempo do Match: —",
        f"- Casos com o iFood fora do ar (503, mensagem honesta; fora das métricas): {len(fora_do_ar)}"
        + (f" — {', '.join(fora_do_ar)}" if fora_do_ar else ""),
        f"- Chamadas MCP por Match (média): {round(sum(l.chamadas_mcp for l in medidos) / max(1, len(medidos)), 1)}",
        "- Onde vai o tempo do Match: " + ("; ".join(
            f"{l.caso} {l.ms / 1000:.1f} s = MCP {l.ms_mcp / 1000:.1f} s ({l.chamadas_mcp} chamadas: "
            + ", ".join(f"{t} {n}" for t, n in sorted(l.por_tool.items(), key=lambda x: -x[1])) + ") + IA/código "
            f"{max(0, l.ms - l.ms_mcp) / 1000:.1f} s" for l in medidos if l.ms >= 3000) or "todos abaixo de 3 s"),
        "- Custo estimado na escolha (itens + taxa da busca) × carrinho (itens + entrega): "
        + (", ".join(f"{l.caso} R$ {a:.2f} × R$ {b:.2f}" for l in linhas if l.estimado_x_carrinho
                     for a, b in [l.estimado_x_carrinho] if abs(a - b) >= 0.01) or "iguais em todos os casos"),
        "",
        "## Casos",
        "| Caso | /rodar | Tempo | Itens | Lojas | Combos | Carrinhos | Partes = total | Falhas |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for l in linhas:
        out.append(f"| {l.caso} | {l.status}{' ⚠️ iFood fora' if l.indisponivel else ''} | {l.ms / 1000:.1f} s | {l.itens_atendidos}/{l.itens_pedidos} | {l.lojas} | "
                   f"{l.combos} | {l.carrinhos} | {'—' if l.partes_ok is None else ('✅' if l.partes_ok else '❌')} | "
                   f"{'; '.join(l.falhas) or '✅'} |")
    out += ["", "## Avisos e taxas por caso"]
    for l in linhas:
        out.append(f"- **{l.caso}:** " + (" · ".join(l.avisos)[:400] or "—")
                   + (f" — taxas: {'; '.join(l.taxa_busca_x_carrinho)}" if l.taxa_busca_x_carrinho else ""))
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    opcoes = set(argv if argv is not None else sys.argv[1:])
    real = "--real" in opcoes
    os.environ["IFOOD_MCP_MODO"] = "real" if real else "demo"
    os.environ["IFOOD_MCP_PERMITIR_ENVIO"] = "false"  # nunca envia pedido
    os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "bateria.db")  # não suja a base do app
    if "--sem-ia" in opcoes:
        os.environ["LLM_PROVIDER"] = "mock"

    import logging

    from fastapi.testclient import TestClient


    from ..config import carregar
    from ..ifood_mcp import resetar_demo
    from ..main import app

    provedor = carregar().llm_provedor
    linhas: list[Linha] = []
    with TestClient(app) as cliente:
        for nome in ("httpx", "httpx2"):  # sem uma linha por requisição
            logging.getLogger(nome).setLevel(logging.WARNING)
        for caso in CASOS:
            if not real:
                resetar_demo()
            try:
                linhas.append(_rodar_caso(cliente, caso, real))
            except Exception as e:  # um caso que quebra vira falha, a bateria segue
                linhas.append(Linha(caso.nome, falhas=[f"exceção: {type(e).__name__}: {e}"[:200]]))
            print(f"{caso.nome}: {'ok' if not linhas[-1].falhas else '; '.join(linhas[-1].falhas)}", flush=True)
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    modo = "real" if real else "demo"
    PASTA.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA / f"{modo}-{agora:%d%H%M}.md"
    arquivo.write_text(_relatorio(linhas, modo, provedor, agora), encoding="utf-8")
    print(f"Relatório: {arquivo}")
    return 1 if any(l.falhas for l in linhas) else 0


if __name__ == "__main__":
    sys.exit(main())
