"""Provedores de LLM plugáveis pelo .env (LLM_PROVIDER).

Cada provedor implementa uma "conversa" com dois métodos:
  passo()                 -> Passo(texto, chamadas de ferramenta)
  adicionar_resultados()  -> devolve ao modelo o resultado de cada chamada
"""

import json
import re
import unicodedata
from dataclasses import dataclass, field

from ..config import Config


def brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class Chamada:
    id: str
    nome: str
    args: dict


@dataclass
class Resultado:
    chamada_id: str
    texto: str
    erro: bool = False


@dataclass
class Passo:
    texto: str
    chamadas: list[Chamada] = field(default_factory=list)


@dataclass
class Ferramenta:
    nome: str
    descricao: str
    schema: dict


def criar_conversa(cfg: Config, sistema: str, historico: list[dict], mensagem: str,
                   ferramentas: list[Ferramenta], contexto: dict):
    if cfg.llm_provedor == "mock":
        return ConversaMock(mensagem, contexto)
    if not cfg.llm_modelo:
        raise RuntimeError(
            f"LLM_MODEL vazio para o provedor '{cfg.llm_provedor}'. "
            "Rode `python -m app.agente.listar_modelos` (em backend/) e escolha um modelo com tool calling."
        )
    if cfg.llm_provedor == "anthropic":
        return ConversaAnthropic(cfg, sistema, historico, mensagem, ferramentas)
    return ConversaOpenAI(cfg, sistema, historico, mensagem, ferramentas)


# ---------------------------------------------------------------------------
# OpenAI e compatíveis (Groq, Gemini, Ollama, OpenAI)
# ---------------------------------------------------------------------------
class ConversaOpenAI:
    def __init__(self, cfg: Config, sistema, historico, mensagem, ferramentas, http_client=None):
        from openai import AsyncOpenAI

        self.cfg = cfg
        self.cliente = AsyncOpenAI(api_key=cfg.llm_chave or "sem-chave", base_url=cfg.llm_base_url,
                                   http_client=http_client)
        self.ferramentas = [
            {"type": "function", "function": {"name": f.nome, "description": f.descricao, "parameters": f.schema}}
            for f in ferramentas
        ]
        self.mensagens = [{"role": "system", "content": sistema}]
        self.mensagens += [{"role": "user" if h["papel"] == "usuario" else "assistant", "content": h["texto"]}
                           for h in historico]
        self.mensagens.append({"role": "user", "content": mensagem})

    async def passo(self) -> Passo:
        resp = await self.cliente.chat.completions.create(
            model=self.cfg.llm_modelo, messages=self.mensagens, tools=self.ferramentas or None,
        )
        msg = resp.choices[0].message
        chamadas = [
            Chamada(tc.id, tc.function.name, json.loads(tc.function.arguments or "{}"))
            for tc in (msg.tool_calls or [])
        ]
        registro = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            registro["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        self.mensagens.append(registro)
        return Passo(msg.content or "", chamadas)

    def adicionar_resultados(self, resultados: list[Resultado]) -> None:
        for r in resultados:
            self.mensagens.append({"role": "tool", "tool_call_id": r.chamada_id, "content": r.texto})


# ---------------------------------------------------------------------------
# Anthropic (Claude) — SDK oficial
# ---------------------------------------------------------------------------
# Modelos que aceitam o fallback automático do servidor em caso de recusa ("default").
_COM_FALLBACK = ("claude-opus-5", "claude-fable-5", "claude-sonnet-5-5")


class ConversaAnthropic:
    def __init__(self, cfg: Config, sistema, historico, mensagem, ferramentas, http_client=None):
        import anthropic

        self.cfg = cfg
        self.cliente = anthropic.AsyncAnthropic(api_key=cfg.llm_chave or None, http_client=http_client)
        self.sistema = sistema
        self.ferramentas = [{"name": f.nome, "description": f.descricao, "input_schema": f.schema}
                            for f in ferramentas]
        self.mensagens = [{"role": "user" if h["papel"] == "usuario" else "assistant", "content": h["texto"]}
                          for h in historico]
        self.mensagens.append({"role": "user", "content": mensagem})

    async def passo(self) -> Passo:
        extras = {}
        if self.cfg.llm_modelo.startswith(_COM_FALLBACK):
            extras = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        resp = await self.cliente.beta.messages.create(
            model=self.cfg.llm_modelo, max_tokens=16000, system=self.sistema, tools=self.ferramentas,
            messages=self.mensagens, output_config={"effort": self.cfg.llm_esforco}, **extras,
        )
        # Devolve o conteúdo inteiro (inclui blocos de thinking) para manter o histórico válido.
        self.mensagens.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "refusal":
            return Passo("O modelo recusou este pedido. Reformule ou tente outra abordagem.")
        texto = "\n".join(b.text for b in resp.content if b.type == "text")
        chamadas = [Chamada(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        return Passo(texto, chamadas)

    def adicionar_resultados(self, resultados: list[Resultado]) -> None:
        self.mensagens.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": r.chamada_id, "content": r.texto, "is_error": r.erro}
            for r in resultados
        ]})


