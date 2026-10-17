"""Tipos do Match (contrato C3 da etapa 02). `para_dict` transforma tudo em JSON simples."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

PERFIS = ("barato", "rapido", "equilibrado", "qualidade")


@dataclass
class Desejo:
    """O que a pessoa escreveu na sala (frase livre + orçamento + chips)."""

    participante_id: str
    nome: str
    texto: str
    orcamento_max: float | None = None
    chips: list[str] = field(default_factory=list)


@dataclass
class Intencao:
    """Desejo interpretado: o que buscar, o que é regra e o que é vontade."""

    participante_id: str
    consultas: list[str] = field(default_factory=list)
    verticais: list[str] = field(default_factory=list)
    restricoes: list[str] = field(default_factory=list)
    vontades: list[str] = field(default_factory=list)
    orcamento_max: float | None = None
    perfil: str = "equilibrado"  # barato | rapido | equilibrado | qualidade


@dataclass
class Candidato:
    """Um item de uma loja que pode atender uma pessoa. Preço/ETA vêm só das tools MCP."""

    participante_id: str
    loja_id: str
    loja_nome: str
    item_id: str
    item_nome: str
    preco: float
    eta_min: int | None
    vertical: str
    perecivel: bool
    nota: float = 0.0  # aderência ao desejo, 0–1
    motivo: str = ""
    viola: list[str] = field(default_factory=list)  # restrições duras violadas (não vazio → descartado)


@dataclass
class Pesos:
    """Pesos da função de pontuação (§4 da etapa 01b)."""

    alfa_justica: float = 0.5
    beta_custo: float = 0.3
    gama_atraso: float = 0.2
    delta_lojas: float = 0.15
    epsilon_perecivel: float = 0.3


@dataclass
class Combinacao:
    """Uma escolha de item por pessoa, com a pontuação e cada termo dela."""

    escolhas: dict[str, Candidato]
    lojas: list[str]
    score: float
    componentes: dict[str, float]
    taxa_conhecida: bool
    explicacao: str = ""


@dataclass
class Parte:
    """Quanto cada pessoa paga no modo "separado" (valores em reais, exatos ao centavo)."""

    participante_id: str
    nome: str
    itens: float
    taxa: float
    desconto: float
    total: float


def para_dict(obj: Any) -> Any:
    """Serializa recursivamente dataclasses, listas, tuplas e dicts em tipos JSON."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return para_dict(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): para_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [para_dict(v) for v in obj]
    return obj
