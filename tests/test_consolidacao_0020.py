"""Chave de consolidação multi-arquivo do processo 0020-26 (CONNECTA).

Garante que, quando o fechamento CONNECTA e a declaração/NF do MESMO processo são
consolidados, o merge costura por ``referencia="0020-26"`` e ambos contribuem
(câmbio + despesas do fechamento; cabeçalho da declaração), sem um sobrescrever o
outro. Também cobre o item 2: os tributos vêm da DECLARAÇÃO quando ela existe e do
FECHAMENTO como fallback quando não existe.

O corpus só tem o dossiê combinado (não há NF-e/DUIMP avulsas do 0020-26), então o
teste roda no nível do ``consolidar()`` com o dict real do fechamento + um dict
mínimo simulando a declaração. O end-to-end multi-arquivo fica como xfail explícito.
"""
import pytest

from backend.consolidador import consolidar
from backend.detector import TipoDocumento
from backend.extractors import fechamento_connecta

# Valores da declaração real (Extrato da Duimp do 0020-26, pág. 3 do dossiê).
_DECLARACAO = {
    "tipo": TipoDocumento.DUIMP.value,
    "processo": "0020-26",
    "referencia": "0020-26",
    "numero": "26BR0000775592-0",
    "importador_cnpj": "15.066.508/0001-60",
    "ii": 25606.96,
    "ipi": 2413.46,
    "pis": 4289.17,
    "cofins": 19765.37,
    "siscomex": 154.23,
}
_TRIBUTOS = {"ii": 25606.96, "ipi": 2413.46, "pis": 4289.17, "cofins": 19765.37, "siscomex": 154.23}


@pytest.fixture(scope="module")
def fechamento(textos):
    d = fechamento_connecta.extrair(textos["connecta"])
    d["_arquivo"] = "0020-26.pdf"
    return d


def _fonte(p, campo):
    """Fonte registrada no rastreamento para ``campo`` (ou None)."""
    for r in p.rastreamento:
        if r["campo"] == campo:
            return r["fonte"]
    return None


class TestConsolidacaoMultiArquivo:
    def test_merge_unico_por_referencia(self, fechamento):
        p = consolidar([fechamento, dict(_DECLARACAO)])
        # consolidar sempre devolve UM ProcessoExtraido (não dois)
        assert p.processo == "0020-26"
        # cabeçalho vem da declaração...
        assert p.di_duimp == "26BR0000775592-0"
        assert p.importador_cnpj == "15.066.508/0001-60"
        # ...e câmbio + despesas vêm do fechamento (nenhum sobrescreve o outro)
        assert len(p.despesas) == 16
        assert p.fob_rs == 147387.79
        assert p.frete_rs == 12575.75
        assert p.valor_aduaneiro_rs == 160043.52

    def test_precedencia_declaracao_autoritativa(self, fechamento):
        p = consolidar([fechamento, dict(_DECLARACAO)])
        for campo, valor in _TRIBUTOS.items():
            assert getattr(p, campo) == valor
            # com a declaração presente, a fonte é a DUIMP, não o Fechamento
            assert _fonte(p, campo) == "DUIMP"

    def test_fallback_so_fechamento(self, fechamento):
        p = consolidar([fechamento])
        for campo, valor in _TRIBUTOS.items():
            assert getattr(p, campo) == valor
            assert _fonte(p, campo) == "Fechamento"
        # total_tributos somado no fallback (bate com o total impresso na DUIMP)
        assert p.total_tributos == 52229.19
        # AFRMM e ICMS também presentes a partir do fechamento
        assert p.afrmm == 1114.05
        assert p.icms == 2222.77

    def test_sem_obrigatoria_ausente_ambos(self, fechamento):
        for docs in ([fechamento], [fechamento, dict(_DECLARACAO)]):
            p = consolidar(docs)
            ausentes = [a for a in p.avisos if a.tipo == "despesa_obrigatoria_ausente"]
            assert ausentes == []


@pytest.mark.xfail(
    reason="end-to-end multi-arquivo do 0020-26 pendente de NF/DUIMP standalone no "
           "corpus (só há o dossiê combinado; não splitar o PDF nesta tarefa)",
    strict=False,
)
def test_e2e_multiarquivo_standalone():
    """Placeholder: quando o corpus ganhar a NF-e e a DUIMP avulsas do 0020-26,
    trocar por extract → detectar_tipo → extrair → consolidar dos N arquivos reais."""
    raise NotImplementedError("NF/DUIMP standalone do 0020-26 ausentes no corpus")
