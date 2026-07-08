"""Extrator da DUIMP (Extrato da Duimp).

Há **dois layouts** de extrato de DUIMP nos exemplos reais:

- **RESUMO** (ex.: DUIMP 1159) — usa os blocos "RESUMO DE VALORES TOTAIS" /
  "RESUMO DOS TRIBUTOS RECOLHIDOS" compartilhados com a DI (``comum.py``).
- **VMCV** (ex.: DUIMP SY1453 `26BR0000258971-1`) — usa blocos ``==========``
  com rótulos ``VMCV USD/REAIS``, ``MOEDAS E TAXAS`` e ``DEMONSTRATIVO DE
  CALCULOS``, e traz a Reforma apenas como ``cClassTrib`` (os valores de
  CBS/IBS ficam na NF-e).

``extrair`` detecta o layout pelo conteúdo e roteia. O branch RESUMO permanece
inalterado (não quebrar o 1159).
"""
from __future__ import annotations

import re
from typing import Dict

from backend.detector import TipoDocumento
from backend.extractors.comum import parse_bloco_comex
from backend.pdf_utils import buscar, buscar_valor, normalizar_espacos, parse_valor_br


def _nome_codigo(rotulo: str, texto: str):
    """Captura o nome (possivelmente em 2 linhas) após 'CODIGO - NOME ... Endereço'."""
    padrao = rotulo + r":[^\n]*\n\s*\S+\s*-\s*(.+?)\n\s*Endere[çc]o"
    m = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return normalizar_espacos(m.group(1)) if m else None


def extrair(texto: str) -> Dict:
    """Detecta o layout da DUIMP e delega ao extrator específico."""
    if _e_layout_vmcv(texto):
        return _extrair_vmcv(texto)
    return _extrair_resumo(texto)


def _e_layout_vmcv(texto: str) -> bool:
    tu = texto.upper()
    return "VMCV USD" in tu or "DEMONSTRATIVO DE CALCULOS" in tu


# ---------------------------------------------------------------------------
# Layout RESUMO (DUIMP 1159) — inalterado
# ---------------------------------------------------------------------------

def _extrair_resumo(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.DUIMP.value}
    d.update(parse_bloco_comex(texto))

    # Identificação
    m = re.search(r"Extrato da Duimp\s+(\S+)\s*/\s*Vers\w+\s*(\d+)", texto, re.IGNORECASE)
    d["numero"] = m.group(1) if m else None
    d["versao"] = m.group(2) if m else None

    d["situacao"] = buscar(r"Situa[çc][ãa]o da Duimp:\s*\n?\s*(.+)", texto)
    d["importador_cnpj"] = buscar(
        r"Nome do importador:\s*\n\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto
    )
    d["importador_nome"] = buscar(
        r"Nome do importador:\s*\n\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+(.+)", texto
    )
    d["tipo_importacao"] = buscar(
        r"Importa[çc][ãa]o por (Conta e Ordem|Pr[óo]pria|Encomenda)", texto
    )

    # Fatura / invoice
    d["fatura_numero"] = buscar(r"N[ÚU]MERO\s*-\s*(\S+?),", texto)
    d["fatura_data"] = buscar(r"DATA DE EMISS[ÃA]O\s*-\s*([\d/]+)", texto)
    d["fatura_valor_us"] = buscar_valor(r"VALOR US\$\s*-\s*\n?\s*([\d.,]+)", texto)

    # País de procedência e pesos (mesma linha no extrato)
    d["pais_procedencia"] = buscar(
        r"Pa[íi]s de Proced[êe]ncia:[^\n]*\n\s*([^,\d\n]+?)\s*,", texto
    )
    m = re.search(
        r"Pa[íi]s de Proced[êe]ncia:[^\n]*\n[^\d\n]*?([\d.,]+)\s+([\d.,]+)",
        texto,
    )
    if m:
        d["peso_bruto"] = parse_valor_br(m.group(1))
        d["peso_liquido"] = parse_valor_br(m.group(2))
    else:
        d["peso_bruto"] = d["peso_liquido"] = None

    d["pais_aquisicao"] = buscar(
        r"Pa[íi]s de aquisi[çc][ãa]o:[^\n]*\n\s*([^-\n]+?)\s*-\s*[A-Z]{2}", texto
    )

    # Exportador estrangeiro e fabricante/produtor (1º item)
    d["exportador"] = _nome_codigo(r"C[óo]digo do Exportador Estrangeiro", texto)
    d["fabricante"] = _nome_codigo(r"C[óo]digo do Fabricante/Produtor", texto)

    # Data de registro (evento "Declaração registrada")
    d["data_registro"] = buscar(
        r"(\d{2}/\d{2}/\d{4}),\s*Declara[çc][ãa]o registrada", texto
    )

    return d


# ---------------------------------------------------------------------------
# Layout VMCV (DUIMP SY1453 26BR0000258971-1)
# ---------------------------------------------------------------------------

