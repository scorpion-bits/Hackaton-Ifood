"""GET /api/saude: campos básicos e ip_local (URL da máquina na rede local)."""

from fastapi.testclient import TestClient

from app import main
from app.main import app


def _saude(base="http://testserver"):
    return TestClient(app, base_url=base).get("/api/saude").json()


def test_saude_basico():
    d = _saude()
    assert d["ok"] is True and d["demonstracao"] is True and "ip_local" in d
    assert d["envio_real_permitido"] is True  # no demo o pedido é simulado


def test_envio_real_permitido_segue_a_trava_no_modo_real(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "real")
    monkeypatch.delenv("IFOOD_MCP_PERMITIR_ENVIO", raising=False)
    assert _saude()["envio_real_permitido"] is False
    monkeypatch.setenv("IFOOD_MCP_PERMITIR_ENVIO", "true")
    assert _saude()["envio_real_permitido"] is True


def test_ip_local_usa_ip_da_rede_e_porta_do_request(monkeypatch):
    monkeypatch.setattr(main, "_ip_da_interface", lambda: "192.168.0.42")
    assert _saude("http://testserver:8123")["ip_local"] == "http://192.168.0.42:8123"
    assert _saude()["ip_local"] == "http://192.168.0.42:8000"


def test_ip_local_nulo_se_loopback_ou_sem_rede(monkeypatch):
    monkeypatch.setattr(main, "_ip_da_interface", lambda: "127.0.0.1")
    assert _saude()["ip_local"] is None
    monkeypatch.setattr(main, "_ip_da_interface", lambda: None)
    assert _saude()["ip_local"] is None
