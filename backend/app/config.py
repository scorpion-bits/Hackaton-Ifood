"""Configuração lida do .env (na raiz do repositório). Lida a cada chamada para facilitar testes."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"

load_dotenv(RAIZ / ".env")

# Provedores com API compatível com OpenAI: só muda a URL base.
PRESETS_OPENAI = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "env_chave": "GROQ_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "env_chave": "GEMINI_API_KEY"},
    "ollama": {"base_url": "http://localhost:11434/v1", "env_chave": None},
    "openai": {"base_url": None, "env_chave": "OPENAI_API_KEY"},
}
PROVEDORES = ["mock", "anthropic", *PRESETS_OPENAI]


@dataclass(frozen=True)
class Config:
    llm_provedor: str
    llm_modelo: str
    llm_chave: str = field(repr=False)
    llm_base_url: str | None
    llm_esforco: str
    ifood_modo: str
    ifood_base_url: str
    ifood_client_id: str
    ifood_client_secret: str = field(repr=False)
    db_path: Path
    # MCP do consumidor do iFood (Match): "demo" = servidor de demonstração em processo; "real" = MCP oficial com OAuth.
    ifood_mcp_modo: str = "demo"
    ifood_mcp_client_id: str = ""
    ifood_mcp_client_secret: str = field(default="", repr=False)
    # OAuth do MCP real: redirect cadastrada no Portal e scopes (vazio = não envia scope).
    ifood_mcp_redirect: str = "http://localhost:8000/oauth/callback"
    ifood_mcp_scope: str = ""
    # Leilão de agentes por loja no Match (MATCH_LEILAO=off volta ao motor sem leilão).
    match_leilao: bool = True


def carregar() -> Config:
    provedor = os.getenv("LLM_PROVIDER", "mock").strip().lower() or "mock"
    if provedor not in PROVEDORES:
        raise ValueError(f"LLM_PROVIDER inválido: {provedor!r}. Use um de: {', '.join(PROVEDORES)}")

    preset = PRESETS_OPENAI.get(provedor, {})
    chave = os.getenv("LLM_API_KEY", "")
    if not chave and preset.get("env_chave"):
        chave = os.getenv(preset["env_chave"], "")
    if not chave and provedor == "anthropic":
        chave = os.getenv("ANTHROPIC_API_KEY", "")
    if provedor == "ollama":
        chave = chave or "ollama"  # o Ollama ignora a chave, mas o SDK exige uma

    modelo = os.getenv("LLM_MODEL", "").strip()
    if provedor == "anthropic" and not modelo:
        modelo = "claude-opus-5-5"

    db = os.getenv("DB_PATH", "").strip()
    return Config(
        llm_provedor=provedor,
        llm_modelo=modelo,
        llm_chave=chave,
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip() or preset.get("base_url"),
        llm_esforco=os.getenv("LLM_EFFORT", "low").strip() or "low",
        ifood_modo=os.getenv("IFOOD_MODE", "mock").strip().lower() or "mock",
        ifood_base_url=os.getenv("IFOOD_BASE_URL", "https://merchant-api.ifood.com.br").rstrip("/"),
        ifood_client_id=os.getenv("IFOOD_CLIENT_ID", ""),
        ifood_client_secret=os.getenv("IFOOD_CLIENT_SECRET", ""),
        db_path=Path(db) if db else BACKEND / "dados" / "app.db",
        ifood_mcp_modo=os.getenv("IFOOD_MCP_MODO", "demo").strip().lower() or "demo",
        ifood_mcp_client_id=os.getenv("IFOOD_MCP_CLIENT_ID", ""),
        ifood_mcp_client_secret=os.getenv("IFOOD_MCP_CLIENT_SECRET", ""),
        ifood_mcp_redirect=os.getenv("IFOOD_MCP_REDIRECT", "").strip() or "http://localhost:8000/oauth/callback",
        ifood_mcp_scope=" ".join(os.getenv("IFOOD_MCP_SCOPE", "").replace(",", " ").split()),
        match_leilao=os.getenv("MATCH_LEILAO", "on").strip().lower() not in ("off", "0", "false", "nao", "não"),
    )
