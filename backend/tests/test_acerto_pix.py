"""Acerto da vaquinha (centavos exatos), prazo de pagamento e Pix copia e cola."""

import pytest

from app.match.acerto import calcular_partes, centavos, prazo_pagamento_min
from app.match.modelos import Candidato
from app.match.pix import crc16_ccitt_false, gerar_pix_copia_e_cola, ler_campos, normalizar_chave_pix


def cand(pid, loja, item, preco):
    return Candidato(
        participante_id=pid, loja_id=loja, loja_nome=f"Loja {loja}", item_id=item, item_nome=item,
        preco=preco, eta_min=30, vertical="RESTAURANT", perecivel=False,
    )


def soma_centavos(partes):
    return sum(centavos(p.total) for p in partes)


def test_exemplo_secao_13_thales_e_milan():
    # Loja A: hambúrguer R$ 10 (Thales) + R$ 10 (Milan); loja B: sorvete R$ 5 (Milan).
    escolhas = {
        "t": cand("t", "A", "hamburguer", 10.00),
        "m": [cand("m", "A", "hamburguer", 10.00), cand("m", "B", "sorvete", 5.00)],
    }
    partes = calcular_partes(escolhas, {"t": "Thales", "m": "Milan"}, {"A": 7.00, "B": 5.99}, {})
    por_id = {p.participante_id: p for p in partes}
    assert por_id["t"].nome == "Thales"
    assert (por_id["t"].itens, por_id["t"].taxa, por_id["t"].desconto, por_id["t"].total) == (10.0, 3.5, 0.0, 13.5)
    assert (por_id["m"].itens, por_id["m"].taxa, por_id["m"].total) == (15.0, 9.49, 24.49)
    assert soma_centavos(partes) == 3799  # 25,00 de itens + 12,99 de taxas


def test_taxa_10_entre_3_soma_exato():
    escolhas = {p: cand(p, "A", f"i{p}", 20.00) for p in ("a", "b", "c")}
    partes = calcular_partes(escolhas, {}, {"A": 10.00}, {})
    assert sorted(p.taxa for p in partes) == [3.33, 3.33, 3.34]
    assert soma_centavos(partes) == 7000
    assert partes[0].nome == "a"  # sem nome → usa o id


def test_desconto_proporcional_e_soma_exata():
    escolhas = {
        "a": cand("a", "A", "x", 33.33),
        "b": cand("b", "A", "y", 33.33),
        "c": cand("c", "A", "z", 16.67),
        "d": cand("d", "B", "w", 9.90),
    }
    partes = calcular_partes(escolhas, {}, {"A": 8.99, "B": 4.49}, {"A": 10.00})
    por_id = {p.participante_id: p for p in partes}
    # desconto de A proporcional: 33,33 / 83,33 de 10,00 ≈ 4,00 cada; 16,67 → 2,00
    assert sum(centavos(p.desconto) for p in partes) == 1000
    assert por_id["d"].desconto == 0.0
    assert por_id["a"].desconto >= por_id["c"].desconto * 1.9
    total = centavos(33.33 * 2 + 16.67 + 9.90) + centavos(8.99) + centavos(4.49) - 1000
    assert soma_centavos(partes) == total
    for p in partes:
        assert centavos(p.itens) + centavos(p.taxa) - centavos(p.desconto) == centavos(p.total)


def test_valores_invalidos():
    with pytest.raises(ValueError):
        calcular_partes({"a": cand("a", "A", "x", 10)}, {}, {"A": -1}, {})
    with pytest.raises(ValueError):
        calcular_partes({"a": cand("a", "A", "x", 10)}, {}, {"A": 1}, {"A": 50})


def test_prazo_pagamento():
    assert prazo_pagamento_min(1) == 10
    assert prazo_pagamento_min(2) == 10
    assert prazo_pagamento_min(3) == 12
    assert prazo_pagamento_min(4) == 14


def test_crc16_vetor_conhecido():
    assert crc16_ccitt_false("123456789") == 0x29B1
    # exemplo do manual do BR Code (Banco Central): termina em "63041D3D"
    exemplo = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR"
               "5913Fulano de Tal6008BRASILIA62070503***6304")
    assert crc16_ccitt_false(exemplo) == 0x1D3D


