"""Testes dos extratores contra os valores esperados do Anexo A (seção 9)."""
import pytest

from backend.extractors import (
    duimp, di, nota_fiscal, fechamento_terra, fechamento_win, fechamento_syndex,
)


def approx(v):
    return pytest.approx(v, abs=0.01)


# ---------------------------------------------------------------------------
# DUIMP 1159
# ---------------------------------------------------------------------------
class TestDuimp1159:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return duimp.extrair(textos["duimp1159"])

    def test_identificacao(self, d):
        assert d["numero"] == "26BR0000380790-9"
        assert d["versao"] == "0001"
        assert "ZINLOG" in d["importador_nome"]
        assert d["importador_cnpj"] == "57.345.180/0001-60"
        assert d["tipo_importacao"] == "Conta e Ordem"
        assert d["referencia"] == "1159#"

    def test_fatura_e_cotacao(self, d):
        assert d["fatura_numero"] == "HKYCMOBR1159"
        assert d["fatura_data"] == "03/02/26"
        assert d["fatura_valor_us"] == approx(17069.00)
        assert d["cotacao"] == approx(5.0899)

    def test_valores(self, d):
        assert d["fob_rs"] == approx(79882.82)
        assert d["fob_us"] == approx(15694.38)
        assert d["frete_rs"] == approx(6996.68)
        assert d["valor_aduaneiro_rs"] == approx(86879.50)

    def test_tributos(self, d):
        assert d["ii"] == approx(15638.31)
        assert d["ipi"] == approx(9995.49)
        assert d["pis"] == approx(1824.47)
        assert d["cofins"] == approx(8383.87)
        assert d["siscomex"] == approx(154.23)
        assert d["total_tributos"] == approx(35996.37)

    def test_logistica(self, d):
        assert d["navio"] == "MSC AVNI"
        assert d["bl"] == "HLCUSHA2601CDGF5"
        assert d["chegada"] == "06/04/26"
        assert d["armazem"] == "BRASKARNE"
        assert d["volumes"] == approx(965)

    def test_mercadoria(self, d):
        assert d["pais_procedencia"] == "China"
        assert d["pais_aquisicao"] == "Hong Kong"
        assert d["peso_bruto"] == approx(18045.15)
        assert d["peso_liquido"] == approx(16188.48)
        assert "HONGKONG YESOP" in d["exportador"]
        assert "SHANGHAI YESOP" in d["fabricante"]


# ---------------------------------------------------------------------------
# DUIMP SY1453 (layout VMCV) — não pode quebrar o layout 1159
# ---------------------------------------------------------------------------
class TestDuimpSY1453:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return duimp.extrair(textos["duimp_sy1453"])

    def test_identificacao(self, d):
        assert d["numero"] == "26BR0000258971-1"
        assert d["versao"] == "0001"
        assert d["importador_cnpj"] == "53.203.621/0001-39"
        assert "ENCATEX" in d["importador_nome"]
        assert d["tipo_importacao"] == "Importação Direta"
        assert d["referencia"] == "SY1453/26"

    def test_valores_vmcv_e_cotacao(self, d):
        assert d["cotacao"] == approx(5.28)
        assert d["vmcv_usd"] == approx(52403.08)
        assert d["vmcv_reais"] == approx(276688.29)
        assert d["valor_aduaneiro_rs"] == approx(282232.29)

    def test_tributos(self, d):
        assert d["ii"] == approx(42114.64)
        assert d["ipi"] == approx(10873.77)
        assert d["pis"] == approx(6141.72)
        assert d["cofins"] == approx(29977.44)
        assert d["siscomex"] == approx(154.23)

    def test_reforma_e_itens(self, d):
        assert d["cclasstrib"] == "000001"
        assert d["ncm"] == "5907.0000"
        assert d["num_itens"] == 6
        # DUIMP não imprime CBS/IBS em valor (só cClassTrib)
        assert d["cbs"] is None


# ---------------------------------------------------------------------------
# NF de Importação 1159
# ---------------------------------------------------------------------------
class TestNotaFiscal1159:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return nota_fiscal.extrair(textos["nf1159"])

    def test_identificacao(self, d):
        assert d["numero"] == "000.000.769"
        assert d["serie"] == "001"
        assert d["emissao"] == "30/04/2026"
        assert d["emitente_cnpj"] == "57.345.180/0001-60"
        assert "ZINLOG" in d["emitente_nome"]
        assert "CMO" in d["destinatario_nome"]
        assert d["destinatario_cnpj"] == "42.435.597/0002-28"
        assert d["cfop"] == "5949"

    def test_valores(self, d):
        assert d["base_icms"] == approx(139663.65)
        assert d["icms"] == approx(5586.55)
        assert d["valor_produtos"] == approx(139663.65)
        assert d["ipi"] == approx(13617.20)
        assert d["valor_total"] == approx(153280.85)

    def test_complementares(self, d):
        assert d["chave"] == "42260457345180000160550010000007691435300822"
        assert d["processo"] == "Z028/26"
        assert d["pis_entrada"] == approx(1824.46)
        assert d["cofins_entrada"] == approx(8383.87)
        assert d["siscomex"] == approx(154.23)


