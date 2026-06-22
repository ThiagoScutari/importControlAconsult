"""Cada arquivo de assets/ deve ser classificado no tipo correto (seção 9)."""
import pytest

from backend.detector import TipoDocumento, detectar_tipo


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("duimp1159", TipoDocumento.DUIMP),
        ("nf1159", TipoDocumento.NOTA_FISCAL),
        ("di870", TipoDocumento.DI),
        ("terra", TipoDocumento.FECHAMENTO_TERRA),
        ("win", TipoDocumento.FECHAMENTO_WIN),
    ],
)
def test_classifica_assets(textos, nome, esperado):
    assert detectar_tipo(textos[nome]) == esperado


def test_texto_irreconhecivel_retorna_desconhecido():
    assert detectar_tipo("um texto qualquer sem âncoras") == TipoDocumento.DESCONHECIDO


def test_nao_confunde_di_com_duimp():
    # DI não contém "Extrato da Duimp"; DUIMP não deve cair em DI
    assert detectar_tipo("Declaração: 25/2290426-3 Data do Registro") == TipoDocumento.DI
