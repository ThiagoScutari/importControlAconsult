"""Extrator da DI (Extrato da Declaração de Importação)."""
from __future__ import annotations

from typing import Dict

from backend.detector import TipoDocumento
from backend.extractors.comum import parse_bloco_comex
from backend.pdf_utils import buscar, buscar_valor


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.DI.value}
    d.update(parse_bloco_comex(texto))

    d["numero"] = buscar(r"Declara[çc][ãa]o:\s*(\d{2}/\d{7}-\d)", texto)
    d["data_registro"] = buscar(r"Data do Registro:\s*([\d/]+)", texto)
    d["adicoes"] = int(buscar(r"Quantidade de Adi[çc][õo]es:\s*(\d+)", texto) or 0) or None

    d["importador_cnpj"] = buscar(
        r"Importador\s*\n\s*CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto
    )
    d["importador_nome"] = buscar(
        r"Importador\s*\n\s*CNPJ:\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+(.+)", texto
    )
    d["adquirente_cnpj"] = buscar(
        r"Adquirente da Mercadoria\s*\n\s*CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto
    )
    d["adquirente_nome"] = buscar(
        r"Adquirente da Mercadoria\s*\n\s*CNPJ:\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s+(.+)", texto
    )
    d["representante"] = buscar(
        r"Representante Legal\s*\n\s*CPF:\s*[\d.\-]+\s+(.+)", texto
    )

    # Valores em US$ (página 1)
    d["frete_us"] = buscar_valor(r"Frete:\s*DOLAR DOS EUA\s*([\d.,]+)", texto)
    d["vmle_us"] = buscar_valor(r"VMLE:\s*DOLAR[^\d]*([\d.,]+)", texto)
    d["vmld_us"] = buscar_valor(r"VMLD:\s*DOLAR[^\d]*([\d.,]+)", texto)

    # Pesos (formato próprio da DI)
    d["peso_bruto"] = buscar_valor(r"Peso Bruto:\s*([\d.,]+)", texto)
    d["peso_liquido"] = buscar_valor(r"Peso L[íi]quido:\s*([\d.,]+)", texto)

    return d