# ---------------------------------------------------------------------------
# DI 870
# ---------------------------------------------------------------------------
class TestDi870:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return di.extrair(textos["di870"])

    def test_identificacao(self, d):
        assert d["numero"] == "25/2290426-3"
        assert d["data_registro"] == "13/10/2025"
        assert d["importador_cnpj"] == "24.545.851/0002-69"
        assert "INFINITY" in d["importador_nome"]
        assert d["adquirente_cnpj"] == "24.545.851/0002-69"
        assert d["representante"] == "JOSIANE IZING"
        assert d["adicoes"] == 7

    def test_valores_us(self, d):
        assert d["frete_us"] == approx(3415.00)
        assert d["vmle_us"] == approx(19214.12)
        assert d["vmld_us"] == approx(22629.08)

    def test_tributos(self, d):
        assert d["ii"] == approx(15679.92)
        assert d["ipi"] == approx(909.47)
        assert d["pis"] == approx(2587.33)
        assert d["cofins"] == approx(12752.27)
        assert d["siscomex"] == approx(331.62)
        assert d["total_tributos"] == approx(32260.61)

    def test_logistica_e_valores(self, d):
        assert d["referencia"] == "870#"
        assert d["bl"] == "SHYY25081848"
        assert d["navio"] == "EVER FAST"
        assert d["chegada"] == "01/10/25"
        assert d["armazem"] == "BRASKARNE"
        assert d["fatura"] == "YSPINFFBR870"
        assert d["cotacao"] == approx(5.4446)
        assert d["fob_rs"] == approx(104612.98)
        assert d["fob_us"] == approx(19214.08)
        assert d["frete_rs"] == approx(18593.31)
        assert d["valor_aduaneiro_rs"] == approx(123206.29)
        assert d["peso_bruto"] == approx(14653.78)
        assert d["peso_liquido"] == approx(13322.55)
        assert d["volumes"] == approx(876)


# ---------------------------------------------------------------------------
# Fechamento TERRA (870)
# ---------------------------------------------------------------------------
class TestFechamentoTerra:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return fechamento_terra.extrair(textos["terra"])

    def test_cabecalho(self, d):
        assert "TERRA" in d["despachante"]
        assert d["cnpj"] == "05.989.453/0001-06"
        assert d["cliente_cnpj"] == "24.545.851/0002-69"
        assert "INFINITY" in d["cliente_nome"]
        assert d["cod_interno"] == "1819"
        assert d["referencia"] == "870#"
        assert d["fatura"] == "YSPINFFBR870"
        assert d["origem"] == "SHANGHAI"
        assert d["destino"] == "NAVEGANTES"

    def test_despesas(self, d):
        mapa = {x["descricao"]: x["valor"] for x in d["despesas"]}
        assert mapa["TARIFA BANCARIA"] == approx(13.50)
        assert mapa["MOTO BOY"] == approx(20.00)
        assert mapa["AFRMM"] == approx(1595.46)
        assert mapa["ICMS"] == approx(1619.45)
        assert mapa["COMISSAO"] == approx(3000.00)
        assert mapa["FRETE MARITIMO"] == approx(3929.89)
        assert mapa["ARMAZENAGEM BRASKARNE"] == approx(3938.82)
        assert mapa["IMPOSTOS DI"] == approx(32260.61)
        assert mapa["ADIANTAMENTO"] == approx(45692.26)
        # cada despesa tem vencimento (dd/mm/aaaa)
        assert d["despesas"][0]["vencimento"] == "03/10/2025"

    def test_retencoes_e_saldo(self, d):
        assert d["retencoes"]["pis"] == approx(19.50)
        assert d["retencoes"]["cofins"] == approx(90.00)
        assert d["retencoes"]["csll"] == approx(30.00)
        assert d["retencoes"]["iss"] == approx(45.00)
        assert d["total_informativo"] == approx(46193.23)
        assert d["saldo"] == approx(500.97)


