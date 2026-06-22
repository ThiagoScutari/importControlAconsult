"""Fixtures compartilhados dos testes."""
import os
import sys

import pytest

# Garante que a raiz do projeto está no sys.path (para `import backend...`)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ASSETS = os.path.join(ROOT, "assets")

# Mapa amigável -> caminho real dos arquivos de exemplo em assets/
ASSET_FILES = {
    "duimp1159": os.path.join(ASSETS, "DUIMP 1159.pdf"),
    "nf1159": os.path.join(ASSETS, "NOTA FISCAL DE IMPORTAÇÃO 1159.pdf"),
    "di870": os.path.join(ASSETS, "DI_870.pdf.pdf"),
    "terra": os.path.join(ASSETS, "Fechamento TERRA.pdf.pdf"),
    "win": os.path.join(ASSETS, "Fechamento WIN TRADING.pdf"),
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
