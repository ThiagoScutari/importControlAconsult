"""Teste de integração das rotas /extract e /generate (FastAPI TestClient)."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# de-para POR EMPRESA que o operador preenche. [R3] (Item 5): sem estes números
# as contas do processo/fornecedor ficam em branco e as partidas dos Passos
# 5/6.2 NÃO são geradas — então os testes de round-trip precisam semeá-las.
_CONTAS = {
    "conta_processo": "1648",
    "fornecedor_estrangeiro": "1177",
    "adiantamento_despachante": "9101",
}


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
    assert dados["numero_nf"] == "769"  # [R3] inteiro limpo
    assert "sugestoes_middleware" in dados


def test_extract_ignora_arquivo_irreconhecivel(asset_files):
    arquivos = [("arquivos", ("lixo.pdf", b"%PDF-1.4 nada util", "application/pdf"))]
    resp = client.post("/extract", files=arquivos)
    assert resp.status_code == 200
    assert resp.json()["nao_reconhecidos"]


def test_generate_devolve_zip_com_saidas(asset_files):
    extraido = client.post("/extract", files=_upload(asset_files, "di870", "terra")).json()
    body = {"processo": extraido, "middleware": {"incluir_saida_c": True, "contas_override": _CONTAS}}
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
    assert dados["numero_nf"] == "2411"  # [R3] inteiro limpo
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
    body = {"processo": extraido, "middleware": {"contas_override": _CONTAS}}
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
    resp = client.post("/generate", json={"processo": proc, "middleware": {"contas_override": _CONTAS}})
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
    resp = client.post("/generate", json={"processo": proc, "middleware": {"contas_override": _CONTAS}})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    b = _saida(zf, "saida_B_lancamentos_dominio.csv")
    assert "382358,58" in b and "276688,26" in b
    assert "38235858" not in b and "528,0000" not in b  # sem corrupção


def test_round_trip_cambio_string_nao_corrompe_variacao(asset_files):
    """Câmbio 4–5 são strings manuais e alimentam o Passo 8; não podem corromper."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    mid = {
        "vlr_usd_pg_cambio": "52.403,08",  # BR
        "tx_cambio": "5,10",               # BR
        "contas_override": {"fornecedor_estrangeiro": "1177", "variacao_cambial_ativa": "973"},
    }
    resp = client.post("/generate", json={"processo": proc, "middleware": mid})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    b = _saida(zf, "saida_B_lancamentos_dominio.csv")
    linha = next(l for l in b.splitlines() if "VARIA" in l.upper())
    # valor da partida = |variação|; magnitude 9.432,55 (sem corrupção do decimal)
    assert linha.split(";")[3] == "9432,55"
    a = dict(zip(*[r.split(";") for r in _saida(zf, "saida_A_extracao.csv").splitlines()[:2]]))
    assert a["VLR PG R$"] == "267.255,71"
    # [R3] variação = campo 6 − campo 7 = 267.255,71 − 276.688,26 = -9.432,55 (negativa)
    assert a["Variação"] == "-9.432,55"


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


def test_generate_conta_processo_numero_preenche_saida_b(asset_files):
    """[bug Saída B vazia] Payload igual ao do front: o operador preencheu só o
    campo "Conta do Processo — número" do middleware. A Saída B não pode voltar
    sem linhas (era exatamente o CSV vazio reportado)."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    mid = {"conta_processo_numero": "1648", "contas_override": {}, "lancamentos": []}
    resp = client.post("/generate", json={"processo": proc, "middleware": mid})
    assert resp.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    b = _saida(zf, "saida_B_lancamentos_dominio.csv").strip()
    assert b, "Saída B veio vazia mesmo com a conta do processo informada"
    linhas = b.splitlines()
    assert all(len(l.split(";")) == 10 for l in linhas)
    assert linhas[0].split(";")[2] == "1648"  # Passo 5.1 credita a conta do processo


def test_generate_sinaliza_saida_b_vazia_nos_headers(asset_files):
    """[bug Saída B vazia] Sem nenhuma conta preenchida a Saída B sai sem linhas;
    o /generate precisa dizer isso ao front (headers) em vez de responder ✓ mudo."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    resp = client.post("/generate", json={"processo": proc, "middleware": {}})
    assert resp.status_code == 200
    assert resp.headers["x-saida-b-partidas"] == "0"
    pendentes = resp.headers["x-contas-pendentes"].split(",")
    assert "conta_processo" in pendentes

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "vazia" in _saida(zf, "AVISOS.txt").lower()


def test_generate_headers_com_partidas(asset_files):
    """Caminho feliz: contagem de partidas no header e nada pendente."""
    proc = client.post(
        "/extract", files=_upload(asset_files, "duimp_sy1453", "nf_sy1453", "syndex_fechamento")
    ).json()
    resp = client.post("/generate", json={"processo": proc, "middleware": {"contas_override": _CONTAS}})
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    linhas = _saida(zf, "saida_B_lancamentos_dominio.csv").strip().splitlines()
    assert resp.headers["x-saida-b-partidas"] == str(len(linhas))
    assert int(resp.headers["x-saida-b-partidas"]) > 0
    assert resp.headers["x-contas-pendentes"] == ""


def test_index_serve_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Extrator de Importação" in resp.text


def test_upload_acima_do_limite_recusado_413():
    """[F1-10] Limite de upload no app: Content-Length acima do teto -> 413."""
    from backend.main import MAX_UPLOAD_BYTES

    resp = client.post(
        "/extract",
        headers={"content-length": str(MAX_UPLOAD_BYTES + 1)},
        content=b"x",
    )
    assert resp.status_code == 413
    assert "limite" in resp.json()["erro"].lower()