# ---------------------------------------------------------------------------
# Fechamento WIN TRADING (ENC-153/2024.1)
# ---------------------------------------------------------------------------
class TestFechamentoWin:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return fechamento_win.extrair(textos["win"])

    def test_cabecalho(self, d):
        assert "WIN" in d["trading"]
        assert d["cnpj"] == "26.316.473/0002-77"
        assert d["processo"] == "ENC-153/2024.1"
        assert d["modalidade"] == "Conta e ordem"
        assert d["incoterm"] == "FOB"
        assert d["adquirente"] == "EQUIPMAX BRASIL"
        assert d["ref_adquirente"] == "ESC-2404-F139"
        assert d["exportador"] == "HANGZHOU EQUIPMAX INDUSTRIES CO., LTD"
        assert d["declaracao"] == "24/2793486-0"
        assert d["data_registro"] == "19/12/2024"
        assert d["cotacao"] == approx(6.16240114)

    def test_valores(self, d):
        assert d["fob"] == approx(479126.69)
        assert d["frete"] == approx(44677.41)
        assert d["seguro"] == approx(785.71)
        assert d["valor_aduaneiro"] == approx(524589.81)
        assert d["total"] == approx(640334.70)
        assert d["retencoes"] == approx(194.86)

    def test_despesas(self, d):
        mapa = {x["descricao"]: x["valor"] for x in d["despesas"]}
        assert mapa["AFRMM"] == approx(3658.67)
        assert mapa["Armazenagem"] == approx(9123.85)
        assert mapa["Frete internacional"] == approx(50483.61)


# ---------------------------------------------------------------------------
# NF de Importação SY1453 — Reforma Tributária (CBS/IBS na NF, não na DUIMP)
# ---------------------------------------------------------------------------
class TestNotaFiscalSY1453:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return nota_fiscal.extrair(textos["nf_sy1453"])

    def test_identificacao(self, d):
        assert d["numero"] == "000.002.411"
        assert d["serie"] == "001"
        assert d["cfop"] == "3102"  # importação direta
        assert d["chave"] == "42260353203621000139550010000024111153675423"

    def test_valores(self, d):
        assert d["valor_produtos"] == approx(292461.18)
        assert d["valor_total"] == approx(382358.58)

    def test_reforma(self, d):
        assert d["cbs"] == approx(3018.30)   # "R$ 3.018,3" (1 casa)
        assert d["ibs_uf"] == approx(273.57)
        assert d["ibs_mun"] == approx(0.00)


# ---------------------------------------------------------------------------
# Fechamento SYNDEX (SY1453)
# ---------------------------------------------------------------------------
class TestFechamentoSyndex:
    @pytest.fixture(scope="class")
    def d(self, textos):
        return fechamento_syndex.extrair(textos["syndex_fechamento"])

    def test_identificacao(self, d):
        assert d["subtipo"] == "fechamento"
        assert d["cnpj"] == "02.286.106/0002-00"
        assert "SYNDEX" in d["despachante"]
        assert d["referencia"] == "SY1453/26"

    def test_totais_e_saldo(self, d):
        assert d["total_debitos"] == approx(103736.87)
        assert d["total_creditos"] == approx(103834.93)
        assert d["saldo"] == approx(98.06)

    def test_despesas_e_bancarios(self, d):
        assert len(d["despesas"]) >= 11
        mapa = {x["descricao"]: x["valor"] for x in d["despesas"]}
        assert mapa["IMPOSTO DE IMPORTAÇÃO"] == approx(42114.64)
        assert mapa["ARMAZENAGEM"] == approx(7352.40)
        assert mapa["AFRMM - MARINHA MERCANTE"] == approx(635.58)
        assert d["banco"] == "SANTANDER"
        assert d["agencia"] == "3159"
        assert d["conta"] == "13005676-6"

    def test_creditos_incluem_adiantamento(self, d):
        descr = [c["descricao"] for c in d["creditos"]]
        assert any("ADIANTAMENTO" in x for x in descr)


class TestNumerarioSyndex:
    def test_subtipo_numerario(self, textos):
        d = fechamento_syndex.extrair(textos["syndex_numerario"])
        assert d["subtipo"] == "numerario"
        assert d["total_debitos"] == approx(101645.23)


# ---------------------------------------------------------------------------
# Tolerância: documento vazio/irreconhecível não deve quebrar
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "mod", [duimp, di, nota_fiscal, fechamento_terra, fechamento_win, fechamento_syndex]
)
def test_extrator_tolera_texto_vazio(mod):
    resultado = mod.extrair("")
    assert isinstance(resultado, dict)
