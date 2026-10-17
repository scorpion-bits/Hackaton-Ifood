"""Pix "copia e cola" (BR Code estático, padrão EMV do Banco Central) — contrato C4.

Cada campo = ID (2) + tamanho (2, zero à esquerda) + valor. O CRC16-CCITT-FALSE (poly 0x1021,
init 0xFFFF) é calculado sobre a string inteira, incluindo "6304".
O valor vai para a chave do organizador; o app nunca guarda nem movimenta dinheiro.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

GUI_PIX = "br.gov.bcb.pix"
MAX_NOME = 25
MAX_CIDADE = 15
MAX_TXID = 25


def crc16_ccitt_false(dados: str) -> int:
    """CRC16-CCITT-FALSE sobre os bytes UTF-8 de `dados`."""
    crc = 0xFFFF
    for byte in dados.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def _campo(id_: str, valor: str) -> str:
    if len(valor) > 99:
        raise ValueError(f"Campo {id_} do Pix passou de 99 caracteres.")
    return f"{id_}{len(valor):02d}{valor}"


def _sem_acento(texto: str) -> str:
    """Remove acentos e qualquer caractere fora do ASCII imprimível."""
    normal = unicodedata.normalize("NFKD", texto)
    ascii_ = normal.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\x20-\x7E]", "", ascii_)


def _limpar(texto: str, limite: int, rotulo: str) -> str:
    limpo = " ".join(_sem_acento(texto or "").split()).upper()[:limite].strip()
    if not limpo:
        raise ValueError(f"Informe o {rotulo} do recebedor do Pix.")
    return limpo


def _valor_texto(valor: float) -> str:
    try:
        decimal = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Valor do Pix inválido.") from None
    if not decimal.is_finite() or decimal <= 0:
        raise ValueError("O valor do Pix precisa ser maior que zero.")
    texto = f"{decimal:.2f}"
    if len(texto) > 13:
        raise ValueError("Valor do Pix grande demais.")
    return texto


def gerar_pix_copia_e_cola(chave: str, nome: str, cidade: str, valor: float, txid: str = "***") -> str:
    """Gera o código "copia e cola" de um Pix estático com valor preenchido."""
    chave = (chave or "").strip()
    if not chave:
        raise ValueError("Informe a chave Pix do organizador.")
    if not chave.isascii():
        raise ValueError("Chave Pix com caractere inválido (acento ou símbolo).")
    if len(chave) > 77:
        raise ValueError("Chave Pix longa demais (máx. 77 caracteres).")
    txid = (txid or "***").strip()
    if txid != "***" and not re.fullmatch(rf"[A-Za-z0-9]{{1,{MAX_TXID}}}", txid):
        raise ValueError("Identificador (txid) do Pix: só letras e números, até 25.")

    conta = _campo("00", GUI_PIX) + _campo("01", chave)
    corpo = (
        _campo("00", "01")
        + _campo("26", conta)
        + _campo("52", "0000")
        + _campo("53", "986")
        + _campo("54", _valor_texto(valor))
        + _campo("58", "BR")
        + _campo("59", _limpar(nome, MAX_NOME, "nome"))
        + _campo("60", _limpar(cidade, MAX_CIDADE, "cidade"))
        + _campo("62", _campo("05", txid))
        + "6304"
    )
    return corpo + f"{crc16_ccitt_false(corpo):04X}"


def ler_campos(codigo: str) -> dict[str, str]:
    """Separa os campos de primeiro nível de um BR Code (útil para testes e conferência)."""
    campos: dict[str, str] = {}
    i = 0
    while i < len(codigo):
        id_, tamanho = codigo[i:i + 2], int(codigo[i + 2:i + 4])
        campos[id_] = codigo[i + 4:i + 4 + tamanho]
        i += 4 + tamanho
    return campos
