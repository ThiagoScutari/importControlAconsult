"""Testes do motor de partidas (contabilizador) sobre o processo SY1453.

Firmes: estrutura das partidas e invariante de balanceamento.
xfail: valores que dependem de conferência contábil da Larissa (brief §4/§7).
"""
import pytest

from backend.consolidador import consolidar
from backend.contabilizador import (
    gerar_partidas,
    lotes_balanceiam,
    montar_nome_conta_processo,
)
from backend.depara import PapelConta, codigo_conta
from backend.extractors import duimp, fechamento_syndex, nota_fiscal
from backend.models import MiddlewareInput


@pytest.fixture
def proc_sy1453(textos):
    docs = [
        duimp.extrair(textos["duimp_sy1453"]),
        nota_fiscal.extrair(textos["nf_sy1453"]),
        fechamento_syndex.extrair(textos["syndex_fechamento"]),
    ]
    return consolidar(docs)


@pytest.fixture
def middleware():
    # de-para POR EMPRESA: [R3] conta do processo/fornecedor não têm mais default
    # hardcoded — o operador as informa (aqui, semeadas). Sem elas, as partidas
    # dos Passos 5/6.2 são bloqueadas (ver test_conta_em_branco_bloqueia_partida).
    return MiddlewareInput(
        data_lancamento="31/03/2026",
        contas_override={
            PapelConta.CONTA_PROCESSO.value: "1648",
            PapelConta.FORNECEDOR_ESTRANGEIRO.value: "1177",
            PapelConta.ADIANTAMENTO_DESPACHANTE.value: "9101",
            PapelConta.BANCO.value: "1",
        },
    )


class TestMotorEstrutura:
    def test_passo5_partida2_valor_devido(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p52 = [l for l in parts if l.passo == "5.2"]
        ovr = middleware.contas_override
        assert len(p52) == 1
        assert p52[0].conta_debito == codigo_conta(PapelConta.CONTA_PROCESSO, ovr)      # 1648 (de-para)
        assert p52[0].conta_credito == codigo_conta(PapelConta.FORNECEDOR_ESTRANGEIRO, ovr)  # 1177 (de-para)
        assert p52[0].valor == pytest.approx(276688.26, abs=0.01)
        assert "VALOR DEVIDO FORNECEDOR" in p52[0].complemento_historico

    def test_passo51_default_total_nf(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p51 = [l for l in parts if l.passo == "5.1"]
        assert len(p51) == 1
        assert p51[0].conta_debito == codigo_conta(PapelConta.IMPORTACOES_EM_ANDAMENTO)  # 1633
        # default documentado = valor total da NF
        assert p51[0].valor == pytest.approx(382358.58, abs=0.01)

    def test_passo62_so_despesas_processo(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p62 = [l for l in parts if l.passo == "6.2"]
        # guard §3: default classifica 4 linhas como despesa_processo
        # (COMISSÃO, ARMAZENAGEM, SEGURO, DESPESAS BANCÁRIAS); tributos federais
        # e ICMS ficam de fora (já entram pela NF no Passo 5).
        descrs = [l.complemento_historico for l in p62]
        assert len(p62) == 4
        assert all(l.conta_debito == codigo_conta(PapelConta.CONTA_PROCESSO, middleware.contas_override) for l in p62)
        soma = sum(l.valor for l in p62)
        assert soma == pytest.approx(9856.61, abs=0.01)
        # nenhum tributo federal recontabilizado
        assert not any("IMPOSTO DE IMPORTA" in d.upper() for d in descrs)

    def test_guard_nao_recontabiliza_tributos(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p62 = [l for l in parts if l.passo == "6.2"]
        soma_62 = sum(l.valor for l in p62)
        # muito menor que os ~103 mil brutos do fechamento
        assert soma_62 < 20000

    def test_invariante_balanceamento(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        assert parts, "motor não gerou partidas"
        assert lotes_balanceiam(parts)
        # nenhuma partida com valor zero silencioso
        assert all(l.valor > 0 for l in parts)

    def test_cambio_ausente_gera_aviso(self, proc_sy1453, middleware):
        gerar_partidas(proc_sy1453, middleware)
        assert any("câmbio" in a.mensagem.lower() for a in proc_sy1453.avisos)

    def test_papel_sem_codigo_gera_aviso(self, proc_sy1453):
        # sem override: adiantamento_despachante não tem código no de-para
        gerar_partidas(proc_sy1453, MiddlewareInput())
        assert any("adiantamento_despachante" in a.campo or "adiantamento_despachante" in a.mensagem
                   for a in proc_sy1453.avisos)

    def test_conta_em_branco_bloqueia_partida(self, proc_sy1453):
        # spec §1.4 [R3]: sem de-para, conta do processo/fornecedor ficam em branco →
        # as partidas dos Passos 5/6.2 NÃO são geradas e sai aviso de "conta obrigatória".
        parts = gerar_partidas(proc_sy1453, MiddlewareInput())
        assert not any(l.passo in ("5.1", "5.2", "6.2") for l in parts)
        assert any("não preenchida" in a.mensagem for a in proc_sy1453.avisos)

    def test_nome_conta_processo(self, proc_sy1453):
        nome = montar_nome_conta_processo(proc_sy1453)
        assert nome.startswith("PROCESSO")
        assert "26BR0000258971-1" in nome
        assert "NF 2411" in nome  # [R3] inteiro limpo, não "000.002.411"


class TestMotorCambio:
    def test_passo8_com_cambio_gera_variacao(self, proc_sy1453):
        # operador informa contrato de câmbio: paga 52.403,08 USD a 5,10.
        # de-para: fornecedor preenchido (sem ele o Passo 8 seria bloqueado — [R3]).
        ovr = {PapelConta.FORNECEDOR_ESTRANGEIRO.value: "1177"}
        mid = MiddlewareInput(vlr_usd_pg_cambio=52403.08, tx_cambio=5.10, contas_override=ovr)
        parts = gerar_partidas(proc_sy1453, mid)
        p8 = [l for l in parts if l.passo == "8"]
        assert len(p8) == 1
        # [R3] variação = 6 − 7: pagou a 5,10 (< tx_di 5,28) => campo6 < campo7 =>
        # X negativo => variação PASSIVA (D 370 · C fornecedor).
        assert p8[0].conta_debito == codigo_conta(PapelConta.VARIACAO_CAMBIAL_PASSIVA)
        assert p8[0].conta_credito == codigo_conta(PapelConta.FORNECEDOR_ESTRANGEIRO, ovr)
        assert lotes_balanceiam(parts)


# ---------------------------------------------------------------------------
# xfail — decisões contábeis pendentes de conferência da Larissa (brief §7)
# ---------------------------------------------------------------------------
class TestPendenteLarissa:
    @pytest.mark.xfail(reason="aguardando Larissa: Passo 5.1 usa total da NF ou valor dos produtos?")
    def test_passo51_valor_produtos(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p51 = [l for l in parts if l.passo == "5.1"][0]
        # alternativa (produtos) — default atual é total da NF, então falha
        assert p51.valor == pytest.approx(292461.18, abs=0.01)

    @pytest.mark.xfail(reason="aguardando Larissa: ICMS entra no Passo 6.2? (5 linhas / 13.839,49)")
    def test_passo62_inclui_icms(self, proc_sy1453, middleware):
        parts = gerar_partidas(proc_sy1453, middleware)
        p62 = [l for l in parts if l.passo == "6.2"]
        assert len(p62) == 5
        assert sum(l.valor for l in p62) == pytest.approx(13839.49, abs=0.01)
