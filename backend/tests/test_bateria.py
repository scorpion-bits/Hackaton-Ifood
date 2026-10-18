"""A bateria automática (`python -m app.match.bateria`) roda inteira no modo demonstração e não acha falha."""

import importlib
import re


def test_bateria_demo_passa_e_grava_relatorio(tmp_path, monkeypatch):
    monkeypatch.setenv("BATERIA_PASTA", str(tmp_path))
    from app.match import bateria
    bateria = importlib.reload(bateria)  # relê BATERIA_PASTA
    assert bateria.main(["--sem-ia"]) == 0
    relatorio = next(tmp_path.glob("demo-*.md")).read_text(encoding="utf-8")
    assert "**Invariantes:** ✅ todos ok" in relatorio
    # todo caso com carrinho fecha ao centavo (13 casos até o T16; 15 com marmita e "Onde pedir?")
    m = re.search(r"Partes da vaquinha = total dos carrinhos \(ao centavo\): (\d+)/(\d+) \(100%\)", relatorio)
    assert m and m.group(1) == m.group(2) and int(m.group(1)) >= 15
