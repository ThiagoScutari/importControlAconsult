"""Testes dos helpers de extração de texto e parsing BR."""
import os

from backend.pdf_utils import extract_text, parse_valor_br


class TestParseValorBR:
    def test_milhar_com_decimal(self):
        assert parse_valor_br("1.234,56") == 1234.56

    def test_valor_grande(self):
        assert parse_valor_br("153.280,85") == 153280.85

    def test_cotacao_com_muitas_casas(self):
        assert parse_valor_br("5,0899") == 5.0899

    def test_com_prefixo_reais(self):
        assert parse_valor_br("R$ 15.638,31") == 15638.31

    def test_zeros_a_direita(self):
        # Caso real da DUIMP: "17069,00000000..."
        assert parse_valor_br("17069,00000000000000") == 17069.0

    def test_inteiro_sem_decimal(self):
        assert parse_valor_br("965") == 965.0

    def test_vazio_retorna_none(self):
        assert parse_valor_br("") is None
        assert parse_valor_br(None) is None
        assert parse_valor_br("   ") is None

    def test_texto_sem_numero_retorna_none(self):
        assert parse_valor_br("ISENTO") is None


class TestExtractText:
    def test_extrai_texto_com_acentos_corretos(self, asset_files):
        texto = extract_text(asset_files["duimp1159"])
        # Âncora chave e acentuação preservada (UTF-8, não mojibake)
        assert "Extrato da Duimp" in texto
        assert "26BR0000380790-9" in texto
        assert "Situação" in texto

    def test_aceita_bytes(self, asset_files):
        with open(asset_files["di870"], "rb") as fh:
            dados = fh.read()
        texto = extract_text(dados)
        assert "EXTRATO DA DECLARA" in texto.upper()