def test_pix_campos_e_crc():
    codigo = gerar_pix_copia_e_cola("organizador@exemplo.com", "João da Conceição Silva Júnior", "São Carlos", 24.49)
    campos = ler_campos(codigo)
    assert campos["00"] == "01"
    assert campos["26"] == "0014br.gov.bcb.pix0123organizador@exemplo.com"
    assert campos["52"] == "0000"
    assert campos["53"] == "986"
    assert campos["54"] == "24.49"
    assert campos["58"] == "BR"
    assert campos["59"] == "JOAO DA CONCEICAO SILVA J"  # sem acento, ≤ 25
    assert campos["60"] == "SAO CARLOS"
    assert campos["62"] == "0503***"
    # CRC: os 4 últimos caracteres batem com o recálculo sobre tudo até "6304" inclusive
    assert codigo[-8:-4] == "6304"
    assert codigo[-4:] == f"{crc16_ccitt_false(codigo[:-4]):04X}"
    assert codigo.isascii()


def test_pix_valor_formatado_e_txid():
    codigo = gerar_pix_copia_e_cola("+5516999999999", "Ana", "Sao Carlos", 10, txid="MATCH123")
    campos = ler_campos(codigo)
    assert campos["54"] == "10.00"
    assert campos["62"] == "0508MATCH123"
    assert ler_campos(gerar_pix_copia_e_cola("x@y.com", "Ana", "Uma Cidade Muito Comprida", 0.1))["60"] == "UMA CIDADE MUIT"


@pytest.mark.parametrize(
    "chave, nome, cidade, valor, txid",
    [
        ("", "Ana", "Sao Carlos", 10, "***"),
        ("   ", "Ana", "Sao Carlos", 10, "***"),
        ("x@y.com", "Ana", "Sao Carlos", 0, "***"),
        ("x@y.com", "Ana", "Sao Carlos", -5, "***"),
        ("x@y.com", "", "Sao Carlos", 10, "***"),
        ("x@y.com", "Ana", "", 10, "***"),
        ("x@y.com", "Ana", "Sao Carlos", 10, "com espaço"),
    ],
)
def test_pix_entradas_invalidas(chave, nome, cidade, valor, txid):
    with pytest.raises(ValueError):
        gerar_pix_copia_e_cola(chave, nome, cidade, valor, txid=txid)


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("123.456.789-09", ("12345678909", "cpf")),
        ("52998224725", ("52998224725", "cpf")),
        ("12.345.678/0001-95", ("12345678000195", "cnpj")),
        ("12345678000195", ("12345678000195", "cnpj")),
        ("+55 (16) 99999-0000", ("+5516999990000", "telefone")),
        ("+5516999990000", ("+5516999990000", "telefone")),
        ("(16) 99999-0000", ("+5516999990000", "telefone")),
        ("16 99999-0000", ("+5516999990000", "telefone")),
        ("5516999990000", ("+5516999990000", "telefone")),
        ("16999990000", ("+5516999990000", "telefone")),  # 11 dígitos, DV de CPF não fecha, 3º dígito 9
        ("(16) 3333-4444", ("+551633334444", "telefone")),
        ("  Ana.Silva@Exemplo.COM ", ("ana.silva@exemplo.com", "email")),
        ("123E4567-E12B-12D1-A456-426655440000", ("123e4567-e12b-12d1-a456-426655440000", "aleatoria")),
    ],
)
def test_normalizar_chave_pix(entrada, esperado):
    assert normalizar_chave_pix(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "   ", "abc", "12345678900", "123.456.789-00", "+1 202 555 0100",
                                     "(00) 99999-0000", "ana@", "João@exemplo.com", "12345"])
def test_normalizar_chave_pix_invalida(entrada):
    with pytest.raises(ValueError):
        normalizar_chave_pix(entrada)


def test_pix_usa_chave_normalizada_e_crc_continua_valido():
    for crua, normal in [("123.456.789-09", "12345678909"), ("+55 (16) 99999-0000", "+5516999990000"),
                         ("16999990000", "+5516999990000"), ("ANA@Exemplo.com", "ana@exemplo.com"),
                         ("12.345.678/0001-95", "12345678000195")]:
        codigo = gerar_pix_copia_e_cola(crua, "Ana", "Sao Carlos", 12.5)
        assert ler_campos(codigo)["26"] == f"0014br.gov.bcb.pix01{len(normal):02d}{normal}"
        assert codigo[-4:] == f"{crc16_ccitt_false(codigo[:-4]):04X}"
        assert codigo == gerar_pix_copia_e_cola(normal, "Ana", "Sao Carlos", 12.5)  # idempotente
