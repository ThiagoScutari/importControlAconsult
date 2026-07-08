"""Identifica o tipo de um documento pelo seu **conteúdo** (não pelo nome).

Âncoras conforme seção 3 das instruções. A ordem de verificação evita
confusões: os fechamentos são checados pelo CNPJ/cabeçalho do despachante,
depois DUIMP, DI e por fim a NF-e.
"""
from __future__ import annotations

import re
from enum import Enum


class TipoDocumento(str, Enum):
    DUIMP = "duimp"
    DI = "di"
    NOTA_FISCAL = "nota_fiscal"
    FECHAMENTO_TERRA = "fechamento_terra"
    FECHAMENTO_WIN = "fechamento_win"
    FECHAMENTO_SYNDEX = "fechamento_syndex"
    DESCONHECIDO = "desconhecido"


# CNPJs dos despachantes (âncora mais confiável que o cabeçalho).
CNPJ_TERRA = "05.989.453/0001-06"
CNPJ_WIN = "26.316.473/0002-77"
CNPJ_SYNDEX = "02.286.106/0002-00"


def detectar_tipo(texto: str) -> TipoDocumento:
    """Retorna o :class:`TipoDocumento` correspondente ao texto extraído."""
    if not texto:
        return TipoDocumento.DESCONHECIDO

    t = texto
    tu = texto.upper()

    # 1) Fechamentos despadronizados — CNPJ/cabeçalho do despachante.
    #    Checados ANTES de DUIMP/DI/NF: um fechamento pode conter o texto da
    #    própria declaração anexada (dossiê). Âncora = CNPJ do despachante
    #    (a palavra "SYNDEX", p.ex., aparece na própria DUIMP e não serve).
    if CNPJ_TERRA in t or "TERRA DESP. ADUANEIROS" in tu:
        return TipoDocumento.FECHAMENTO_TERRA
    if CNPJ_WIN in t or "WIN TRADING" in tu:
        return TipoDocumento.FECHAMENTO_WIN
    if CNPJ_SYNDEX in t or "DEMONSTRATIVO DE DESPESAS" in tu or "PEDIDO DE NUMERÁRIO" in tu:
        return TipoDocumento.FECHAMENTO_SYNDEX

    # 2) DUIMP — âncora específica "Extrato da Duimp" (a NF-e cita "DUIMP" nas
    #    informações complementares, então a palavra solta não serve).
    if "EXTRATO DA DUIMP" in tu:
        return TipoDocumento.DUIMP

    # 3) DI — extrato da declaração de importação / "Declaração: NN/NNNNNNN-N".
    if "EXTRATO DA DECLARA" in tu or re.search(r"DECLARA[ÇC][ÃA]O:\s*\d{2}/\d{7}-\d", tu):
        return TipoDocumento.DI

    # 4) Nota Fiscal de importação — DANFE / NF-e.
    if "DANFE" in tu or "NF-E" in tu or "NOTA FISCAL ELETR" in tu:
        return TipoDocumento.NOTA_FISCAL

    return TipoDocumento.DESCONHECIDO
