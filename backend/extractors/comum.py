"""Parsing do bloco "Dados Complementares / RESUMO" comum à DI e à DUIMP.

Ambos os extratos da Receita trazem o mesmo trecho montado pelo despachante:
referência, B/L, navio, chegada, armazém, fatura, volumes, e os blocos
"RESUMO DE VALORES TOTAIS" e "RESUMO DOS TRIBUTOS RECOLHIDOS".
"""
from __future__ import annotations

from typing import Dict

from backend.pdf_utils import buscar, buscar_valor


def parse_bloco_comex(texto: str) -> Dict:
    """Extrai os campos compartilhados entre DI e DUIMP a partir do texto."""
    d: Dict = {}

    # Identificação interna do despacho
    d["referencia"] = buscar(r"REF\.*:\s*(\d+#)", texto)
    d["bl"] = buscar(r"B/L\.*:\s*(\S+)", texto)
    d["navio"] = buscar(r"NAVIO\.*:\s*(.+)", texto)
    d["chegada"] = buscar(r"CHEGADA\.*:\s*([\d/]+)", texto)
    d["armazem"] = buscar(r"ARMAZEM\.*:\s*(.+)", texto)
    d["fatura"] = buscar(r"FATURA\.*:\s*(\S+)", texto)
    d["volumes"] = buscar_valor(r"VOLUME\.*:\s*(\d+)", texto)

    # Cotação (linha "FOB : 220 DOLAR DOS EUA 5,089900000")
    d["cotacao"] = buscar_valor(r"FOB\s*:\s*\d+\s+DOLAR DOS EUA\s+([\d.,]+)", texto)

    # RESUMO DE VALORES TOTAIS
    d["fob_rs"] = buscar_valor(r"FOB\.+\s*R\$\s*([\d.,]+)", texto)
    d["fob_us"] = buscar_valor(r"FOB\.+\s*R\$\s*[\d.,]+\s*US\$\s*([\d.,]+)", texto)
    d["frete_rs"] = buscar_valor(r"Frete Intl\.+\s*R\$\s*([\d.,]+)", texto)
    d["valor_aduaneiro_rs"] = buscar_valor(r"Vr\.Aduaneiro\s*R\$\s*([\d.,]+)", texto)

    # RESUMO DOS TRIBUTOS RECOLHIDOS
    d["ii"] = buscar_valor(r"Imposto de Importacao\.+R\$\s*([\d.,]+)", texto)
    d["ipi"] = buscar_valor(r"Imposto Prod\. Industrializados\.+R\$\s*([\d.,]+)", texto)
    d["pis"] = buscar_valor(r"PIS/PASEP\.+R\$\s*([\d.,]+)", texto)
    d["cofins"] = buscar_valor(r"COFINS\.+R\$\s*([\d.,]+)", texto)
    d["siscomex"] = buscar_valor(r"Siscomex\.+R\$\s*([\d.,]+)", texto)
    d["total_tributos"] = buscar_valor(r"\nTotal\.+R\$\s*([\d.,]+)", texto)

    return d