# ---------------------------------------------------------------------------
# Mock offline: roteiro por palavras-chave. Funciona sem internet e sem chave.
# ---------------------------------------------------------------------------
_COMIDAS = ["burger", "pizza", "sushi", "combinado", "lasanha", "espaguete", "massa", "batata",
            "refrigerante", "yakisoba", "lanche", "cha"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _valor(texto: str) -> float | None:
    m = re.search(r"(?:r\$|ate|até)\s*(\d+(?:[.,]\d+)?)", texto)
    return float(m.group(1).replace(",", ".")) if m else None


class ConversaMock:
    """Simula o modelo: decide 1–2 chamadas de ferramenta e resume os resultados."""

    def __init__(self, mensagem: str, contexto: dict):
        self.msg = _normalizar(mensagem)
        self.lado = contexto.get("lado", "comprador")
        self.loja_id = contexto.get("loja_id", "loja-demo-1")
        self.resultados: list[tuple[Chamada, Resultado]] = []
        self.pendentes: list[Chamada] = []
        self.termo = ""
        self.n = 0

    async def passo(self) -> Passo:
        self.n += 1
        chamada = self._decidir()
        if chamada:
            self.pendentes = [chamada]
            return Passo("", [chamada])
        return Passo(self._resumir())

    def adicionar_resultados(self, resultados: list[Resultado]) -> None:
        for ch, r in zip(self.pendentes, resultados):
            self.resultados.append((ch, r))
        self.pendentes = []

    # --- roteiro ---
    def _decidir(self) -> Chamada | None:
        if self.resultados and self.resultados[-1][1].erro:
            return None
        ultimo = self._dados(-1)
        if self.lado == "vendedor":
            if not self.resultados:
                return Chamada("m1", "vendedor_listar_cardapio", {"loja_id": self.loja_id})
            if len(self.resultados) == 1 and ("promo" in self.msg or "desconto" in self.msg):
                ativos = [i for i in ultimo["itens"] if i["disponivel"]]
                alvo = max(ativos, key=lambda i: i["estoque"] or 0)
                pct = float(m.group(1)) if (m := re.search(r"(\d+)\s*%", self.msg)) else 10.0
                return Chamada("m2", "vendedor_propor_promocao", {
                    "loja_id": self.loja_id, "item_id": alvo["id"], "desconto_pct": pct,
                    "motivo": f"'{alvo['nome']}' tem o maior estoque ({alvo['estoque']} un.), girar mais rápido."})
            if len(self.resultados) == 1 and any(p in self.msg for p in ("pausa", "pausar", "acabou", "esgot")):
                alvo = next((i for i in ultimo["itens"] if _normalizar(i["nome"]).split()[0] in self.msg), None)
                alvo = alvo or min(ultimo["itens"], key=lambda i: i["estoque"] or 0)
                return Chamada("m2", "vendedor_propor_disponibilidade", {
                    "loja_id": self.loja_id, "item_id": alvo["id"], "disponivel": False,
                    "motivo": f"Pedido do lojista; '{alvo['nome']}' está com {alvo['estoque']} un. em estoque."})
            return None

        # comprador
        if not self.resultados:
            if "loja" in self.msg or "restaurante" in self.msg:
                return Chamada("m1", "comprador_listar_lojas", {})
            palavras = self.msg.split()
            self.termo = next((c for c in _COMIDAS if c in self.msg), palavras[-1] if palavras else "")
            return Chamada("m1", "comprador_buscar_itens", {"termo": self.termo, "preco_max": _valor(self.msg)})
        quer_pedir = any(p in self.msg for p in ("pedir", "pedido", "comprar", "quero"))
        if len(self.resultados) == 1 and quer_pedir and ultimo.get("itens"):
            disponiveis = [i for i in ultimo["itens"] if i["disponivel"]]
            alvo = next((i for i in disponiveis if self.termo in _normalizar(i["nome"])), None)
            alvo = alvo or (disponiveis[0] if disponiveis else None)
            if alvo:
                args = {"loja_id": alvo["loja_id"], "itens": [{"item_id": alvo["id"], "quantidade": 1}],
                        "motivo": f"Opção disponível mais barata encontrada: {alvo['nome']} ({alvo['loja_nome']})."}
                if (orc := _valor(self.msg)) is not None:
                    args["orcamento_max"] = orc + 15  # margem para taxa de entrega
                return Chamada("m2", "comprador_propor_pedido", args)
        return None

    def _dados(self, i: int) -> dict:
        if not self.resultados:
            return {}
        try:
            return json.loads(self.resultados[i][1].texto)
        except (json.JSONDecodeError, IndexError):
            return {}

    def _resumir(self) -> str:
        if not self.resultados:
            return ("Modo offline (roteiro de demonstração). Tente: 'quero um burger até R$ 40', "
                    "'quais lojas tem?', 'mostre o cardápio', 'crie uma promoção de 15%'.")
        chamada, res = self.resultados[-1]
        if res.erro:
            return f"Não consegui concluir: {res.texto}"
        dados = self._dados(-1)
        if dados.get("status") == "pendente":
            return (f"Preparei esta ação: **{dados['resumo']}**.\nPor quê: {dados['motivo']}\n"
                    "Nada foi executado ainda — confirme ou recuse no cartão abaixo.")
        if "lojas" in dados:
            linhas = [f"- {l['nome']} ({l['categoria']}) · nota {l['nota']} · {l['tempo_entrega_min']} min" for l in dados["lojas"]]
            return "Lojas encontradas:\n" + "\n".join(linhas)
        itens = dados.get("itens", [])
        if not itens:
            return "Não encontrei itens com esse critério."
        linhas = [f"- {i['nome']} · {brl(i['preco'])}" + (f" · {i['loja_nome']}" if i.get("loja_nome") else "")
                  + ("" if i["disponivel"] else " (pausado)") for i in itens[:6]]
        return "Encontrei:\n" + "\n".join(linhas)
