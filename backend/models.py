"""Schemas Pydantic do mockup.

- :class:`ProcessoExtraido`: visão consolidada de 1 processo (espelha a Saída A).
- :class:`MiddlewareInput`: campos que o operador confere/preenche (seção 6).
- :class:`Lancamento`: uma partida do layout Domínio (Saída B).
"""
from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, Field

from backend.pdf_utils import coerta_valor

# Tipo de valor numérico na fronteira: aceita float (extração) OU string do
# formulário (round-trip), coagindo com segurança — sem tratar ponto como milhar
# indevidamente. É o único ponto de parse de número vindo da requisição.
ValorOpt = Annotated[Optional[float], BeforeValidator(coerta_valor)]


def _valor_ou_zero(v) -> float:
    """Coação de valor obrigatório (partida): mesma regra do ValorOpt, default 0."""
    return coerta_valor(v) or 0.0


# Valor não-opcional (ex.: Lancamento.valor) coagido pela mesma regra de fronteira.
ValorReq = Annotated[float, BeforeValidator(_valor_ou_zero)]


class Aviso(BaseModel):
    """Mensagem de campo não encontrado ou divergência entre documentos."""

    tipo: str  # "ausente" | "divergencia"
    campo: str
    mensagem: str


class ProcessoExtraido(BaseModel):
    """Registro consolidado de um processo de importação (extração crua)."""

    processo: Optional[str] = None
    tipo_importacao: Optional[str] = None

    # Documento fiscal / declaração
    di_duimp: Optional[str] = None
    data_nf: Optional[str] = None
    numero_nf: Optional[str] = None
    valor_nf: ValorOpt = None
    chave_nfe: Optional[str] = None

    # Partes
    importador_nome: Optional[str] = None
    importador_cnpj: Optional[str] = None
    adquirente_nome: Optional[str] = None
    adquirente_cnpj: Optional[str] = None
    despachante: Optional[str] = None
    fornecedor_estrangeiro: Optional[str] = None
    fabricante: Optional[str] = None
    pais_origem: Optional[str] = None
    pais_aquisicao: Optional[str] = None

    # Invoice / câmbio
    invoice: Optional[str] = None
    invoice_usd: ValorOpt = None  # campo 1 — VALOR INVOICE US$ (Invoice > VMCV DUIMP)
    cotacao: ValorOpt = None

    # Planilha de controle — colunas 1–8 (spec §1.3)
    tx_di: ValorOpt = None            # campo 2 — taxa da DI/DUIMP
    resultado_rs: ValorOpt = None     # campo 3 — 1×2, provisão do fornecedor
    vlr_usd_pg_cambio: ValorOpt = None  # campo 4 — do contrato de câmbio (middleware)
    tx_cambio: ValorOpt = None        # campo 5 — do contrato de câmbio (middleware)
    vlr_pg_rs: ValorOpt = None        # campo 6 — 4×5
    vlr_pg_x_tx_di: ValorOpt = None   # campo 7 — 4×2
    variacao: ValorOpt = None         # campo 8 — variação cambial

    # Reforma tributária (extraídos e reservados — regra de partida a confirmar)
    cbs: ValorOpt = None
    ibs_uf: ValorOpt = None
    ibs_mun: ValorOpt = None
    cclasstrib: Optional[str] = None

    # Valores
    fob_rs: ValorOpt = None
    frete_rs: ValorOpt = None
    valor_aduaneiro_rs: ValorOpt = None

    # Tributos / despesas
    ii: ValorOpt = None
    ipi: ValorOpt = None
    pis: ValorOpt = None
    cofins: ValorOpt = None
    siscomex: ValorOpt = None
    afrmm: ValorOpt = None
    icms: ValorOpt = None
    armazenagem: ValorOpt = None
    total_tributos: ValorOpt = None

    # Carga
    peso_liquido: ValorOpt = None
    volumes: ValorOpt = None
    navio: Optional[str] = None
    bl: Optional[str] = None
    chegada: Optional[str] = None

    # Rastreabilidade
    documentos: List[Dict[str, Any]] = Field(default_factory=list)
    despesas: List[Dict[str, Any]] = Field(default_factory=list)
    avisos: List[Aviso] = Field(default_factory=list)
    rastreamento: List[Dict[str, Any]] = Field(default_factory=list)


class Lancamento(BaseModel):
    """Uma partida do layout Domínio (Saída B) — 10 colunas.

    ``lote`` e ``passo`` são metadados internos (não vão para o CSV): ``lote``
    agrupa as partidas de um mesmo lançamento (ex.: os vários débitos do Passo
    6.2) para checar o balanceamento; ``passo`` documenta a origem no POP.
    """

    data: str = ""
    conta_debito: str = ""
    conta_credito: str = ""
    valor: ValorReq = 0.0  # coagido na fronteira (aceita float, "382358.58" ou "382.358,58")
    cod_historico: str = ""
    complemento_historico: str = ""
    inicia_lote: str = ""
    matriz_filial: str = ""
    cc_debito: str = ""
    cc_credito: str = ""
    # metadados internos (fora das 10 colunas do CSV)
    lote: int = 0
    passo: str = ""


class MiddlewareInput(BaseModel):
    """Campos confirmados/preenchidos pelo operador antes de gerar.

    Tudo aqui é *regra de negócio / plano de contas* que não sai dos documentos
    (spec §5). Os defaults do de-para pré-preenchem; o operador ajusta.
    """

    tipo_importacao: Optional[str] = None
    entidade_contabil: Optional[str] = None

    # Conta do processo (nome gerado pela regra §1.4; número informado)
    conta_processo_nome: Optional[str] = None
    conta_processo_numero: Optional[str] = None

    # Papel-de-conta → código (sobrepõe PLANO_CONTAS_PADRAO) e histórico por papel
    contas_override: Dict[str, str] = Field(default_factory=dict)
    historicos_override: Dict[str, str] = Field(default_factory=dict)

    # Classificação das linhas do fechamento (descrição → categoria) — guard §3
    classificacao_override: Dict[str, str] = Field(default_factory=dict)

    # Câmbio (campos 4–5; 6/7/8 são calculados) — do contrato de câmbio, ausente aqui
    vlr_usd_pg_cambio: ValorOpt = None
    tx_cambio: ValorOpt = None

    # Reforma: "reservar" (default) ou "lancar" (quando a Larissa definir a regra)
    tratamento_cbs_ibs: str = "reservar"

    # Campos legados do fluxo TERRA/WIN (conta única) — mantidos por compat.
    conta_debito: Optional[str] = None
    conta_credito: Optional[str] = None
    cod_historico: Optional[str] = None
    complemento_historico: Optional[str] = None
    data_lancamento: Optional[str] = None
    inicia_lote: Optional[str] = None
    matriz_filial: Optional[str] = None
    cc_debito: Optional[str] = None
    cc_credito: Optional[str] = None
    incluir_saida_c: bool = False
    lancamentos: List[Lancamento] = Field(default_factory=list)


class GerarRequest(BaseModel):
    """Corpo do POST /generate."""

    processo: ProcessoExtraido
    middleware: MiddlewareInput = Field(default_factory=MiddlewareInput)
