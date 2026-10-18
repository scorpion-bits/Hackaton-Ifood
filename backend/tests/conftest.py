import pytest

from app import db
from app.ifood_mcp import oauth


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    """Cada teste usa uma base nova, agente mock e iFood mock, sem depender do .env."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("IFOOD_MODE", "mock")
    # nunca usar (nem imprimir num traceback) credenciais reais do .env da equipe
    for var in ("IFOOD_MCP_CLIENT_ID", "IFOOD_MCP_CLIENT_SECRET", "IFOOD_CLIENT_SECRET", "IFOOD_MCP_SCOPE",
                "IFOOD_MCP_ENDERECO_MOCK"):
        monkeypatch.setenv(var, "")
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    monkeypatch.setattr(oauth, "ARQUIVO_TOKENS", tmp_path / ".tokens_ifood.json")  # nunca o login real
    db.inicializar()
