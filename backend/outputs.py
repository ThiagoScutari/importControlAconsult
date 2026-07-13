"""Geração dos arquivos de saída (seção 7).

- Saída A: extração estruturada (1 linha por processo) + versão rastreável.
- Saída B: lançamentos no layout Domínio (10 colunas, ``;``, sem cabeçalho).
- Saída C: cadastro de fornecedor (bônus).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import List, Optional

import openpyxl
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter

from backend.depara import sugerir_despesa, sugerir_fornecedor
from backend.models import Lancamento, MiddlewareInput, ProcessoExtraido
from backend.pdf_utils import numero_nf_limpo

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


# ---------------------------------------------------------------------------
# Saída D — Relação das Importações (append no .xlsx da empresa, spec §6.4 [R3])
# ---------------------------------------------------------------------------
#
# A empresa mantém UMA planilha histórica ("Relação importações"), com blocos
# por ano (marcador = col B com o ano e col A vazia) e uma linha por processo.
# A ferramenta NÃO recria a planilha: recebe o arquivo atual da empresa, insere
# UMA linha sob o bloco do ano e devolve para download, preservando as fórmulas
# das colunas calculadas e as demais abas.
#
# Fórmulas reais da 1ª linha de dados (calibrado no arquivo de assets):
#   H = CONCATENATE(I," ",M," ",J," ",C," ",K," ",D)   (descrição do processo)
#   R = P*Q   (col 3 = Invoice USD × TX DI)
#   V = T*U   (col 6 = USD pago × TX câmbio)
#   W = T*Q   (col 7 = USD pago × TX DI)
#   X = V-W   (col 8 = variação cambial)
# São reescritas rebaseadas na linha nova — nunca copiadas por insert_rows, que
# não reajusta referências (limitação do openpyxl).

# Índice 1-based de cada coluna (A=1 … X=24).
_COL_D = {c: i + 1 for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWX")}


def _parse_data_nf(data_nf) -> Optional[datetime]:
    """``dd/mm/aaaa`` (ou ISO) → ``datetime``; ``None`` se não parsear."""
    if not data_nf:
        return None
    if isinstance(data_nf, datetime):
        return data_nf
    txt = str(data_nf).strip()[:10]
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def _num_ou_none(v):
    """Só devolve float para valores já numéricos (campos do modelo já vêm coeridos)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _nf_inteiro(numero_nf):
    """``numero_nf_limpo`` → ``int`` quando possível (col D é inteiro, ex.: 458)."""
    limpo = numero_nf_limpo(numero_nf)
    if limpo in (None, ""):
        return None
    try:
        return int(limpo)
    except (TypeError, ValueError):
        return limpo


def _aba_relacao(wb):
    """Localiza a aba da Relação por nome normalizado ("Relação importações")."""
    for nome in wb.sheetnames:
        n = nome.lower()
        if "rela" in n and "importa" in n:
            return wb[nome]
    return wb[wb.sheetnames[0]]


def _linha_cabecalho(ws) -> int:
    """Linha de cabeçalho (col A começa com "TIPO")."""
    for r in range(1, min(ws.max_row, 12) + 1):
        if str(ws.cell(r, 1).value or "").strip().upper().startswith("TIPO"):
            return r
    return 2


def _eh_linha_dados(ws, r: int) -> bool:
    """Linha de processo real = tem DI/DUIMP (col C) ou Valor NF (col E).

    Ignora marcadores de ano, linhas-modelo de dropdown (só col A/L) e resíduos.
    """
    return (
        ws.cell(r, _COL_D["C"]).value not in (None, "")
        or ws.cell(r, _COL_D["E"]).value not in (None, "")
    )


def _marcadores_ano(ws) -> dict:
    """{ano: linha_do_marcador} — col B é o ano e col A está vazia."""
    marcas = {}
    for r in range(1, ws.max_row + 1):
        a = ws.cell(r, 1).value
        b = ws.cell(r, 2).value
        if (a is None or a == "") and isinstance(b, int) and 2000 < b < 2100:
            marcas[b] = r
    return marcas


