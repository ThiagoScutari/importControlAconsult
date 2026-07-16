"""Extrator do fechamento SYNDEX (Demonstrativo de Despesas / Pedido de numerário).

Layout tabular por linha: ``Data  Descrição  [Complemento]  Valor  T[C|D]  [Nr. Nota]``.
Ancorado em **rótulos** (``Total de Créditos``/``Total de Débitos``, cabeçalho
``Valor T``), nunca em índice de token — evita a fragilidade do TERRA/WIN.

Dois subtipos com o mesmo layout:
- ``fechamento`` — prestação de contas real (é o que se lança);
- ``numerario`` — pedido de adiantamento (estimativa).
"""
from __future__ import annotations

import re
from typing import Dict, List

from backend.detector import CNPJ_SYNDEX, TipoDocumento
from backend.pdf_utils import buscar, buscar_valor, parse_valor_br, somar_adiantamentos

# Uma linha de lançamento: data, descrição (+complemento), valor BR, tipo C/D, resto (nota).
_LINHA = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.]+,\d{2})\s+([CD])\b(.*)$",
    re.MULTILINE,
)


def _regiao_lancamentos(texto: str) -> str:
    """Trecho do cabeçalho da tabela até 'Total de Débitos' (exclui dossiê anexo)."""
    m = re.search(
        r"Valor\s+T(?:ipo)?\b.*?\n(.*?)Total de D[ée]bitos",
        texto,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1) if m else texto


def _lancamentos(texto: str):
    """Devolve (despesas[D], creditos[C]) como listas de dicts."""
    regiao = _regiao_lancamentos(texto)
    despesas: List[Dict] = []
    creditos: List[Dict] = []
    for m in _LINHA.finditer(regiao):
        data, desc, valor, tipo, resto = m.groups()
        item = {
            "descricao": desc.strip(),
            "valor": parse_valor_br(valor),
            "vencimento": data,
            "tipo": tipo,
            "nota": resto.strip() or None,
        }
        (despesas if tipo == "D" else creditos).append(item)
    return despesas, creditos


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.FECHAMENTO_SYNDEX.value}

    # Subtipo: prestação de contas real x pedido de numerário (estimativa)
    if "PEDIDO DE NUMERÁRIO" in texto.upper():
        d["subtipo"] = "numerario"
    else:
        d["subtipo"] = "fechamento"

    d["despachante"] = buscar(r"(SYNDEX[^\n]*?LTDA)", texto) or "SYNDEX"
    d["cnpj"] = buscar(r"CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto) or CNPJ_SYNDEX

    d["cliente_nome"] = buscar(r"Cliente:\s*(.+?)\s+CNPJ:", texto)
    d["cliente_cnpj"] = buscar(r"Cliente:[^\n]*CNPJ:\s*(\d{14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto)

    # Processo (nº SYNDEX) e referência do cliente
    d["processo"] = buscar(r"(?:Fatura|processo):\s*\n?\s*(SY\d+/\d+)", texto)
    d["referencia"] = d["processo"]  # chave de consolidação
    d["ref_cliente"] = buscar(r"Ref\.:\s*(\S+)", texto)

    despesas, creditos = _lancamentos(texto)
    d["despesas"] = despesas
    d["creditos"] = creditos

    # Adiantamento (crédito do Passo 6.2): no SYNDEX vem como lançamento tipo "C"
    # ("ADIANTAMENTO DE NUMERÁRIO"), então mora em `creditos`. Soma todas as
    # entradas rotuladas "adiantamento" (numerário + complemento). [F1-04]
    d["adiantamento_total"], d["adiantamentos"] = somar_adiantamentos(despesas, creditos)

    d["total_debitos"] = buscar_valor(r"Total de D[ée]bitos:\s*R\$\s*([\d.,]+)", texto)
    d["total_creditos"] = buscar_valor(r"Total de Cr[ée]ditos:\s*R\$\s*([\d.,]+)", texto)
    if d["total_debitos"] is not None and d["total_creditos"] is not None:
        d["saldo"] = round(d["total_creditos"] - d["total_debitos"], 2)
    else:
        d["saldo"] = None

    # Dados bancários (preferir conta com hífen)
    d["banco"] = "SANTANDER" if re.search(r"SANTANDER", texto, re.IGNORECASE) else buscar(r"Banco:\s*(.+)", texto)
    d["agencia"] = buscar(r"Ag[êe]ncia:\s*(\d+)", texto) or buscar(r"Ag\.?:\s*(\d+)", texto)
    # preferir a conta com dígito verificador (hífen)
    d["conta"] = (
        buscar(r"Conta Corrente:\s*([\d-]+)", texto)
        or buscar(r"C/C:\s*([\d-]+)", texto)
        or buscar(r"Conta:\s*([\d-]+)", texto)
    )

    return d
