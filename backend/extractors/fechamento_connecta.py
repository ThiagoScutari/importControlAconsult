"""Extrator do fechamento CONNECTA (página de FATURAMENTO).

Layout (pág. 1 do dossiê): cabeçalho de referências, um bloco de câmbio/valor
aduaneiro (FOB/FRETE/SEGURO/VALOR ADUANEIRO, colunas USD e BRL — como o WIN) e uma
tabela de DESPESAS por linha (como o SYNDEX). Ancorado em RÓTULOS, nunca em índice
de token.

O bloco da pág. 1 é recortado entre ``TAXA CAMBIAL`` e ``DADOS BANCÁRIOS`` para
blindar contra os anexos do dossiê: a NFS-e da pág. 9 traz "VALOR TOTAL DO SERVIÇO",
que não pode ser confundido com o ``TOTAL`` do faturamento.

A coluna COBRADOR vem colada à descrição no texto linear (sem coordenadas); só a
data e o valor são âncoras confiáveis, então descrição+cobrador são capturados
juntos e — quando o fim casa um cobrador conhecido — ele é destacado em
``cobrador`` (as palavras-chave de :func:`classificar_linha` permanecem na
``descricao``, então o guard §3 e o de-para continuam funcionando).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from backend.detector import TipoDocumento
from backend.pdf_utils import buscar, buscar_valor, parse_valor_br

CNPJ_CONNECTA = "42.929.006/0001-98"

# Cobradores conhecidos (destacados do fim da descrição). Mais específico antes do
# genérico para o casamento por sufixo não parar cedo demais.
_COBRADORES = (
    "Connecta Assessoria Aduaneira",
    "Marinha Mercante",
    "Receita Federal",
    "Portonave",
    "Sefaz/SC",
    "Inmetro",
    "Atlantis",
    "Royal",
)

# Uma linha de despesa: ``<descrição+cobrador> [data] R$ <valor BRL>``. Só data e
# valor são âncoras; a descrição (grupo 1) inclui o cobrador (destacado depois).
_LINHA = re.compile(
    r"^(.+?)\s+(?:(\d{2}/\d{2}/\d{4})\s+)?R\$\s*([\d.]+,\d{2})\s*$",
    re.MULTILINE,
)


def _slice_faturamento(texto: str) -> str:
    """Recorta o bloco da pág. 1 — de 'TAXA CAMBIAL' até 'DADOS BANCÁRIOS'."""
    ini = re.search(r"TAXA CAMBIAL", texto, re.IGNORECASE)
    if not ini:
        return texto
    fim = re.search(r"DADOS\s+BANC[ÁA]RIOS", texto, re.IGNORECASE)
    return texto[ini.start(): fim.start()] if fim else texto[ini.start():]


def _linha_cambio(fat: str, rotulo: str) -> Optional[float]:
    """Coluna BRL (2ª) da linha ``<rotulo> <USD> <BRL> [...]`` do bloco de câmbio.

    O ``^`` + a exigência de dígitos logo após o rótulo desambigua da linha de
    despesa homônima (ex.: a linha 'Frete Maritimo Royal ... R$' não casa).
    """
    m = re.search(
        rf"^{re.escape(rotulo)}\s+([\d.]+,\d{{2}})\s+([\d.]+,\d{{2}})",
        fat,
        re.MULTILINE | re.IGNORECASE,
    )
    return parse_valor_br(m.group(2)) if m else None


def _destacar_cobrador(descricao: str) -> Tuple[str, Optional[str]]:
    """Se a descrição terminar num cobrador conhecido, separa ``(descricao, cobrador)``."""
    alvo = descricao.strip()
    for cob in _COBRADORES:
        m = re.search(re.escape(cob) + r"\s*$", alvo, re.IGNORECASE)
        if m:
            limpa = alvo[: m.start()].strip(" .-")
            return (limpa or alvo), cob
    return alvo, None


def _despesas(fat: str) -> List[Dict]:
    """Tabela de despesas: do cabeçalho 'DESPESAS COBRADOR ...' até 'TOTAL R$'."""
    m = re.search(
        r"DESPESAS\s+COBRADOR\s+DATA DE PAGAMENTO[^\n]*\n(.*?)\n\s*TOTAL\s+R\$",
        fat,
        re.DOTALL | re.IGNORECASE,
    )
    regiao = m.group(1) if m else ""
    despesas: List[Dict] = []
    for lm in _LINHA.finditer(regiao):
        desc, data, valor = lm.groups()
        descricao, cobrador = _destacar_cobrador(desc)
        despesas.append({
            "descricao": descricao,
            "cobrador": cobrador,
            "valor": parse_valor_br(valor),
            "vencimento": data,
            "tipo": "D",  # o layout não tem coluna C/D — tudo é despesa (débito)
        })
    return despesas


def extrair(texto: str) -> Dict:
    d: Dict = {"tipo": TipoDocumento.FECHAMENTO_CONNECTA.value}
    fat = _slice_faturamento(texto)

    # Despachante / CNPJ (rodapé 'DADOS BANCÁRIOS', fora do slice) — com fallback.
    d["despachante"] = (
        buscar(r"(CONNECTA ASSESSORIA ADUANEIRA[^\n]*?LTDA)", texto)
        or "CONNECTA ASSESSORIA ADUANEIRA LTDA"
    )
    d["cnpj"] = (
        buscar(r"CONNECTA ASSESSORIA ADUANEIRA[^\n]*?CNPJ\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", texto)
        or CNPJ_CONNECTA
    )

    # Referências (linha do cabeçalho, ACIMA do slice): interna CNN26/0863 + cliente A 0020-26.
    m = re.search(r"(CNN\d{2}/\d{4})\s+(\S+)", texto)
    d["processo"] = m.group(1) if m else None            # ref interna do despachante
    d["referencia"] = m.group(2) if m else d["processo"]  # ref cliente A = chave de consolidação

    # Bloco câmbio / valor aduaneiro (espelha o WIN; usa sempre a coluna BRL).
    d["taxa_cambial"] = buscar_valor(r"TAXA CAMBIAL\s+USD\s+([\d.]+,\d+)", fat)
    d["fob"] = _linha_cambio(fat, "FOB")
    d["frete"] = _linha_cambio(fat, "FRETE")
    d["seguro"] = _linha_cambio(fat, "SEGURO")

    m = re.search(
        r"^VALOR ADUANEIRO\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})(?:\s+R\$\s*([\d.]+,\d{2}))?",
        fat,
        re.MULTILINE | re.IGNORECASE,
    )
    d["valor_aduaneiro"] = parse_valor_br(m.group(2)) if m else None
    # Numerário/adiantamento à direita da linha VALOR ADUANEIRO (crédito do Passo 6.2).
    d["adiantamento_total"] = parse_valor_br(m.group(3)) if (m and m.group(3)) else None
    d["adiantamentos"] = []

    # Despesas + totais (dentro do slice).
    d["despesas"] = _despesas(fat)
    d["creditos"] = []  # layout sem coluna C/D
    d["total"] = buscar_valor(r"^TOTAL\s+R\$\s*([\d.]+,\d{2})", fat, flags=re.MULTILINE | re.IGNORECASE)
    d["saldo"] = buscar_valor(r"^SALDO\s+R\$\s*([\d.]+,\d{2})", fat, flags=re.MULTILINE | re.IGNORECASE)

    # Dados bancários (rodapé, fora do slice).
    d["dados_bancarios"] = {
        "pix": buscar(r"PIX:\s*(\S+)", texto),
        "banco": buscar(r"\bBANCO\s+(\S+)", texto),
        "agencia": buscar(r"AG[ÊE]NCIA\s+([\d-]+)", texto),
        "conta": buscar(r"C/CORRENTE\s+([\d-]+)", texto),
    }

    return d