def _rebasear_formulas_deslocadas(ws, ins: int) -> None:
    """Reajusta as fórmulas das linhas que desceram por causa de ``insert_rows(ins)``.

    O ``openpyxl`` move as células mas NÃO reescreve as referências: uma linha de
    2026 empurrada de R6→R7 mantém ``=P6*Q6`` (agora apontando para a linha de
    cima). Isso corromperia blocos de anos abaixo do ponto de inserção. Aqui cada
    fórmula deslocada é traduzida da posição antiga (r-1) para a nova (r), como o
    Excel faz ao inserir — os blocos seguintes ficam intactos.
    """
    for r in range(ins + 1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            cel = ws.cell(r, c)
            v = cel.value
            if isinstance(v, str) and v.startswith("="):
                letra = get_column_letter(c)
                cel.value = Translator(v, origin=f"{letra}{r - 1}").translate_formula(f"{letra}{r}")


def append_relacao(
    xlsx_bytes: bytes, p: ProcessoExtraido, m: Optional[MiddlewareInput] = None
) -> bytes:
    """Insere uma linha do processo na Relação da empresa e devolve o .xlsx.

    Não altera fórmulas de linhas existentes, preserva as demais abas e reescreve
    (rebaseadas) as fórmulas das colunas calculadas na linha nova.
    """
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))  # data_only=False: mantém fórmulas
    ws = _aba_relacao(wb)
    hdr = _linha_cabecalho(ws)
    template = hdr + 1  # 1ª linha de dados: molde de number_format

    dt = _parse_data_nf(p.data_nf)
    ano = dt.year if dt else None
    marcas = _marcadores_ano(ws)

    if ano in marcas:
        marcador = marcas[ano]
        posteriores = [row for row in marcas.values() if row > marcador]
        fim = (min(posteriores) - 1) if posteriores else ws.max_row
        ins = marcador + 1
        for r in range(marcador + 1, fim + 1):
            if _eh_linha_dados(ws, r):
                ins = r + 1
    else:
        # Ano sem bloco: cria um novo marcador ao fim dos dados existentes.
        ins = hdr + 1
        for r in range(hdr + 1, ws.max_row + 1):
            if _eh_linha_dados(ws, r):
                ins = r + 1
        if ano:
            ws.insert_rows(ins)
            _rebasear_formulas_deslocadas(ws, ins)
            ws.cell(ins, _COL_D["B"]).value = ano
            ins += 1

    # Inserir NO MEIO (ex.: ano 2025 acima de um bloco 2026) empurra os blocos
    # seguintes para baixo; o rebaseamento reescreve as fórmulas deles p/ a nova
    # posição, deixando-os intactos. Fórmulas ACIMA do ponto de inserção não mudam.
    ws.insert_rows(ins)
    _rebasear_formulas_deslocadas(ws, ins)
    _preencher_linha_relacao(ws, ins, template, p, m)

    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()


def _preencher_linha_relacao(ws, r: int, template: int, p: ProcessoExtraido, m) -> None:
    """Escreve a linha ``r``: colunas de entrada + fórmulas rebaseadas + formatos."""

    def escrever(letra: str, valor) -> None:
        col = _COL_D[letra]
        ws.cell(r, col).value = valor
        ws.cell(r, col).number_format = ws.cell(template, col).number_format

    di = (p.di_duimp or "").strip()
    rotulo_decl = "DUIMP" if "BR" in di.upper() else "DI"
    nf_int = _nf_inteiro(p.numero_nf)
    proc = p.processo or ""

    conta_processo = (m.conta_processo_numero if m else None) or ""
    conta_forn = ""
    if m and getattr(m, "contas_override", None):
        conta_forn = m.contas_override.get("fornecedor_estrangeiro", "") or ""
    usd_cambio = _num_ou_none((m.vlr_usd_pg_cambio if m else None)) or _num_ou_none(p.vlr_usd_pg_cambio) or 0.0
    tx_cambio = _num_ou_none((m.tx_cambio if m else None)) or _num_ou_none(p.tx_cambio) or 0.0

    escrever("A", (m.tipo_importacao if m else None) or p.tipo_importacao or "")
    escrever("B", _parse_data_nf(p.data_nf) or (p.data_nf or ""))
    escrever("C", di)
    escrever("D", nf_int if nf_int is not None else "")
    escrever("E", _num_ou_none(p.valor_nf) if _num_ou_none(p.valor_nf) is not None else "")
    escrever("F", conta_processo)
    # G (texto) e H (fórmula) descrevem o processo do mesmo jeito. Para garantir
    # que G == resultado de H na linha nova, G é montado com os MESMOS valores e
    # separadores da fórmula: CONCATENATE(I," ",M," ",J," ",C," ",K," ",D).
    i_val, k_val = "PROCESSO", "NF"
    d_txt = str(nf_int) if nf_int is not None else ""
    escrever("G", f"{i_val} {proc} {rotulo_decl} {di} {k_val} {d_txt}")
    escrever("H", f'=CONCATENATE(I{r}," ",M{r}," ",J{r}," ",C{r}," ",K{r}," ",D{r})')
    escrever("I", i_val)
    escrever("J", rotulo_decl)
    escrever("K", k_val)
    escrever("L", p.despachante or "")
    escrever("M", proc)
    escrever("N", conta_forn)
    escrever("O", p.fornecedor_estrangeiro or "")
    escrever("P", _num_ou_none(p.invoice_usd) or 0.0)
    escrever("Q", _num_ou_none(p.tx_di) or 0.0)
    escrever("R", f"=P{r}*Q{r}")
    escrever("S", "")
    escrever("T", usd_cambio)
    escrever("U", tx_cambio)
    escrever("V", f"=T{r}*U{r}")
    escrever("W", f"=T{r}*Q{r}")
    escrever("X", f"=V{r}-W{r}")
