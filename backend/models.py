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
    invoice_usd: Optional[float] = None
    cotacao: Optional[float] = None

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
    """Uma partida do layout Domínio (Saída B) — 10 colunas."""

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


class MiddlewareInput(BaseModel):
    """Campos confirmados/preenchidos pelo operador antes de gerar."""

    tipo_importacao: Optional[str] = None
    entidade_contabil: Optional[str] = None
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
