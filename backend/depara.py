"""Tabela de-para (seed simples e editável).

Pré-preenche contas contábeis e código de histórico a partir do **fornecedor
estrangeiro** e do **tipo de despesa**. É proposital que seja pequena: a ideia
é mostrar o mecanismo e deixar a estrutura pronta para crescer (em produção,
viraria uma tabela em banco).
"""
from __future__ import annotations

from typing import Dict, Optional

# fornecedor estrangeiro (trecho do nome em MAIÚSCULAS) -> conta do fornecedor + histórico padrão
DEPARA_FORNECEDOR: Dict[str, Dict[str, str]] = {
    "SHANGHAI YESOP": {"conta": "12374", "cod_historico": "25"},
    "HONGKONG YESOP": {"conta": "12374", "cod_historico": "25"},
    "HANGZHOU EQUIPMAX": {"conta": "12500", "cod_historico": "25"},
}

# tipo de despesa (trecho da descrição em MAIÚSCULAS) -> conta débito + histórico
DEPARA_DESPESA: Dict[str, Dict[str, str]] = {
    "AFRMM": {"conta_debito": "5210", "cod_historico": "59"},
    "ICMS": {"conta_debito": "5215", "cod_historico": "59"},
    "FRETE": {"conta_debito": "5220", "cod_historico": "56"},
    "ARMAZENAGEM": {"conta_debito": "5230", "cod_historico": "56"},
    "COMISSAO": {"conta_debito": "5240", "cod_historico": "56"},
    "TARIFA BANCARIA": {"conta_debito": "5250", "cod_historico": "56"},
    "SISCOMEX": {"conta_debito": "5260", "cod_historico": "59"},
    "IMPOSTOS DI": {"conta_debito": "5270", "cod_historico": "59"},
    "HONORARIOS": {"conta_debito": "5280", "cod_historico": "56"},
    "DESPACHO": {"conta_debito": "5280", "cod_historico": "56"},
}

# Conta crédito padrão (ex.: banco/adiantamento) quando não há regra específica.
CONTA_CREDITO_PADRAO = "805"


def _match(tabela: Dict[str, Dict[str, str]], chave: Optional[str]) -> Optional[Dict[str, str]]:
    if not chave:
        return None
    alvo = chave.upper()
    for trecho, valores in tabela.items():
        if trecho in alvo:
            return valores
    return None


def sugerir_fornecedor(nome: Optional[str]) -> Optional[Dict[str, str]]:
    """Sugestão de conta/histórico a partir do fornecedor estrangeiro."""
    return _match(DEPARA_FORNECEDOR, nome)


def sugerir_despesa(descricao: Optional[str]) -> Dict[str, str]:
    """Sugestão de conta débito/crédito e histórico para uma despesa.

    Sempre retorna um dicionário (com vazios quando não há regra), para
    facilitar o pré-preenchimento no front-end.
    """
    regra = _match(DEPARA_DESPESA, descricao) or {}
    return {
        "conta_debito": regra.get("conta_debito", ""),
        "conta_credito": CONTA_CREDITO_PADRAO,
        "cod_historico": regra.get("cod_historico", ""),
    }
