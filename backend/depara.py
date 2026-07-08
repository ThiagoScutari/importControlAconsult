"""Tabela de-para (seed simples e editável).

Dois modelos convivem aqui:

1. **Papel-de-conta → código** (:class:`PapelConta` + :data:`PLANO_CONTAS_PADRAO`):
   o motor de partidas (``contabilizador.py``) referencia sempre um *papel*
   contábil (ex.: ``CONTA_PROCESSO``), nunca um código solto. O código é um
   *default* do POP, **sobreponível pelo middleware**. Assim, a resposta da
   Larissa vira preenchimento de tabela, não alteração de código.

2. **Classificação de linha do fechamento** (:class:`CategoriaLinha` +
   :func:`classificar_linha`): resolve o *guard anti-double-count* (spec/brief
   §3). Cada rubrica do fechamento recebe uma categoria; só as
   ``DESPESA_PROCESSO`` entram no Passo 6.2 (as demais já entraram pela NF no
   Passo 5). O mapa default está semeado e é editável (dropdown na demo).

O de-para legado (fornecedor→conta, despesa→conta/histórico) da macro original
é mantido para o fluxo TERRA/WIN já existente.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# 1. Papéis de conta contábil (o motor referencia papel, não código)
# ---------------------------------------------------------------------------

class PapelConta(str, Enum):
    """Papel contábil de uma conta no algoritmo do POP (spec §1.5)."""

    IMPORTACOES_EM_ANDAMENTO = "importacoes_em_andamento"
    CONTA_PROCESSO = "conta_processo"
    FORNECEDOR_ESTRANGEIRO = "fornecedor_estrangeiro"
    ADIANTAMENTO_DESPACHANTE = "adiantamento_despachante"
    DESPACHANTE = "despachante"
    ESTOQUE = "estoque"
    SERVICO_TERCEIROS = "servico_terceiros"
    VARIACAO_CAMBIAL_ATIVA = "variacao_cambial_ativa"
    VARIACAO_CAMBIAL_PASSIVA = "variacao_cambial_passiva"
    BANCO = "banco"


# Códigos-exemplo observados no POP (spec §1.5). Confirmar por cliente; o
# middleware pode sobrescrever qualquer entrada. Papéis "a semear" ficam vazios
# de propósito (o operador informa) — nunca inventar um código.
PLANO_CONTAS_PADRAO: Dict[PapelConta, str] = {
    PapelConta.IMPORTACOES_EM_ANDAMENTO: "1633",
    PapelConta.CONTA_PROCESSO: "1648",
    PapelConta.FORNECEDOR_ESTRANGEIRO: "1177",
    PapelConta.ADIANTAMENTO_DESPACHANTE: "",   # a semear (operador)
    PapelConta.DESPACHANTE: "",                 # a semear (operador)
    PapelConta.ESTOQUE: "",                     # a semear (operador)
    PapelConta.SERVICO_TERCEIROS: "362",
    PapelConta.VARIACAO_CAMBIAL_ATIVA: "973",
    PapelConta.VARIACAO_CAMBIAL_PASSIVA: "370",
    PapelConta.BANCO: "",                       # a semear (operador)
}

# Históricos-modelo do Domínio observados no POP (spec §1.5).
HISTORICO_DESPESA_PROCESSO = "41"   # despesa referente ao processo (Passo 6.2)
HISTORICO_TRANSFERENCIA = "45"      # transferência (Passo 5.1)
HISTORICO_VALOR_DEVIDO = "46"       # valor devido ao fornecedor (Passo 5.2)


def codigo_conta(papel: PapelConta, overrides: Optional[Dict[str, str]] = None) -> str:
    """Código de uma conta pelo papel, aplicando os overrides do middleware.

    ``overrides`` é um dict ``{papel_value: codigo}`` vindo do middleware. Se o
    papel não tiver código (nem default nem override), retorna ``""`` — o motor
    registra um :class:`Aviso` em vez de inventar.
    """
    if overrides and papel.value in overrides and overrides[papel.value]:
        return overrides[papel.value]
    return PLANO_CONTAS_PADRAO.get(papel, "")


# ---------------------------------------------------------------------------
# 2. Classificação das linhas do fechamento (guard anti-double-count, §3)
# ---------------------------------------------------------------------------

class CategoriaLinha(str, Enum):
    """Categoria de uma rubrica do fechamento, para o guard do Passo 6.2."""

    TRIBUTO_FEDERAL_NA_NF = "tributo_federal_na_nf"  # já entrou pela NF (P5) -> NÃO relança
    DESPESA_PROCESSO = "despesa_processo"            # entra no Passo 6.2
    ICMS_IMPORTACAO = "icms_importacao"              # tratamento próprio (DARE/diferido)
    RETENCAO = "retencao"                            # crédito (retenção na NF de serviço)
    ADIANTAMENTO = "adiantamento"                    # crédito (numerário adiantado)


# Mapa ORDENADO (trecho MAIÚSCULO -> categoria). Ordem = prioridade: trechos mais
# específicos primeiro (ex.: "PIS IMPORTA" antes de "PIS"). Editável no middleware;
# a confirmação deste mapa é a pergunta contábil #1 para a Larissa (fica xfail).
CLASSIFICACAO_DESPESA_PADRAO = [
    ("IMPOSTO DE IMPORTA", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("I.P.I", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("PIS IMPORTA", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("COFINS IMPORTA", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("SISCOMEX", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("AFRMM", CategoriaLinha.TRIBUTO_FEDERAL_NA_NF),
    ("ICMS", CategoriaLinha.ICMS_IMPORTACAO),
    ("ADIANTAMENTO", CategoriaLinha.ADIANTAMENTO),
    ("IRRF", CategoriaLinha.RETENCAO),
    ("CSLL", CategoriaLinha.RETENCAO),
    ("COMISSAO", CategoriaLinha.DESPESA_PROCESSO),
    ("COMISSÃO", CategoriaLinha.DESPESA_PROCESSO),
    ("ARMAZENAGEM", CategoriaLinha.DESPESA_PROCESSO),
    ("SEGURO", CategoriaLinha.DESPESA_PROCESSO),
    ("BANCAR", CategoriaLinha.DESPESA_PROCESSO),   # DESPESAS BANCÁRIAS
    ("MOTO BOY", CategoriaLinha.DESPESA_PROCESSO),
    ("TARIFA", CategoriaLinha.DESPESA_PROCESSO),
    ("FRETE", CategoriaLinha.DESPESA_PROCESSO),
    # retenções "puras" (crédito) por último, para não capturar "PIS IMPORTA"
    ("PIS", CategoriaLinha.RETENCAO),
    ("COFINS", CategoriaLinha.RETENCAO),
]

# Categoria default quando nenhuma regra casa: DESPESA_PROCESSO (fica visível e
# editável no dropdown — o operador reclassifica se preciso).
CATEGORIA_DEFAULT = CategoriaLinha.DESPESA_PROCESSO


def classificar_linha(
    descricao: Optional[str],
    tipo: Optional[str] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> CategoriaLinha:
    """Classifica uma rubrica do fechamento.

    - ``tipo`` = ``"C"`` (crédito) força :attr:`CategoriaLinha.ADIANTAMENTO` ou
      :attr:`RETENCAO` conforme a descrição, pois créditos nunca são despesa.
    - ``overrides`` = ``{descricao_norm: categoria_value}`` do middleware; tem
      prioridade sobre o mapa default.
    """
    if descricao is None:
        return CATEGORIA_DEFAULT
    alvo = descricao.upper()

    if overrides:
        for chave, cat in overrides.items():
            if chave and chave.upper() in alvo:
                try:
                    return CategoriaLinha(cat)
                except ValueError:
                    pass

    for trecho, categoria in CLASSIFICACAO_DESPESA_PADRAO:
        if trecho in alvo:
            # créditos só podem ser adiantamento ou retenção
            if tipo == "C" and categoria not in (CategoriaLinha.ADIANTAMENTO, CategoriaLinha.RETENCAO):
                return CategoriaLinha.RETENCAO
            return categoria

    if tipo == "C":
        return CategoriaLinha.ADIANTAMENTO
    return CATEGORIA_DEFAULT


# ---------------------------------------------------------------------------
# De-para legado (macro original) — usado pelo fluxo TERRA/WIN existente
# ---------------------------------------------------------------------------

# fornecedor estrangeiro (trecho do nome em MAIÚSCULAS) -> conta do fornecedor + histórico padrão
DEPARA_FORNECEDOR: Dict[str, Dict[str, str]] = {
    "SHANGHAI YESOP": {"conta": "12374", "cod_historico": "25"},
    "HONGKONG YESOP": {"conta": "12374", "cod_historico": "25"},
    "HANGZHOU EQUIPMAX": {"conta": "12500", "cod_historico": "25"},
    "HONG KONG ALLIANCE": {"conta": "12600", "cod_historico": "25"},
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
