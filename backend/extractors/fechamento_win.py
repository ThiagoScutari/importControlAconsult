"""Extrator do fechamento despadronizado WIN TRADING (Prestação de contas)."""
from __future__ import annotations

import re
from typing import Dict, List

from backend.detector import CNPJ_WIN, TipoDocumento
from backend.pdf_utils import (
    buscar,
    buscar_valor,
    normalizar_espacos,
    parse_valor_br,
    somar_adiantamentos,
)

# Descrições que são apenas seções/subtotais (não são despesas reais)
_IGNORAR = re.compile(
    r"^(SUBTOTAL|TOTAL|DESPESAS INTERNACIONAIS|IMPOSTOS|DEMAIS DESPESAS|"
    r"DESCRI[ÇC][ÃA]O|RETEN|DESCONTOS|TOTAIS|FECHAMENTO|.*RECEITAS|SALDO)",
    re.IGNORECASE,
)


def _despesas(texto: str) -> List[Dict]:
    bloco = re.search(r"\nDespesas\s*\n(.*?)\nDescontos", texto, re.IGNORECASE | re.DOTALL)
    trecho = bloco.group(1) if bloco else ""
    despesas = []
    for linha in trecho.splitlines():
        m = re.match(r"\s*(.+?)\s+([\d.]+,\d{2})\s*$", linha)
        if not m:
            continue
        desc = m.group(1).strip()
        # remove sufixos de processo tipo "- {{...}}" ou "- N.F. de entrada"
        desc_limpo = re.sub(r"\s*-\s*\{\{.*?\}\}.*$", "", desc).strip()
        if _IGNORAR.match(desc_limpo):
            continue
        despesas.append({"descricao": desc_limpo, "valor": parse_valor_br(m.group(2))})
    return despesas


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.FECHAMENTO_WIN.value}

    d["trading"] = buscar(r"^(WIN TRADING[^\n]*)", texto, flags=re.IGNORECASE | re.MULTILINE) or "WIN TRADING"
    d["cnpj"] = buscar(r"CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto) or CNPJ_WIN

    d["processo"] = buscar(r"PROCESSO:\s*(\S+)", texto)
    d["modalidade"] = buscar(r"MODALIDADE:\s*(.+?)\s+INCOTERM", texto)
    d["incoterm"] = buscar(r"INCOTERMS?[^:]*:\s*(\w+)", texto)

    # Adquirente / referência / exportador: rótulos vêm DEPOIS dos valores (layout 2 colunas)
    d["adquirente"] = buscar(r"\n([^\n]+?)\s+ESC-\d{4}-", texto)
    m = re.search(r"(ESC-\d{4}-)\s*\n[^\n]*\n\s*([A-Z]\d+)", texto)
    d["ref_adquirente"] = (m.group(1) + m.group(2)) if m else None

    m = re.search(r"\n([A-Z][^\n]*CO\.,)\s*\n[^\n]*INVOICE[^\n]*\n\s*([A-Z]+)", texto, re.IGNORECASE)
    d["exportador"] = normalizar_espacos(m.group(1) + " " + m.group(2)) if m else None

    d["declaracao"] = buscar(r"DECLARA[ÇC][ÃA]O:\s*(\d{2}/\d{7}-\d)", texto)
    d["data_registro"] = buscar(r"DATA REGISTRO DA DECLARA[ÇC][ÃA]O:\s*([\d/]+)", texto)
    d["cotacao"] = buscar_valor(r"COTA[ÇC][ÃA]O USD:\s*([\d.,]+)", texto)

    # Linha de totais FOB/FRETE/SEGURO/VALOR ADUANEIRO
    m = re.search(
        r"FOB \(R\$\)\s+FRETE \(R\$\)\s+SEGURO \(R\$\)\s+VALOR ADUANEIRO \(R\$\)\s*\n([^\n]+)",
        texto,
        re.IGNORECASE,
    )
    nums = [parse_valor_br(x) for x in re.findall(r"[\d.]+,\d+", m.group(1))] if m else []
    d["fob"] = nums[0] if len(nums) > 0 else None
    d["frete"] = nums[1] if len(nums) > 1 else None
    d["seguro"] = nums[2] if len(nums) > 2 else None
    d["valor_aduaneiro"] = nums[3] if len(nums) > 3 else None

    d["despesas"] = _despesas(texto)
    d["total"] = buscar_valor(r"\bTOTAL \(R\$\)\s*([\d.,]+)", texto)
    d["retencoes"] = buscar_valor(r"RETEN[ÇC][ÕO]ES\s*([\d.,]+)", texto)

    # Adiantamento (crédito do Passo 6.2): o layout WIN pode não trazer a linha;
    # nesse caso total = None (o operador informa no middleware). [F1-04]
    d["adiantamento_total"], d["adiantamentos"] = somar_adiantamentos(d["despesas"])

    return d
