"""Helpers de extração de texto de PDF e parsing de números/datas no formato BR.

Mantém tudo isolado de regras de negócio: aqui só ficam utilidades genéricas
reutilizadas pelos extratores.
"""
from __future__ import annotations

import io
import re
from typing import Optional, Union

import pdfplumber

# ---------------------------------------------------------------------------
# Extração de texto
# ---------------------------------------------------------------------------

def extract_text(source: Union[str, bytes, io.IOBase]) -> str:
    """Extrai todo o texto de um PDF.

    Aceita um caminho de arquivo (str), bytes ou um objeto file-like.
    Concatena o texto de todas as páginas separando por ``\n``.
    """
    if isinstance(source, (bytes, bytearray)):
        stream: Union[io.IOBase, str] = io.BytesIO(source)
    else:
        stream = source

    partes = []
    with pdfplumber.open(stream) as pdf:
        for page in pdf.pages:
            partes.append(page.extract_text() or "")
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Números no formato brasileiro
# ---------------------------------------------------------------------------

# Número com separador de milhar (1.234.567,89) OU número simples (17069,00 / 965).
# A primeira alternativa exige ao menos um grupo ".ddd" para não truncar
# números longos sem separador (ex.: "17069" não pode virar "170").
_NUM_BR = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?")


def parse_valor_br(texto: Optional[str]) -> Optional[float]:
    """Converte ``"1.234,56"`` -> ``1234.56``.

    Regras:
    - ``.`` é separador de milhar, ``,`` é separador decimal.
    - Tolera prefixos como ``R$`` e espaços.
    - String vazia / ``None`` / sem dígitos -> ``None`` (campo não encontrado).
    """
    if texto is None:
        return None
    s = str(texto).strip()
    if not s:
        return None
    m = _NUM_BR.search(s)
    if not m:
        return None
    bruto = m.group(0)
    if "," in bruto:
        # vírgula decimal -> remove milhar (.) e troca vírgula por ponto
        normalizado = bruto.replace(".", "").replace(",", ".")
    else:
        # sem vírgula: pode ter . como milhar (ex.: "1.234") -> remove ponto
        normalizado = bruto.replace(".", "")
    try:
        return float(normalizado)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Helpers de regex
# ---------------------------------------------------------------------------

def buscar(padrao: str, texto: str, grupo: int = 1, flags: int = re.IGNORECASE) -> Optional[str]:
    """Retorna o grupo capturado da primeira ocorrência, ou ``None``."""
    m = re.search(padrao, texto, flags)
    if not m:
        return None
    return m.group(grupo).strip()


def buscar_valor(padrao: str, texto: str, grupo: int = 1, flags: int = re.IGNORECASE) -> Optional[float]:
    """Como :func:`buscar`, mas devolve o número BR já convertido em float."""
    bruto = buscar(padrao, texto, grupo, flags)
    return parse_valor_br(bruto)


_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")


def primeiro_cnpj(texto: str) -> Optional[str]:
    """Primeiro CNPJ encontrado no texto (formato ``00.000.000/0000-00``)."""
    m = _CNPJ.search(texto)
    return m.group(0) if m else None


def normalizar_espacos(texto: Optional[str]) -> Optional[str]:
    """Colapsa espaços/quebras de linha múltiplos em um único espaço."""
    if texto is None:
        return None
    return re.sub(r"\s+", " ", texto).strip()
