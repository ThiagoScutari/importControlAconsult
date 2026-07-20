"""Testes do fechamento CONNECTA (layout FATURAMENTO) — corpus 0020-26.

O PDF é um dossiê único (faturamento + Extrato da Duimp + NFS-e/anexos). Antes,
o "EXTRATO DA DUIMP" embutido roteava o arquivo para o parser DUIMP e as despesas
da pág. 1 sumiam. Estes testes pinam a detecção correta, os 16 lançamentos e a
reconciliação com o TOTAL/SALDO/numerário impressos.
"""
import pytest

from backend.consolidador import consolidar
from backend.detector import TipoDocumento, detectar_tipo
from backend.extractors import fechamento_connecta


@pytest.fixture(scope="module")
def texto(textos):
    return textos["connecta"]


@pytest.fixture(scope="module")
def dados(texto):
    return fechamento_connecta.extrair(texto)


def _por_chave(despesas, chave):
    """Valor da 1ª despesa cuja descrição contém ``chave`` (case-insensitive)."""
    for d in despesas:
        if chave.upper() in d["descricao"].upper():
            return d["valor"]
    return None


class TestConnecta:
    def test_detecta_connecta_nao_duimp(self, texto):
        assert detectar_tipo(texto) == TipoDocumento.FECHAMENTO_CONNECTA

    def test_qtde_despesas(self, dados):
        assert len(dados["despesas"]) == 16

    def test_soma_despesas_bate_total(self, dados):
        soma = round(sum(d["valor"] for d in dados["despesas"]), 2)
        assert soma == 74822.33
        assert dados["total"] == 74822.33

    def test_saldo_e_adiantamento(self, dados):
        assert dados["saldo"] == 4105.00
        assert dados["adiantamento_total"] == 78927.33

    def test_reconciliacao_numerario(self, dados):
        # (adiantamento − total) == saldo
        assert round(dados["adiantamento_total"] - dados["total"], 2) == dados["saldo"]

    def test_bloco_cambio(self, dados):
        assert dados["taxa_cambial"] == 5.0303
        assert dados["fob"] == 147387.79
        assert dados["frete"] == 12575.75
        assert dados["seguro"] == 79.98
        assert dados["valor_aduaneiro"] == 160043.52

    def test_valores_chave(self, dados):
        desp = dados["despesas"]
        assert _por_chave(desp, "AFRMM") == 1114.05
        assert _por_chave(desp, "Imposto de Importação") == 25606.96
        assert _por_chave(desp, "Produtos Industrializados") == 2413.46  # IPI
        assert _por_chave(desp, "Pis/Pasep") == 4289.17
        assert _por_chave(desp, "Cofins") == 19765.37
        assert _por_chave(desp, "Siscomex") == 154.23
        assert _por_chave(desp, "ICMS") == 2222.77
        assert _por_chave(desp, "Frete Maritimo") == 16647.79
        assert _por_chave(desp, "Armazenagem") == 1000.00  # 1º período (1ª ocorrência)
        assert _por_chave(desp, "Despacho") == 850.00
        assert _por_chave(desp, "Emissão LI") == 50.00
        assert _por_chave(desp, "Licença") == 53.53

    def test_despachante_cnpj(self, dados):
        assert "CONNECTA" in dados["despachante"].upper()
        assert dados["cnpj"] == "42.929.006/0001-98"

    def test_consolidar_sem_obrigatoria_ausente(self, texto):
        d = fechamento_connecta.extrair(texto)
        d["_arquivo"] = "0020-26.pdf"
        p = consolidar([d])
        ausentes = [a for a in p.avisos if a.tipo == "despesa_obrigatoria_ausente"]
        assert ausentes == []
