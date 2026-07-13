"""Cada arquivo de assets/ deve ser classificado no tipo correto (seção 9).

Inclui os anexos/referência reais do corpus: a regressão que travou a demo era
o detector roteando anexo/dossiê para o parser errado (spec §10 / [R3]).
"""
import os

import pytest

from backend.detector import TipoDocumento, detectar_tipo
from backend.pdf_utils import extract_text

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORPUS = os.path.join(_ROOT, "assets", "corpus")

# Anexos/referência reais (não são tipos suportados) → devem virar ANEXO_REFERENCIA.
_ANEXOS = {
    "nfes_terra": os.path.join(_CORPUS, "982_cmo_terra", "NFES 1.pdf"),          # NFS-e c/ CNPJ do TERRA
    "gru_inmetro": os.path.join(_CORPUS, "982_cmo_terra", "GRU Inmetro 3631859.pdf"),
    "cte_frete": os.path.join(_CORPUS, "sy1453_syndex", "FRETE_PORTO-CTE.pdf"),  # CT-e que cita "NF-e"
    "boleto_frete": os.path.join(_CORPUS, "sy1453_syndex", "FRETE_PORTO-BOLETO.pdf"),
    "bill_of_lading": os.path.join(_CORPUS, "sy1453_syndex", "BILL OF LADING.pdf"),  # só-imagem
}


@pytest.fixture(scope="session")
def anexo_textos():
    return {nome: extract_text(caminho) for nome, caminho in _ANEXOS.items()}


@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("duimp1159", TipoDocumento.DUIMP),
        ("nf1159", TipoDocumento.NOTA_FISCAL),
        ("di870", TipoDocumento.DI),
        ("terra", TipoDocumento.FECHAMENTO_TERRA),
        ("win", TipoDocumento.FECHAMENTO_WIN),
        # Kit SY1453 (SYNDEX)
        ("duimp_sy1453", TipoDocumento.DUIMP),
        ("nf_sy1453", TipoDocumento.NOTA_FISCAL),
        ("syndex_fechamento", TipoDocumento.FECHAMENTO_SYNDEX),
        ("syndex_numerario", TipoDocumento.FECHAMENTO_SYNDEX),
    ],
)
def test_classifica_assets(textos, nome, esperado):
    assert detectar_tipo(textos[nome]) == esperado


@pytest.mark.parametrize("nome", list(_ANEXOS))
def test_anexos_viram_referencia(anexo_textos, nome):
    # NFS-e (mesmo carregando o CNPJ do despachante), CT-e (que cita "NF-e"),
    # boleto/GRU e o BL só-imagem: todos ANEXO_REFERENCIA, nunca parser errado.
    assert detectar_tipo(anexo_textos[nome]) == TipoDocumento.ANEXO_REFERENCIA


def test_nfse_com_cnpj_terra_nao_vira_terra(anexo_textos):
    # Regressão da demo: a NFS-e do porto carrega o CNPJ do TERRA e caía no
    # fechamento_terra — agora é anexo.
    assert detectar_tipo(anexo_textos["nfes_terra"]) != TipoDocumento.FECHAMENTO_TERRA


def test_duimp_sy1453_nao_vira_syndex(textos):
    # A DUIMP contém a palavra "SYNDEX" e a carta do despachante, mas NÃO o
    # CNPJ do despachante — não pode ser classificada como fechamento.
    assert detectar_tipo(textos["duimp_sy1453"]) == TipoDocumento.DUIMP


def test_texto_longo_sem_ancora_e_desconhecido():
    txt = "um texto qualquer sem nenhuma ancora reconhecivel de documento " * 2
    assert detectar_tipo(txt) == TipoDocumento.DESCONHECIDO


def test_texto_vazio_ou_curto_vira_anexo_imagem():
    # PDF só-imagem/quase-vazio (sem camada de texto) → anexo (imagem), não desconhecido.
    assert detectar_tipo("") == TipoDocumento.ANEXO_REFERENCIA
    assert detectar_tipo("   ") == TipoDocumento.ANEXO_REFERENCIA
    assert detectar_tipo("rabisco") == TipoDocumento.ANEXO_REFERENCIA


def test_nao_confunde_di_com_duimp():
    # DI não contém "Extrato da Duimp"; DUIMP não deve cair em DI
    assert detectar_tipo("Declaração: 25/2290426-3 — Data do Registro da DI") == TipoDocumento.DI
