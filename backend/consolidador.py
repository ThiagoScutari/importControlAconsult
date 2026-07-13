"""Consolida vários documentos extraídos em um único :class:`ProcessoExtraido`.

Regras (seção 5):
- Chave do processo = referência (``1159#``); se ausente, nº da DI/DUIMP.
- Em conflito de valor, mantém o documento de maior prioridade:
  DUIMP/DI > NF > Fechamento, registrando o divergente em ``avisos``.
- Extração crua: não concilia, apenas sinaliza.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from backend.models import Aviso, ProcessoExtraido

# Campos cuja ausência merece um aviso visível (evita poluir com 30 mensagens).
_CRITICOS = {"di_duimp", "numero_nf", "valor_nf", "fornecedor_estrangeiro", "processo"}


def _primeiro(por_tipo: Dict[str, list], tipo: str) -> Optional[dict]:
    docs = por_tipo.get(tipo)
    return docs[0] if docs else None


def _syndex_preferido(por_tipo: Dict[str, list]) -> Optional[dict]:
    """Entre os documentos SYNDEX, prefere o fechamento real ao numerário."""
    docs = por_tipo.get("fechamento_syndex") or []
    if not docs:
        return None
    reais = [d for d in docs if d.get("subtipo") == "fechamento"]
    return reais[0] if reais else docs[0]


def _difere(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) > 0.01
    return str(a).strip() != str(b).strip()


def _despesa_valor(fechamento: Optional[dict], keyword: str) -> Optional[float]:
    if not fechamento:
        return None
    for item in fechamento.get("despesas", []):
        if keyword in str(item.get("descricao", "")).upper():
            return item.get("valor")
    return None


def consolidar(documentos: List[dict]) -> ProcessoExtraido:
    por_tipo: Dict[str, list] = {}
    for doc in documentos:
        por_tipo.setdefault(doc.get("tipo"), []).append(doc)

    duimp = _primeiro(por_tipo, "duimp")
    di = _primeiro(por_tipo, "di")
    nf = _primeiro(por_tipo, "nota_fiscal")
    terra = _primeiro(por_tipo, "fechamento_terra")
    win = _primeiro(por_tipo, "fechamento_win")
    syndex = _syndex_preferido(por_tipo)
    declaracao = duimp or di
    fechamento = terra or win or syndex

    avisos: List[Aviso] = []
    rastreamento: List[Dict] = []

    def g(doc, campo):
        return doc.get(campo) if doc else None

    def pega(campo: str, candidatos: list):
        """candidatos = [(fonte, valor), ...] em ordem de prioridade."""
        escolhido = None
        fonte_escolhida = None
        for fonte, valor in candidatos:
            if valor in (None, ""):
                continue
            if escolhido is None:
                escolhido = valor
                fonte_escolhida = fonte
                rastreamento.append({"campo": campo, "valor": valor, "fonte": fonte})
            elif _difere(valor, escolhido):
                avisos.append(
                    Aviso(
                        tipo="divergencia",
                        campo=campo,
                        mensagem=f"{campo}: {fonte}={valor} difere de {fonte_escolhida}={escolhido}",
                    )
                )
        if escolhido is None and campo in _CRITICOS:
            avisos.append(
                Aviso(tipo="ausente", campo=campo, mensagem=f"{campo} não encontrado nos documentos")
            )
        return escolhido

    # Chave do processo
    ref = g(declaracao, "referencia") or g(fechamento, "referencia")
    if ref:
        processo = str(ref).rstrip("#")
    else:
        processo = g(declaracao, "numero") or g(nf, "processo")

    p = ProcessoExtraido(
        processo=processo,
        tipo_importacao=pega("tipo_importacao", [("DUIMP", g(duimp, "tipo_importacao")), ("WIN", g(win, "modalidade"))]),
        di_duimp=pega("di_duimp", [("DUIMP", g(duimp, "numero")), ("DI", g(di, "numero"))]),
        data_nf=pega("data_nf", [("NF", g(nf, "emissao"))]),
        numero_nf=pega("numero_nf", [("NF", g(nf, "numero"))]),
        valor_nf=pega("valor_nf", [("NF", g(nf, "valor_total"))]),
        chave_nfe=pega("chave_nfe", [("NF", g(nf, "chave"))]),
        importador_nome=pega("importador_nome", [("DUIMP", g(duimp, "importador_nome")), ("DI", g(di, "importador_nome")), ("NF", g(nf, "emitente_nome"))]),
        importador_cnpj=pega("importador_cnpj", [("DUIMP", g(duimp, "importador_cnpj")), ("DI", g(di, "importador_cnpj")), ("NF", g(nf, "emitente_cnpj"))]),
        adquirente_nome=pega("adquirente_nome", [("DI", g(di, "adquirente_nome")), ("WIN", g(win, "adquirente"))]),
        adquirente_cnpj=pega("adquirente_cnpj", [("DI", g(di, "adquirente_cnpj"))]),
        despachante=pega("despachante", [("TERRA", g(terra, "despachante")), ("WIN", g(win, "trading")), ("SYNDEX", g(syndex, "despachante")), ("ALLTIME", g(alltime, "despachante"))]),
        fornecedor_estrangeiro=pega("fornecedor_estrangeiro", [("DUIMP", g(duimp, "exportador")), ("WIN", g(win, "exportador"))]),
        fabricante=pega("fabricante", [("DUIMP", g(duimp, "fabricante"))]),
        pais_origem=pega("pais_origem", [("DUIMP", g(duimp, "pais_procedencia"))]),
        pais_aquisicao=pega("pais_aquisicao", [("DUIMP", g(duimp, "pais_aquisicao"))]),
        invoice=pega("invoice", [("DUIMP", g(duimp, "fatura_numero")), ("DI", g(di, "fatura"))]),
        invoice_usd=pega("invoice_usd", [("DUIMP", g(duimp, "fatura_valor_us"))]),  # campo 1
        cotacao=pega("cotacao", [("DUIMP", g(duimp, "cotacao")), ("DI", g(di, "cotacao")), ("WIN", g(win, "cotacao"))]),
        tx_di=pega("tx_di", [("DUIMP", g(duimp, "cotacao")), ("DI", g(di, "cotacao"))]),  # campo 2
        cbs=pega("cbs", [("NF", g(nf, "cbs"))]),
        ibs_uf=pega("ibs_uf", [("NF", g(nf, "ibs_uf"))]),
        ibs_mun=pega("ibs_mun", [("NF", g(nf, "ibs_mun"))]),
        cclasstrib=pega("cclasstrib", [("DUIMP", g(duimp, "cclasstrib"))]),
        fob_rs=pega("fob_rs", [("DUIMP", g(duimp, "fob_rs")), ("DI", g(di, "fob_rs")), ("WIN", g(win, "fob"))]),
        frete_rs=pega("frete_rs", [("DUIMP", g(duimp, "frete_rs")), ("DI", g(di, "frete_rs")), ("WIN", g(win, "frete"))]),
        valor_aduaneiro_rs=pega("valor_aduaneiro_rs", [("DUIMP", g(duimp, "valor_aduaneiro_rs")), ("DI", g(di, "valor_aduaneiro_rs")), ("WIN", g(win, "valor_aduaneiro"))]),
        ii=pega("ii", [("DUIMP", g(duimp, "ii")), ("DI", g(di, "ii"))]),
        ipi=pega("ipi", [("DUIMP", g(duimp, "ipi")), ("DI", g(di, "ipi")), ("NF", g(nf, "ipi"))]),
        pis=pega("pis", [("DUIMP", g(duimp, "pis")), ("DI", g(di, "pis")), ("NF", g(nf, "pis_entrada"))]),
        cofins=pega("cofins", [("DUIMP", g(duimp, "cofins")), ("DI", g(di, "cofins")), ("NF", g(nf, "cofins_entrada"))]),
        siscomex=pega("siscomex", [("DUIMP", g(duimp, "siscomex")), ("DI", g(di, "siscomex")), ("NF", g(nf, "siscomex"))]),
        afrmm=pega("afrmm", [("Fechamento", _despesa_valor(fechamento, "AFRMM"))]),
        icms=pega("icms", [("NF", g(nf, "icms")), ("Fechamento", _despesa_valor(fechamento, "ICMS"))]),
        armazenagem=pega("armazenagem", [("Fechamento", _despesa_valor(fechamento, "ARMAZENAGEM"))]),
        total_tributos=pega("total_tributos", [("DUIMP", g(duimp, "total_tributos")), ("DI", g(di, "total_tributos"))]),
        peso_liquido=pega("peso_liquido", [("DUIMP", g(duimp, "peso_liquido")), ("DI", g(di, "peso_liquido"))]),
        volumes=pega("volumes", [("DUIMP", g(duimp, "volumes")), ("DI", g(di, "volumes"))]),
        navio=pega("navio", [("DUIMP", g(duimp, "navio")), ("DI", g(di, "navio")), ("TERRA", g(terra, "navio"))]),
        bl=pega("bl", [("DUIMP", g(duimp, "bl")), ("DI", g(di, "bl"))]),
        chegada=pega("chegada", [("DUIMP", g(duimp, "chegada")), ("DI", g(di, "chegada"))]),
        adiantamento_total=pega("adiantamento_total", [
            ("TERRA", g(terra, "adiantamento_total")), ("WIN", g(win, "adiantamento_total")),
            ("SYNDEX", g(syndex, "adiantamento_total")), ("ALLTIME", g(alltime, "adiantamento_total")),
        ]),
        documentos=list(documentos),
        despesas=list(fechamento.get("despesas", [])) if fechamento else [],
        adiantamentos=list(fechamento.get("adiantamentos", [])) if fechamento else [],
        avisos=avisos,
        divergencias=divergencias,
        rastreamento=rastreamento,
    )

    # Campo 3 (RESULTADO R$) = invoice US$ × TX DI — provisão do fornecedor
    # (não é o valor da NF nem o aduaneiro; spec §1.3). Só quando ambos existem.
    if p.invoice_usd is not None and p.tx_di is not None:
        p.resultado_rs = round(p.invoice_usd * p.tx_di, 2)

    return p
