"""Fixtures compartilhados dos testes."""
import glob
import os
import sys

import pytest

# Garante que a raiz do projeto está no sys.path (para `import backend...`)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ASSETS = os.path.join(ROOT, "assets")
SY1453 = os.path.join(ASSETS, "corpus", "sy1453_syndex")


def _um(padrao: str) -> str:
    """Resolve um único arquivo por glob (evita hardcode de nome com acentos)."""
    achados = glob.glob(os.path.join(SY1453, padrao))
    if not achados:
        raise FileNotFoundError(f"corpus SY1453: nenhum arquivo casa {padrao!r}")
    return achados[0]


# Mapa amigável -> caminho real dos arquivos de exemplo em assets/
ASSET_FILES = {
    "duimp1159": os.path.join(ASSETS, "DUIMP 1159.pdf"),
    "nf1159": os.path.join(ASSETS, "NOTA FISCAL DE IMPORTAÇÃO 1159.pdf"),
    "di870": os.path.join(ASSETS, "DI_870.pdf.pdf"),
    "terra": os.path.join(ASSETS, "Fechamento TERRA.pdf.pdf"),
    "win": os.path.join(ASSETS, "Fechamento WIN TRADING.pdf"),
    # Kit SY1453 (SYNDEX) — resolvido por glob por causa dos acentos nos nomes
    "duimp_sy1453": _um("DUIMP DESEMBARA*SY1453*.pdf"),
    "nf_sy1453": _um("*NOTA FISCAL IMPORTA*.pdf"),
    "syndex_fechamento": _um("FECHAMENTO_SY1453*Fatura.pdf"),
    "syndex_numerario": _um("NUMERARIO*SY1453*[!O].pdf"),
    # Dossiê CONNECTA (layout FATURAMENTO) — DUIMP+NF+faturamento em um só PDF
    "connecta": os.path.join(ASSETS, "corpus", "0020-26 - FECHAMENTO COMPLETO.pdf"),
}


@pytest.fixture(scope="session")
def assets_dir():
    return ASSETS


@pytest.fixture(scope="session")
def asset_files():
    return ASSET_FILES


@pytest.fixture(scope="session")
def textos(asset_files):
    """Texto extraído de cada PDF de exemplo (cacheado na sessão)."""
    from backend.pdf_utils import extract_text

    return {nome: extract_text(caminho) for nome, caminho in asset_files.items()}
