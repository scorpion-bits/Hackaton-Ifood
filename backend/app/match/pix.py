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


_EMAIL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(\.[a-z0-9-]+)+")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_CPF_PONTUADO = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CNPJ_PONTUADO = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_SO_TELEFONE = re.compile(r"\+?[\d\s().-]+")


def _cpf_valido(digitos: str) -> bool:
    if len(digitos) != 11 or not digitos.isdigit() or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], range(tamanho + 1, 1, -1)))
        if int(digitos[tamanho]) != (soma * 10 % 11) % 10:
            return False
    return True


def _telefone(nacional: str) -> tuple[str, str]:
    """`nacional` = DDD + número (10 ou 11 dígitos). Devolve ("+55…", "telefone")."""
    if len(nacional) not in (10, 11) or not 11 <= int(nacional[:2]) <= 99 \
            or (len(nacional) == 11 and nacional[2] != "9"):
        raise ValueError("Telefone da chave Pix inválido: use DDD + número, ex. (16) 99999-0000.")
    return "+55" + nacional, "telefone"


def normalizar_chave_pix(chave: str) -> tuple[str, str]:
    """Deixa a chave no formato do BR Code. Devolve (chave normalizada, tipo).

    Tipos: "email" (minúsculas, sem espaços) · "cpf"/"cnpj" (só dígitos) · "telefone" (+55DDDNÚMERO) ·
    "aleatoria" (UUID em minúsculas). 11 dígitos sem pontuação: CPF se o dígito verificador fecha; senão, se parece
    celular (3º dígito 9), telefone. Formato irreconhecível → ValueError legível.
    """
    bruta = (chave or "").strip()
    if not bruta:
        raise ValueError("Informe a chave Pix do organizador.")
    if not bruta.isascii():
        raise ValueError("Chave Pix com caractere inválido (acento ou símbolo).")
    if "@" in bruta:
        email = "".join(bruta.split()).lower()
        if not _EMAIL.fullmatch(email):
            raise ValueError("E-mail da chave Pix inválido.")
        if len(email) > 77:
            raise ValueError("Chave Pix longa demais (máx. 77 caracteres).")
        return email, "email"
    if _UUID.fullmatch(bruta.lower()):
        return bruta.lower(), "aleatoria"
    if _CPF_PONTUADO.fullmatch(bruta) or _CNPJ_PONTUADO.fullmatch(bruta):
        digitos = re.sub(r"\D", "", bruta)
        if len(digitos) == 11 and not _cpf_valido(digitos):
            raise ValueError("CPF da chave Pix inválido (confira os dígitos).")
        return digitos, "cpf" if len(digitos) == 11 else "cnpj"
    if not _SO_TELEFONE.fullmatch(bruta):
        raise ValueError("Chave Pix irreconhecível: use e-mail, CPF, CNPJ, telefone com DDD ou chave aleatória.")
    digitos = re.sub(r"\D", "", bruta)
    if bruta.startswith("+"):
        if not digitos.startswith("55"):
            raise ValueError("Telefone da chave Pix: só números do Brasil (+55).")
        return _telefone(digitos[2:])
    if "(" in bruta:  # "(16) 99999-0000" é telefone mesmo com 11 dígitos
        return _telefone(digitos)
    if len(digitos) == 14:
        return digitos, "cnpj"
    if len(digitos) == 11:
        if _cpf_valido(digitos):
            return digitos, "cpf"
        if digitos[2] == "9":
            return _telefone(digitos)
        raise ValueError("CPF da chave Pix inválido (confira os dígitos).")
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return _telefone(digitos[2:])
    if len(digitos) == 10:
        return _telefone(digitos)
    raise ValueError("Chave Pix irreconhecível: use e-mail, CPF, CNPJ, telefone com DDD ou chave aleatória.")


def gerar_pix_copia_e_cola(chave: str, nome: str, cidade: str, valor: float, txid: str = "***") -> str:
    """Gera o código "copia e cola" de um Pix estático com valor preenchido."""
    chave, _tipo = normalizar_chave_pix(chave)
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
