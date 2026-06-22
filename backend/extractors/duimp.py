"""Extrator da DUIMP (Extrato da Duimp)."""
from __future__ import annotations

import re
from typing import Dict

from backend.detector import TipoDocumento
from backend.extractors.comum import parse_bloco_comex
from backend.pdf_utils import buscar, buscar_valor, normalizar_espacos


def _nome_codigo(rotulo: str, texto: str):
    """Captura o nome (possivelmente em 2 linhas) após 'CODIGO - NOME ... Endereço'."""
    padrao = rotulo + r":[^\n]*\n\s*\S+\s*-\s*(.+?)\n\s*Endere[çc]o"
    m = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return normalizar_espacos(m.group(1)) if m else None


def extrair(texto: str) -> Dict:
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
        from backend.pdf_utils import parse_valor_br

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
