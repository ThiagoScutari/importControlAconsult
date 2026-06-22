"""Teste de integração das rotas /extract e /generate (FastAPI TestClient)."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _upload(asset_files, *nomes):
    arquivos = []
    for nome in nomes:
        with open(asset_files[nome], "rb") as fh:
            arquivos.append(("arquivos", (nome + ".pdf", fh.read(), "application/pdf")))
    return arquivos


def test_extract_consolida_processo_1159(asset_files):
    resp = client.post("/extract", files=_upload(asset_files, "duimp1159", "nf1159"))
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["processo"] == "1159"
    assert dados["di_duimp"] == "26BR0000380790-9"
    assert dados["numero_nf"] == "000.000.769"
    assert "sugestoes_middleware" in dados


def test_extract_ignora_arquivo_irreconhecivel(asset_files):
    arquivos = [("arquivos", ("lixo.pdf", b"%PDF-1.4 nada util", "application/pdf"))]
    resp = client.post("/extract", files=arquivos)
    assert resp.status_code == 200
    assert resp.json()["nao_reconhecidos"]


def test_generate_devolve_zip_com_saidas(asset_files):
    extraido = client.post("/extract", files=_upload(asset_files, "di870", "terra")).json()
    body = {"processo": extraido, "middleware": {"incluir_saida_c": True}}
    resp = client.post("/generate", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    nomes = zf.namelist()
    assert "saida_A_extracao.csv" in nomes
    assert "saida_B_lancamentos_dominio.csv" in nomes
    assert "saida_B_lancamentos_dominio.txt" in nomes
    assert "saida_C_fornecedores.csv" in nomes

    # Saída B: 10 colunas por linha, sem cabeçalho
    conteudo_b = zf.read("saida_B_lancamentos_dominio.csv").decode("utf-8-sig")
    primeira = conteudo_b.strip().splitlines()[0]
    assert len(primeira.split(";")) == 10


def test_index_serve_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Extrator de Importação" in resp.text
