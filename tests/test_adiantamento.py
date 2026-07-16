"""Item 4 [F1-04]: captura do total de 'adiantamento' (crédito do Passo 6.2).

Regra spec §1.5 6.2 [R2]: somar toda linha do fechamento rotulada "adiantamento".
Posição varia por layout (SYNDEX = crédito; TERRA = linha nas despesas; WIN = ausente).
"""
import pytest

from backend.consolidador import consolidar
from backend.extractors import (
    duimp,
    fechamento_syndex,
    fechamento_terra,
    fechamento_win,
    nota_fiscal,
)


def test_syndex_soma_dois_adiantamentos(textos):
    d = fechamento_syndex.extrair(textos["syndex_fechamento"])
    # Dois "ADIANTAMENTO DE NUMERÁRIO" — evidência: os 2 Pix 101.645,23 + 2.090,00.
    assert len(d["adiantamentos"]) == 2
    assert d["adiantamento_total"] == pytest.approx(103735.23, abs=0.01)


def test_terra_captura_adiantamento(textos):
    d = fechamento_terra.extrair(textos["terra"])
    assert d["adiantamento_total"] == pytest.approx(45692.26, abs=0.01)


def test_win_sem_adiantamento_nao_quebra(textos):
    d = fechamento_win.extrair(textos["win"])
    assert d["adiantamento_total"] is None
    assert d["adiantamentos"] == []


def test_consolida_adiantamento_no_processo(textos):
    docs = [
        duimp.extrair(textos["duimp_sy1453"]),
        nota_fiscal.extrair(textos["nf_sy1453"]),
        fechamento_syndex.extrair(textos["syndex_fechamento"]),
    ]
    p = consolidar(docs)
    # o adiantamento (crédito) chega ao processo — antes era descartado
    assert p.adiantamento_total == pytest.approx(103735.23, abs=0.01)
    assert len(p.adiantamentos) == 2
