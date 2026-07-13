"""Geração dos arquivos de saída (seção 7).

- Saída A: extração estruturada (1 linha por processo) + versão rastreável.
- Saída B: lançamentos no layout Domínio (10 colunas, ``;``, sem cabeçalho).
- Saída C: cadastro de fornecedor (bônus).
"""
from __future__ import annotations

import csv
import io
from typing import List, Optional

from backend.depara import sugerir_despesa, sugerir_fornecedor
from backend.models import Lancamento, MiddlewareInput, ProcessoExtraido

# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def fmt_br(valor, casas: int = 2) -> str:
    """Formata número no padrão BR com separador de milhar (uso humano)."""
    if valor is None or valor == "":
        return ""
    if isinstance(valor, (int, float)):
        s = f"{valor:,.{casas}f}"  # 1,234.56
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    return str(valor)


def fmt_dominio(valor) -> str:
    """Valor no formato aceito pela macro do Domínio (vírgula decimal, sem milhar)."""
    if valor is None or valor == "":
        return ""
    if isinstance(valor, (int, float)):
        return f"{valor:.2f}".replace(".", ",")
    return str(valor)


def _writer(linhas: List[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    for linha in linhas:
        w.writerow(linha)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Saída A — extração estruturada
# ---------------------------------------------------------------------------

# Layout v0.2 (spec §6.1): inclui as colunas 1–8 da planilha de controle
# (câmbio) e os campos da Reforma (CBS/IBS-UF/IBS-MUN).
COLUNAS_A = [
    "Tipo Importação", "Data NF", "DI/DUIMP", "Nº NF", "Valor NF", "Processo",
    "Despachante", "Fornecedor Estrangeiro", "Fabricante", "País Origem",
    "País Aquisição", "Invoice", "Invoice USD", "TX DI", "Resultado R$",
    "USD PG Câmbio", "TX Câmbio", "VLR PG R$", "VLR PG × TX DI", "Variação",
    "FOB R$", "Frete R$", "Valor Aduaneiro R$", "II", "IPI", "PIS", "COFINS",
    "CBS", "IBS-UF", "IBS-MUN", "Siscomex", "AFRMM", "ICMS", "Armazenagem",
    "Total Tributos", "Peso Líquido", "Volumes", "Navio", "BL", "Chave NF-e",
]


def _linha_a(p: ProcessoExtraido) -> list:
    return [
        p.tipo_importacao or "", p.data_nf or "", p.di_duimp or "", p.numero_nf or "",
        fmt_br(p.valor_nf), p.processo or "", p.despachante or "",
        p.fornecedor_estrangeiro or "", p.fabricante or "", p.pais_origem or "",
        p.pais_aquisicao or "", p.invoice or "", fmt_br(p.invoice_usd),
        fmt_br(p.tx_di, casas=4), fmt_br(p.resultado_rs),
        fmt_br(p.vlr_usd_pg_cambio), fmt_br(p.tx_cambio, casas=4), fmt_br(p.vlr_pg_rs),
        fmt_br(p.vlr_pg_x_tx_di), fmt_br(p.variacao),
        fmt_br(p.fob_rs), fmt_br(p.frete_rs), fmt_br(p.valor_aduaneiro_rs),
        fmt_br(p.ii), fmt_br(p.ipi), fmt_br(p.pis), fmt_br(p.cofins),
        fmt_br(p.cbs), fmt_br(p.ibs_uf), fmt_br(p.ibs_mun),
        fmt_br(p.siscomex), fmt_br(p.afrmm), fmt_br(p.icms), fmt_br(p.armazenagem),
        fmt_br(p.total_tributos), fmt_br(p.peso_liquido), fmt_br(p.volumes),
        p.navio or "", p.bl or "", p.chave_nfe or "",
    ]


def gerar_saida_a(processos: List[ProcessoExtraido]) -> str:
    """CSV com cabeçalho e uma linha por processo."""
    return _writer([COLUNAS_A] + [_linha_a(p) for p in processos])


def gerar_saida_a_rastreavel(processos: List[ProcessoExtraido]) -> str:
    """Formato longo (auditoria): Processo;Documento;Campo;Valor;Fonte."""
    linhas = [["Processo", "Documento", "Campo", "Valor", "Fonte"]]
    for p in processos:
        for r in p.rastreamento:
            valor = r.get("valor")
            linhas.append([
                p.processo or "",
                r.get("fonte", ""),
                r.get("campo", ""),
                fmt_br(valor) if isinstance(valor, (int, float)) else (valor or ""),
                r.get("fonte", ""),
            ])
    return _writer(linhas)


# ---------------------------------------------------------------------------
# Saída B — lançamentos Domínio (10 colunas, sem cabeçalho)
# ---------------------------------------------------------------------------

def gerar_saida_b(lancamentos: List[Lancamento]) -> str:
    """Layout idêntico à macro Sub Gerar(): 10 colunas ``;`` sem cabeçalho."""
    linhas = []
    for l in lancamentos:
        linhas.append([
            l.data, l.conta_debito, l.conta_credito, fmt_dominio(l.valor),
            l.cod_historico, l.complemento_historico, l.inicia_lote,
            l.matriz_filial, l.cc_debito, l.cc_credito,
        ])
    return _writer(linhas)


def gerar_lancamentos_sugeridos(p: ProcessoExtraido, m: MiddlewareInput) -> List[Lancamento]:
    """Monta partidas a partir das despesas do fechamento + de-para + middleware.

    Heurística do mockup: uma partida por despesa, com contas/histórico
    pré-preenchidos pelo de-para (operador ajusta no front-end).
    """
    complemento = m.complemento_historico or _complemento_padrao(p)
    data = m.data_lancamento or (p.data_nf or "")
    lancamentos: List[Lancamento] = []
    for desp in p.despesas:
        sug = sugerir_despesa(desp.get("descricao"))
        lancamentos.append(
            Lancamento(
                data=data,
                conta_debito=m.conta_debito or sug["conta_debito"],
                conta_credito=m.conta_credito or sug["conta_credito"],
                valor=float(desp.get("valor") or 0.0),
                cod_historico=m.cod_historico or sug["cod_historico"],
                complemento_historico=f"{complemento} - {desp.get('descricao', '')}".strip(" -"),
                inicia_lote=m.inicia_lote or "",
                matriz_filial=m.matriz_filial or "",
                cc_debito=m.cc_debito or "",
                cc_credito=m.cc_credito or "",
            )
        )
    if not lancamentos and p.valor_nf:
        # Sem fechamento: ao menos um lançamento de exemplo com o valor da NF.
        sug = sugerir_fornecedor(p.fornecedor_estrangeiro) or {}
        lancamentos.append(
            Lancamento(
                data=data,
                conta_debito=m.conta_debito or sug.get("conta", ""),
                conta_credito=m.conta_credito or "",
                valor=float(p.valor_nf),
                cod_historico=m.cod_historico or sug.get("cod_historico", ""),
                complemento_historico=complemento,
            )
        )
    return lancamentos


def _complemento_padrao(p: ProcessoExtraido) -> str:
    partes = []
    if p.processo:
        partes.append(f"PROCESSO {p.processo}")
    if p.di_duimp:
        partes.append(f"DI/DUIMP {p.di_duimp}")
    if p.numero_nf:
        partes.append(f"NF {numero_nf_limpo(p.numero_nf)}")  # inteiro limpo (spec §1.4 [R3])
    return " ".join(partes)


# ---------------------------------------------------------------------------
# Saída C — cadastro de fornecedor (bônus)
# ---------------------------------------------------------------------------

COLUNAS_C = [
    "Código Exportador", "Nome Exportador Estrangeiro", "Endereço",
    "País Aquisição", "Nome Fabricante", "País Origem",
    "Relação Exportador×Fabricante", "Vinculação Comprador×Vendedor",
]


def gerar_saida_c(processos: List[ProcessoExtraido]) -> str:
    linhas = [COLUNAS_C]
    for p in processos:
        linhas.append([
            "", p.fornecedor_estrangeiro or "", "", p.pais_aquisicao or "",
            p.fabricante or "", p.pais_origem or "", "", "",
        ])
    return _writer(linhas)
