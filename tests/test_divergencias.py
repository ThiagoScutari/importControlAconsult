"""Item 8 [F1-08]: conferência navegável — divergências estruturadas.

A consolidação guarda TODOS os candidatos (fonte+valor) de cada campo em conflito,
não só o escolhido, para o operador decidir na conferência (spec §3 [R2]/[R3]).
"""
from backend.consolidador import consolidar
from backend.extractors import duimp, fechamento_syndex, nota_fiscal


def test_divergencias_guardam_candidatos(textos):
    docs = [
        duimp.extrair(textos["duimp_sy1453"]),
        nota_fiscal.extrair(textos["nf_sy1453"]),
        fechamento_syndex.extrair(textos["syndex_fechamento"]),
    ]
    p = consolidar(docs)
    campos = {d.campo for d in p.divergencias}
    # o caso SY1453 diverge em importador_nome (NF sem "LTDA") e em icms (fech x NF)
    assert "importador_nome" in campos
    assert "icms" in campos

    icms = next(d for d in p.divergencias if d.campo == "icms")
    fontes = {c["fonte"] for c in icms.candidatos}
    assert {"NF", "Fechamento"} <= fontes          # todos os candidatos preservados
    assert len(icms.candidatos) >= 2
    assert icms.escolhido_fonte == "NF"            # prioridade; operador pode trocar

    # divergência não vira mais aviso plano (substituída pela navegação)
    assert not any(a.tipo == "divergencia" for a in p.avisos)
