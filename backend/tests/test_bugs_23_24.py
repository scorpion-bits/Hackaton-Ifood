"""Bugs 23 (listAddresses fora do ar + mock) e 24 (aviso "mais próxima" bate com a combinação)."""

import pytest

from app.config import carregar
from app.ifood_mcp import abrir_cliente, resetar_demo
from app.ifood_mcp.cliente import ErroMCP
from app.match import interprete
from app.match import motor as motor_mod
from app.match.modelos import Desejo
from app.match.motor import rodar_match

MOCK = "-22.0025,-47.8986"


@pytest.fixture(autouse=True)
def demo_limpo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_MODO", "demo")
    resetar_demo()
    yield
    resetar_demo()


class _ClienteFalha:
    """Demo com o `listAddresses` levantando ErroMCP."""

    def __init__(self, cliente, erro):
        self._cli, self._erro, self.modo = cliente, erro, "demo"

    async def chamar(self, tool, **args):
        if tool == "listAddresses":
            raise ErroMCP(self._erro)
        return await self._cli.chamar(tool, **args)

    def rastro_como_dicts(self):
        return self._cli.rastro_como_dicts()


async def _rodar(desejos, erro=None):
    cfg = carregar()
    async with abrir_cliente(cfg) as cli:
        return await rodar_match(cfg, _ClienteFalha(cli, erro) if erro else cli, desejos)


def _achatar(exc):
    if isinstance(exc, BaseExceptionGroup):
        return [m for x in exc.exceptions for m in _achatar(x)]
    return [str(exc)]


DESEJOS = [Desejo("milan", "Milan", "japonês, até R$ 45")]


async def test_listaddresses_falha_com_mock_roda_com_aviso(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", MOCK)
    r = await _rodar(DESEJOS, "INTERNAL: tente de novo")
    assert "problema" not in r and r["combinacoes"]
    assert r["endereco"]["id"] == motor_mod.ID_ENDERECO_MOCK
    # bug 33: sem o erro cru do iFood na tela (ele fica no rastro)
    assert ("Não consegui ler os endereços no iFood (o iFood está instável agora); usando o endereço de teste."
            in r["avisos"])
    assert motor_mod.MSG_ENDERECO_MOCK not in r["avisos"]  # uma mensagem só


async def test_listaddresses_falha_sem_mock_comporta_como_antes(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", "")
    r = await _rodar(DESEJOS, "INTERNAL")
    assert r["problema"] == "endereco" and r["combinacoes"] == []
    assert r["avisos"] == ["Não consegui ler os endereços no iFood: o iFood está instável agora"]


async def test_listaddresses_401_continua_subindo(monkeypatch):
    monkeypatch.setenv("IFOOD_MCP_ENDERECO_MOCK", MOCK)
    with pytest.raises(BaseException) as e:  # o abrir_cliente embrulha em ExceptionGroup
        await _rodar(DESEJOS, "login recusado (401)")
    assert "(401)" in "".join(_achatar(e.value))


async def test_aviso_da_opcao_aproximada_cita_o_item_da_combinacao(monkeypatch):
    monkeypatch.setattr(interprete, "_consulta_livre", lambda *a, **k: "")
    original = motor_mod.otimizar

    def otimizar_trocando(candidatos, *a, **k):
        # simula o otimizador escolhendo, para a Ana, outro item que não o "mais próximo" do aviso
        combos = original(candidatos, *a, **k)
        for c in combos:
            outro = next((x for x in candidatos["ana"] if x.item_id != c.escolhas["ana"].item_id), None)
            if outro:
                c.escolhas["ana"] = outro
        return combos

    monkeypatch.setattr(motor_mod, "otimizar", otimizar_trocando)
    r = await _rodar([Desejo("milan", "Milan", "japonês, até R$ 45"),
                      Desejo("ana", "Ana", "feijoada completa, até R$ 60")])
    esc = r["combinacoes"][0]["escolhas"]["ana"]
    aviso = next(a for a in r["avisos"] if a.startswith("Não achei feijoada completa para Ana"))
    assert f"a opção mais próxima é {esc['item_nome']} ({esc['loja_nome']})." in aviso
    assert sum(a.startswith("Não achei feijoada") for a in r["avisos"]) == 1
