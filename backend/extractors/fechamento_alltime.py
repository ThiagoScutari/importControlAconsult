"""Extrator do fechamento ALL TIME (Prestação de Contas).

O PDF vem de digitalização e o texto é **OCR-degradado** (ex.: ``ADIANTAMENTO`` →
``ADIANTAMENT0``/``ADIANTAMENTC)S``; ``R$`` → ``R;``/``RS``). Extração
**best-effort** para a Fatia 1: o objetivo é (1) rotear ALL TIME para o parser
certo — antes ele caía no SYNDEX/DI — e (2) **povoar as despesas** para o
operador conferir/completar. A leitura fina fica para a Fatia 2 (OCR).

Layout (topo do documento): seção ``PRESTAÇÃO DE CONTAS`` com uma linha por
rubrica ``<descrição> PAGTO VIA ALL TIME R$<valor>`` e um bloco
``ADIANTAMENTOS``. Ancorado em rótulos, nunca em índice de token.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from backend.detector import TipoDocumento
from backend.pdf_utils import buscar, parse_valor_br, primeiro_cnpj, somar_adiantamentos

# Valor monetário tolerante ao ruído do OCR no "R$" (aparece como R$, R;, R!, RS).
_VALOR = re.compile(r"R[\$S;!]?\s?(\d[\d.\s]*,\d{2})")

# Raiz "ADIANTAMENT" casa o OCR "ADIANTAMENT0"/"ADIANTAMENTC)S" (spec §1.5 6.2 [R2]).
_ADIANT = re.compile(r"ADIANTAMENT", re.IGNORECASE)

# Linhas que são subtotal/total puros (não são despesa própria).
_SO_TOTAL = re.compile(r"(?i)^(TOTAL|SUBTOTAL|SALDO|VALOR TOTAL|BASE)\b")

# Linhas de cabeçalho (valor CIF/total da nota) — não são despesa; evita um
# fantasma de ~402 mil (o valor CIF) entrar na lista.
_CABECALHO = re.compile(r"(?i)(PRODUTOS|VALOR\s*CIF|TOTAL DA NOTA|TRANSPORTE:)")


def _regiao_prestacao(texto: str) -> str:
    """Trecho da 'PRESTAÇÃO DE CONTAS' (topo) até 'SALDO FINAL' — exclui o dossiê
    anexo (NFS-e, comprovantes, DI) que vem depois e poluiria as despesas."""
    ini = re.search(r"PRESTA[ÇC]A[O0]\s+DE\s+CONTAS", texto, re.IGNORECASE)
    resto = texto[ini.start():] if ini else texto
    fim = re.search(r"SALDO\s+FINAL", resto, re.IGNORECASE)
    if fim:
        return resto[: fim.end() + 120]
    dem = re.search(r"DEMONSTRATIVO DE DESPESAS", resto, re.IGNORECASE)
    return resto[: dem.start()] if dem else resto[:2000]


def _valor_linha(linha: str) -> Optional[float]:
    m = _VALOR.search(linha)
    if not m:
        return None
    return parse_valor_br(re.sub(r"\s+", "", m.group(1)))


def _despesas(regiao: str) -> List[Dict]:
    despesas: List[Dict] = []
    for linha in regiao.splitlines():
        l = linha.strip()
        if not l:
            continue
        valor = _valor_linha(l)
        if valor is None:
            continue
        # descrição = texto antes de "PAGT"/do valor, limpo
        corte = re.split(r"PAGT|R[\$S;!]\s?\d", l, maxsplit=1)[0].strip(" .:-'`")
        desc = re.sub(r"\s+", " ", corte)
        if _SO_TOTAL.match(desc) or _CABECALHO.search(desc):
            continue
        # exige uma descrição minimamente textual (evita subtotais "R$17.224,79")
        if len(re.findall(r"[A-Za-zÀ-ÿ]", desc)) < 3:
            continue
        tipo = "C" if _ADIANT.search(l) else "D"  # adiantamento é crédito (Passo 6.2)
        despesas.append({"descricao": desc, "valor": valor, "tipo": tipo})
    return despesas


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.FECHAMENTO_ALLTIME.value}

    d["despachante"] = buscar(r"(ALL TIME[^\n]*?LTDA)", texto) or "ALL TIME"
    d["cnpj"] = primeiro_cnpj(texto)

    # Referência ALL TIME (nº do processo) e referência do cliente
    d["processo"] = buscar(r"REF\s+ALL\s+TIME:\s*(\S+)", texto)
    d["referencia"] = d["processo"]  # chave de consolidação
    d["ref_cliente"] = buscar(r"REF\s+CLIENTE:\s*(\S+)", texto)
    d["di"] = buscar(r"\bDI\s+(\d{2}/\d{6,7}-?\w)", texto)

    regiao = _regiao_prestacao(texto)
    despesas = _despesas(regiao)
    d["despesas"] = despesas

    # Adiantamento (crédito do Passo 6.2): soma toda linha cujo rótulo contenha
    # a raiz "adiantament" (tolerante ao OCR "ADIANTAMENT0"). [F1-04]
    d["adiantamento_total"], d["adiantamentos"] = somar_adiantamentos(despesas)

    # Saldo final (best-effort): valor logo após "SALDO FINAL".
    m = re.search(r"SALDO\s+FINAL[\s\S]{0,60}?R[\$S;!]?\s?([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["saldo"] = parse_valor_br(m.group(1)) if m else None

    return d
