"""Testes de consolidação e geração de arquivos (seção 9)."""
import pytest

from backend.consolidador import consolidar
from backend.extractors import duimp, di, nota_fiscal, fechamento_terra
from backend.models import Lancamento, MiddlewareInput
from backend.outputs import (
    COLUNAS_A,
    gerar_lancamentos_sugeridos,
    gerar_saida_a,
    gerar_saida_b,
)


@pytest.fixture
def proc_1159(textos):
    docs = [duimp.extrair(textos["duimp1159"]), nota_fiscal.extrair(textos["nf1159"])]
    return consolidar(docs)


@pytest.fixture
def proc_870(textos):
    docs = [di.extrair(textos["di870"]), fechamento_terra.extrair(textos["terra"])]
    return consolidar(docs)


class TestConsolidacao:
    def test_duimp_mais_nf_gera_processo_1159(self, proc_1159):
        assert proc_1159.processo == "1159"
        assert proc_1159.di_duimp == "26BR0000380790-9"
        assert proc_1159.numero_nf == "000.000.769"
        assert proc_1159.valor_nf == pytest.approx(153280.85, abs=0.01)
        assert proc_1159.fob_rs == pytest.approx(79882.82, abs=0.01)
        assert proc_1159.chave_nfe == "42260457345180000160550010000007691435300822"
        assert "HONGKONG YESOP" in proc_1159.fornecedor_estrangeiro

    def test_di_mais_terra_gera_processo_870(self, proc_870):
        assert proc_870.processo == "870"
        assert proc_870.di_duimp == "25/2290426-3"
        assert "TERRA" in proc_870.despachante
        # AFRMM e armazenagem vêm do fechamento
        assert proc_870.afrmm == pytest.approx(1595.46, abs=0.01)
        assert proc_870.armazenagem == pytest.approx(3938.82, abs=0.01)

    def test_processo_com_um_unico_documento_nao_quebra(self, textos):
        proc = consolidar([duimp.extrair(textos["duimp1159"])])
        assert proc.processo == "1159"
        assert proc.numero_nf is None  # sem NF, não inventa
        # ausência de NF deve gerar aviso (campo crítico)
        assert any(a.campo == "numero_nf" for a in proc.avisos)


@pytest.fixture
def proc_sy1453(textos):
    from backend.extractors import duimp, fechamento_syndex
    docs = [
        duimp.extrair(textos["duimp_sy1453"]),
        nota_fiscal.extrair(textos["nf_sy1453"]),
        fechamento_syndex.extrair(textos["syndex_fechamento"]),
    ]
    return consolidar(docs)


class TestSaidaA:
    def test_cabecalho_e_uma_linha(self, proc_1159):
        csv_txt = gerar_saida_a([proc_1159])
        linhas = csv_txt.strip().splitlines()
        assert linhas[0].split(";") == COLUNAS_A
        assert len(linhas) == 2  # cabeçalho + 1 processo
        assert "1159" in linhas[1]

    def test_saida_a_v02_tem_colunas_novas(self, proc_sy1453):
        # Layout v0.2: câmbio (1–8) + Reforma
        for col in ["Resultado R$", "TX DI", "USD PG Câmbio", "Variação",
                    "CBS", "IBS-UF", "IBS-MUN"]:
            assert col in COLUNAS_A
        csv_txt = gerar_saida_a([proc_sy1453])
        assert csv_txt.splitlines()[0].split(";") == COLUNAS_A

    def test_campos_reforma_e_resultado_sy1453(self, proc_sy1453):
        # CBS/IBS vêm da NF; resultado_rs = invoice_usd × tx_di
        assert proc_sy1453.cbs == pytest.approx(3018.30, abs=0.01)
        assert proc_sy1453.ibs_uf == pytest.approx(273.57, abs=0.01)
        assert proc_sy1453.tx_di == pytest.approx(5.28, abs=0.0001)
        assert proc_sy1453.invoice_usd == pytest.approx(52403.08, abs=0.01)
        assert proc_sy1453.resultado_rs == pytest.approx(276688.26, abs=0.01)


class TestSaidaB:
    def test_layout_10_colunas_sem_cabecalho(self):
        lanc = [
            Lancamento(
                data="30/04/2026", conta_debito="12374", conta_credito="805",
                valor=286876.72, cod_historico="25",
                complemento_historico="REF. ACERTO PAGAMENTOS FORNECEDOR",
            )
        ]
        txt = gerar_saida_b(lanc)
        linhas = txt.strip().splitlines()
        # sem cabeçalho: a primeira linha já é dado
        assert linhas[0].startswith("30/04/2026;")
        colunas = linhas[0].split(";")
        assert len(colunas) == 10
        assert colunas[3] == "286876,72"  # valor BR sem separador de milhar

    def test_sugestao_a_partir_do_fechamento(self, proc_870):
        lancs = gerar_lancamentos_sugeridos(proc_870, MiddlewareInput())
        assert len(lancs) == len(proc_870.despesas) > 0
        txt = gerar_saida_b(lancs)
        for linha in txt.strip().splitlines():
            assert len(linha.split(";")) == 10
