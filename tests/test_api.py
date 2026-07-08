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
    # nomes prefixados com a referência do processo (870)
    assert any(n.endswith("saida_A_extracao.csv") for n in nomes)
    assert any(n.endswith("saida_B_lancamentos_dominio.csv") for n in nomes)
    assert any(n.endswith("saida_B_lancamentos_dominio.txt") for n in nomes)
    assert any(n.endswith("saida_C_fornecedores.csv") for n in nomes)
    assert all(n.startswith("870_") for n in nomes)

    # Saída B: 10 colunas por linha, sem cabeçalho
    nome_b = next(n for n in nomes if n.endswith("saida_B_lancamentos_dominio.csv"))
    conteudo_b = zf.read(nome_b).decode("utf-8-sig")
    primeira = conteudo_b.strip().splitlines()[0]
    assert len(primeira.split(";")) == 10


def test_extract_sy1453_reforma_e_classificacao(asset_files):
    resp = client.post("/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento"))
    dados = resp.json()
    assert dados["di_duimp"] == "26BR0000258971-1"
    assert dados["numero_nf"] == "000.002.411"
    assert dados["resultado_rs"] == pytest.approx(276688.26, abs=0.01)
    assert dados["cbs"] == pytest.approx(3018.30, abs=0.01)
    sm = dados["sugestoes_middleware"]
    assert sm["conta_processo_nome"].startswith("PROCESSO")
    cats = {d["descricao"]: d["categoria"] for d in sm["despesas"]}
    assert cats["IMPOSTO DE IMPORTAÇÃO"] == "tributo_federal_na_nf"
    assert cats["ARMAZENAGEM"] == "despesa_processo"


def test_generate_sy1453_saida_b_respeita_guard(asset_files):
    extraido = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    body = {"processo": extraido, "middleware": {"contas_override": {"adiantamento_despachante": "9101"}}}
    resp = client.post("/generate", json=body)
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    nome_b = next(n for n in zf.namelist() if n.endswith("saida_B_lancamentos_dominio.csv"))
    b = zf.read(nome_b).decode("utf-8-sig")
    linhas = b.strip().splitlines()
    # todas com 10 colunas
    assert all(len(l.split(";")) == 10 for l in linhas)
    # guard §3: o Imposto de Importação (tributo federal) não vira partida 6.2
    assert not any("IMPOSTO DE IMPORTA" in l.upper() and ";41;" in l for l in linhas)
    # Passo 5.2 presente com o valor devido ao fornecedor
    assert any("276688,26" in l for l in linhas)


def _saida(zf, sufixo):
    nome = next(n for n in zf.namelist() if n.endswith(sufixo))
    return zf.read(nome).decode("utf-8-sig")


def test_round_trip_nao_corrompe_decimais(asset_files):
    """/extract -> /generate SEM alterar: os decimais devem sobreviver."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    resp = client.post("/generate", json={"processo": proc, "middleware": {}})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))

    b = _saida(zf, "saida_B_lancamentos_dominio.csv").strip().splitlines()
    p51 = next(l for l in b if l.split(";")[1] == "1633")  # Passo 5.1
    assert p51.split(";")[3] == "382358,58"          # NÃO 38235858,00
    p52 = next(l for l in b if "VALOR DEVIDO FORNECEDOR" in l)
    assert p52.split(";")[3] == "276688,26"
    assert "USD 52.403,08 TAXA INVOICE 5,28" in p52  # histórico coerente

    a = _saida(zf, "saida_A_extracao.csv").splitlines()
    hdr, row = a[0].split(";"), a[1].split(";")
    linha = dict(zip(hdr, row))
    assert linha["Valor NF"] == "382.358,58"
    assert linha["Resultado R$"] == "276.688,26"
    assert linha["TX DI"] == "5,2800"


def test_round_trip_valores_como_string_do_formulario(asset_files):
    """O front envia strings (ponto = decimal do JS); backend não pode corromper."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    # simula o formulário: números viram string com ponto decimal
    proc["valor_nf"] = "382358.58"
    proc["invoice_usd"] = "52403.08"
    proc["tx_di"] = "5.28"
    proc["resultado_rs"] = "276688.26"
    resp = client.post("/generate", json={"processo": proc, "middleware": {}})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    b = _saida(zf, "saida_B_lancamentos_dominio.csv")
    assert "382358,58" in b and "276688,26" in b
    assert "38235858" not in b and "528,0000" not in b  # sem corrupção


def test_generate_avisa_conta_faltante(asset_files):
    """Bug 2: papel sem código -> AVISOS.txt no zip (não passa em silêncio)."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    # sem contas_override: adiantamento_despachante fica sem código
    resp = client.post("/generate", json={"processo": proc, "middleware": {}})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    nomes = zf.namelist()
    assert any(n.endswith("AVISOS.txt") for n in nomes)
    avisos = _saida(zf, "AVISOS.txt")
    assert "adiantamento_despachante" in avisos or "incompleta" in avisos.lower()


def test_index_serve_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Extrator de Importação" in resp.text
