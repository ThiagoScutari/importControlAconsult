"""Extrator do fechamento despadronizado TERRA DESP. ADUANEIROS."""
from __future__ import annotations

import re
from typing import Dict, List

from backend.detector import CNPJ_TERRA, TipoDocumento
from backend.pdf_utils import buscar, parse_valor_br


def _despesas(texto: str) -> List[Dict]:
    """Lê os lançamentos entre 'Lançamentos' e o bloco de retenções."""
    bloco = re.search(
        r"Lan[çc]amentos\s*\n.*?Vencimento\s+Valor\s*\n(.*?)\n\s*Adiantamentos",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    trecho = bloco.group(1) if bloco else ""
    despesas = []
    for linha in trecho.splitlines():
        m = re.match(
            r"\s*(.+?)\s+(\d{2}/\d{2}/\d{4})\s*[-+]\s*([\d.,]+)\s*$", linha
        )
        if m:
            despesas.append(
                {
                    "descricao": m.group(1).strip(),
                    "vencimento": m.group(2),
                    "valor": parse_valor_br(m.group(3)),
                }
            )
    return despesas


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.FECHAMENTO_TERRA.value}

    d["despachante"] = buscar(r"^(TERRA[^\n]*?)\s+Nota de", texto, flags=re.IGNORECASE | re.MULTILINE) or "TERRA"
    d["cnpj"] = buscar(r"C\.N\.P\.J\.\s*:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto) or CNPJ_TERRA

    # Cliente: primeiro CNPJ que não é o do despachante
    m = re.search(
        r"\n([A-ZÀ-Ÿ][^\n]*?)\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto
    )
    # pula a linha do próprio despachante, se vier antes
    for m in re.finditer(r"\n([A-ZÀ-Ÿ][^\n]*?)\s+(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto):
        if m.group(2) != d["cnpj"]:
            d["cliente_nome"] = m.group(1).strip()
            d["cliente_cnpj"] = m.group(2)
            break
    else:
        d["cliente_nome"] = d["cliente_cnpj"] = None

    # Linha do processo: "1819 25/10/2025 Importação YSPINFFBR870 20/08/2025 870#"
    m = re.search(
        r"\n(\d+)\s+\d{2}/\d{2}/\d{4}\s+Importa[çc][ãa]o\s+(\S+)\s+\d{2}/\d{2}/\d{4}\s+(\d+#)",
        texto,
    )
    if m:
        d["cod_interno"] = m.group(1)
        d["fatura"] = m.group(2)
        d["referencia"] = m.group(3)
    else:
        d["cod_interno"] = d["fatura"] = d["referencia"] = None

    # Transporte: navio / origem / destino
    m = re.search(
        r"Armador / Cia\. A[ée]rea\s+Navio / V[ôo]o\s+Origem\s+Destino\s*\n([^\n]+)",
        texto,
        re.IGNORECASE,
    )
    if m:
        tokens = m.group(1).split()
        d["destino"] = tokens[-1] if tokens else None
        d["origem"] = tokens[-2] if len(tokens) >= 2 else None
        # navio = tokens entre armador (2 primeiros) e origem (best-effort)
        d["navio"] = " ".join(tokens[2:-2]) if len(tokens) > 4 else None
    else:
        d["origem"] = d["destino"] = d["navio"] = None

    d["despesas"] = _despesas(texto)

    # Linha de retenções/totais (layout fixo TERRA)
    m = re.search(r"Adiantamentos PIS COFINS.*?\n([^\n]+)", texto, re.IGNORECASE | re.DOTALL)
    nums = [parse_valor_br(x) for x in re.findall(r"[\d.]+,\d{2}", m.group(1))] if m else []
    # ordem: adiantamentos, pis, cofins, csll, despesas, iss, total_informativo, saldo
    d["retencoes"] = {
        "pis": nums[1] if len(nums) > 1 else None,
        "cofins": nums[2] if len(nums) > 2 else None,
        "csll": nums[3] if len(nums) > 3 else None,
        "iss": nums[5] if len(nums) > 5 else None,
    }
    d["total_informativo"] = nums[6] if len(nums) > 6 else None
    d["saldo"] = nums[7] if len(nums) > 7 else None

    return d