def _extrair_vmcv(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.DUIMP.value}

    # Identificação
    m = re.search(r"Extrato da Duimp\s+(\S+)\s*/\s*Vers\w+\s*(\d+)", texto, re.IGNORECASE)
    d["numero"] = m.group(1) if m else None
    d["versao"] = m.group(2) if m else None
    d["situacao"] = buscar(r"Situa[çc][ãa]o da Duimp:\s*\n\s*(.+)", texto)

    # Importador (CNPJ e nome na linha seguinte aos rótulos)
    d["importador_cnpj"] = buscar(
        r"CNPJ do importador:[^\n]*\n\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto
    )
    d["importador_nome"] = buscar(
        r"CNPJ do importador:[^\n]*\n\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+(.+)", texto
    )

    # Tipo de importação (indicação para terceiros)
    d["tipo_importacao"] = buscar(
        r"Indica[çc][ãa]o de importa[çc][ãa]o para terceiros:\s*\n\s*(.+)", texto
    )

    # Referências do despachante/cliente
    d["referencia"] = buscar(r"REF\.\s*SYNDEX:\s*(\S+)", texto)
    d["ref_cliente"] = buscar(r"REF\.\s*CLIENTE:\s*(\S+)", texto)

    # Cotação (TX DI) — "220 - USD - DOLAR DOS EUA - Taxa: 5,28000"
    d["cotacao"] = buscar_valor(r"DOLAR DOS EUA\s*-\s*Taxa:\s*([\d.,]+)", texto)

    # Demonstrativo de valores (VMCV = valor da mercadoria; ~FOB)
    d["vmcv_usd"] = buscar_valor(r"VMCV USD:\s*([\d.,]+)", texto)
    d["vmcv_reais"] = buscar_valor(r"VMCV REAIS:\s*([\d.,]+)", texto)
    d["fob_us"] = d["vmcv_usd"]
    d["fob_rs"] = d["vmcv_reais"]
    # invoice: sem Comercial Invoice, o valor em US$ vem do VMCV da DUIMP
    d["fatura_numero"] = None
    d["fatura_valor_us"] = d["vmcv_usd"]
    d["frete_rs"] = buscar_valor(r"VALOR REAIS:\s*([\d.,]+)", texto)
    d["valor_aduaneiro_us"] = buscar_valor(r"VALOR ADUANEIRO USD:\s*([\d.,]+)", texto)
    d["valor_aduaneiro_rs"] = buscar_valor(r"VALOR ADUANEIRO REAIS:\s*([\d.,]+)", texto)

    # Demonstrativo de cálculos (tributos recolhidos)
    d["ii"] = buscar_valor(r"II RECOLHIDO\.*:\s*R\$\s*([\d.,]+)", texto)
    d["ipi"] = buscar_valor(r"IPI RECOLHIDO\.*:\s*R\$\s*([\d.,]+)", texto)
    d["pis"] = buscar_valor(r"PIS RECOLHIDO\.*:\s*R\$\s*([\d.,]+)", texto)
    d["cofins"] = buscar_valor(r"COFINS RECOLHIDO\.*:\s*R\$\s*([\d.,]+)", texto)
    d["siscomex"] = buscar_valor(r"TAXA SISCOMEX\.*:\s*R\$\s*([\d.,]+)", texto)
    federais = [d["ii"], d["ipi"], d["pis"], d["cofins"], d["siscomex"]]
    # total não é impresso na DUIMP VMCV -> derivado (soma), None se faltar algo
    d["total_tributos"] = (
        round(sum(v for v in federais if v is not None), 2)
        if all(v is not None for v in federais)
        else None
    )

    # Reforma: só cClassTrib na DUIMP (valores de CBS/IBS ficam na NF-e)
    d["cclasstrib"] = buscar(r"cClassTrib\)\s*\n\s*(\d{6})", texto)
    d["cbs"] = d["ibs_uf"] = d["ibs_mun"] = None

    # Carga / logística
    d["pais_procedencia"] = buscar(r"PA[ÍI]S PROCED[ÊE]NCIA:\s*\w+\s*-\s*(.+)", texto)
    d["pais_aquisicao"] = buscar(
        r"Pa[íi]s de aquisi[çc][ãa]o:[^\n]*\n\s*([^-\n]+?)\s*-\s*[A-Z]{2}", texto
    )
    d["peso_bruto"] = buscar_valor(r"PESO BRUTO:\s*([\d.,]+)", texto)
    d["peso_liquido"] = buscar_valor(r"PESO L[ÍI]QUIDO:\s*([\d.,]+)", texto)
    d["chegada"] = buscar(r"DATA CHEGADA:\s*([\d/]+)", texto)
    d["data_registro"] = buscar(r"(\d{2}/\d{2}/\d{4}),\s*Declara[çc][ãa]o registrada", texto)
    d["navio"] = None  # não impresso na DUIMP (vem do fechamento/NFS-e)
    d["bl"] = None
    d["volumes"] = None

    # Exportador / fabricante (mesmos helpers; nome pode vir com versão no fim)
    d["exportador"] = _nome_codigo_vmcv(r"C[óo]digo do Exportador Estrangeiro", texto)
    d["fabricante"] = _nome_codigo_vmcv(r"C[óo]digo do Fabricante/Produtor", texto)

    # NCM (1º item) e número de itens
    d["ncm"] = buscar(r"NCM:\s*\n\s*(\d{4}\.\d{4})", texto)
    d["num_itens"] = len(re.findall(r":\s*Item\s+\d{5}", texto)) or None

    return d


def _nome_codigo_vmcv(rotulo: str, texto: str):
    """Nome após 'CODIGO - NOME <versão>\\nEndereço' (layout VMCV, versão no fim)."""
    padrao = rotulo + r":[^\n]*\n\s*\S+\s*-\s*(.+?)\s*\d*\s*\n\s*Endere[çc]o"
    m = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return normalizar_espacos(m.group(1)) if m else None
