"""Schemas Pydantic do mockup.

- :class:`ProcessoExtraido`: visão consolidada de 1 processo (espelha a Saída A).
- :class:`MiddlewareInput`: campos que o operador confere/preenche (seção 6).
- :class:`Lancamento`: uma partida do layout Domínio (Saída B).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
    valor_nf: Optional[float] = None
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
    invoice_usd: Optional[float] = None  # campo 1 — VALOR INVOICE US$ (Invoice > VMCV DUIMP)
    cotacao: Optional[float] = None

    # Planilha de controle — colunas 1–8 (spec §1.3)
    tx_di: Optional[float] = None            # campo 2 — taxa da DI/DUIMP
    resultado_rs: Optional[float] = None     # campo 3 — 1×2, provisão do fornecedor
    vlr_usd_pg_cambio: Optional[float] = None  # campo 4 — do contrato de câmbio (middleware)
    tx_cambio: Optional[float] = None        # campo 5 — do contrato de câmbio (middleware)
    vlr_pg_rs: Optional[float] = None        # campo 6 — 4×5
    vlr_pg_x_tx_di: Optional[float] = None   # campo 7 — 4×2
    variacao: Optional[float] = None         # campo 8 — variação cambial

    # Reforma tributária (extraídos e reservados — regra de partida a confirmar)
    cbs: Optional[float] = None
    ibs_uf: Optional[float] = None
    ibs_mun: Optional[float] = None
    cclasstrib: Optional[str] = None

    # Valores
    fob_rs: Optional[float] = None
    frete_rs: Optional[float] = None
    valor_aduaneiro_rs: Optional[float] = None

    # Tributos / despesas
    ii: Optional[float] = None
    ipi: Optional[float] = None
    pis: Optional[float] = None
    cofins: Optional[float] = None
    siscomex: Optional[float] = None
    afrmm: Optional[float] = None
    icms: Optional[float] = None
    armazenagem: Optional[float] = None
    total_tributos: Optional[float] = None

    # Carga
    peso_liquido: Optional[float] = None
    volumes: Optional[float] = None
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
    valor: float = 0.0
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
    vlr_usd_pg_cambio: Optional[float] = None
    tx_cambio: Optional[float] = None

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
