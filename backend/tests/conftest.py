import pytest

from app import db


@pytest.fixture(autouse=True)
def ambiente_isolado(tmp_path, monkeypatch):
    """Cada teste usa uma base nova, agente mock e iFood mock, sem depender do .env."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("IFOOD_MODE", "mock")
    db.inicializar()
