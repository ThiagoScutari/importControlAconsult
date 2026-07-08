"""Extrator da Nota Fiscal de Importação (DANFE de entrada)."""
from __future__ import annotations

import re
from typing import Dict

from backend.detector import TipoDocumento
from backend.pdf_utils import buscar, buscar_valor, parse_valor_br


def _valores_apos(rotulo: str, texto: str):
    """Retorna a lista de números BR na linha seguinte ao cabeçalho `rotulo`."""
    m = re.search(rotulo + r"[^\n]*\n([^\n]+)", texto, re.IGNORECASE)
    if not m:
        return []
    return [parse_valor_br(x) for x in re.findall(r"[\d.]+,\d+", m.group(1))]


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.NOTA_FISCAL.value}

    d["numero"] = buscar(r"N[ºo]\.?\s*(\d{3}\.\d{3}\.\d{3})", texto)
    d["serie"] = buscar(r"S[ée]rie\s*(\d+)", texto)
    d["emissao"] = buscar(r"EMISS[ÃA]O:\s*([\d/]+)", texto)

    d["emitente_nome"] = buscar(r"RECEBEMOS DE (.+?) OS PRODUTOS", texto)
    d["emitente_cnpj"] = buscar(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto)

    m = re.search(
        r"NOME / RAZ[ÃA]O SOCIAL CNPJ / CPF DATA DA EMISS[ÃA]O\s*\n(.+?)\s+"
        r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})",
        texto,
        re.IGNORECASE,
    )
    d["destinatario_nome"] = m.group(1).strip() if m else None
    d["destinatario_cnpj"] = m.group(2) if m else None

    # CFOP: layout 1159 ("5949PECAS") ou geral do item (NCM CST CFOP UNID)
    d["cfop"] = buscar(r"(\d{4})PECAS", texto) or buscar(
        r"\b\d{8}\s+\d{2,3}\s+(\d{4})\s+[A-Z]{2}\b", texto
    )

    # Linha 1 do cálculo: base ICMS, ICMS, ..., valor produtos (último).
    # Âncora tolera "CÁLC. DO ICMS" (1159) e "CÁLCULO DO ICMS" (SY1453).
    linha1 = _valores_apos(r"BASE DE C[ÁA]LC[\w.]* DO ICMS", texto)
    if linha1:
        d["base_icms"] = linha1[0]
        d["icms"] = linha1[1] if len(linha1) > 1 else None
        d["valor_produtos"] = linha1[-1]
    else:
        d["base_icms"] = d["icms"] = d["valor_produtos"] = None

    # Linha 2: frete, seguro, desc, outras, IPI, COFINS, total (último)
    linha2 = _valores_apos(r"VALOR DO FRETE", texto)
    if linha2:
        d["ipi"] = linha2[4] if len(linha2) > 4 else None
        d["valor_total"] = linha2[-1]
    else:
        d["ipi"] = d["valor_total"] = None

    # Chave de acesso (11 grupos de 4 dígitos)
    chave = buscar(r"((?:\d{4}\s+){10}\d{4})", texto)
    d["chave"] = re.sub(r"\s+", "", chave) if chave else None

    # Informações complementares
    d["processo"] = buscar(r"N[úu]mero do Processo:\s*(\S+)", texto)
    d["pis_entrada"] = buscar_valor(r"Valor do PIS Entrada:\s*\n?\s*R\$\s*([\d.,]+)", texto)
    d["cofins_entrada"] = buscar_valor(r"Valor do COFINS Entrada:\s*R\$\s*([\d.,]+)", texto)
    d["siscomex"] = buscar_valor(r"Valor Taxa Siscomex:\s*R\$\s*([\d.,]+)", texto)

    # Reforma tributária (Info. Complementares): "CBS R$ 3.018,3 / IBS UF R$
    # 273,57 / IBS MUN. R$ 0,00". Extraídos e reservados (regra de partida a
    # confirmar com a Larissa). Ausentes na NF antiga (1159) -> None.
    d["cbs"] = buscar_valor(r"\bCBS\s*R\$\s*([\d.,]+)", texto)
    d["ibs_uf"] = buscar_valor(r"IBS[\s.]*UF[\s.]*R\$\s*([\d.,]+)", texto)
    d["ibs_mun"] = buscar_valor(r"IBS[\s.]*MUN[\s.]*R\$\s*([\d.,]+)", texto)

    return d
