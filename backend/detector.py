"""Identifica o tipo de um documento pelo seu **conteúdo** (não pelo nome).

Ordem de verificação (spec §3 / [R3]):

1. **Fechamentos suportados** (TERRA/WIN/SYNDEX/ALL TIME) — âncoras FORTES e
   específicas do cabeçalho/CNPJ. Checados ANTES das declarações porque o
   fechamento é um *dossiê* que embute a DUIMP/DI/NF-e e os anexos, e casaria
   com as âncoras deles. **Não** ancorar em CNPJ solto nem em frase genérica:
   a NFS-e do porto carrega o CNPJ do despachante, e "DEMONSTRATIVO DE DESPESAS"
   aparece também no ALL TIME.
2. **Declaração / NF-e de importação** — âncoras próprias ("Extrato da Duimp",
   "Extrato da Declaração"/"Declaração: NN/NNNNNNN-N", "DANFE").
3. **Só-imagem / quase-vazio** → `ANEXO_REFERENCIA` (imagem). OCR fica p/ Fatia 2.
4. **Anexos de referência** reconhecíveis (NFS-e de serviço, CT-e/DACTE, boleto,
   GRU, DARE, BL, comprovantes) → `ANEXO_REFERENCIA` — reconhecidos e ignorados
   com calma, sem cair no parser errado nem virar "tipo não reconhecido".
"""
from __future__ import annotations

import re
from enum import Enum


class TipoDocumento(str, Enum):
    DUIMP = "duimp"
    DI = "di"
    NOTA_FISCAL = "nota_fiscal"
    FECHAMENTO_TERRA = "fechamento_terra"
    FECHAMENTO_WIN = "fechamento_win"
    FECHAMENTO_SYNDEX = "fechamento_syndex"
    FECHAMENTO_ALLTIME = "fechamento_alltime"  # [F1-03] despachante ALL TIME (+ Rhenus)
    FECHAMENTO_CONNECTA = "fechamento_connecta"  # [F1-11] despachante CONNECTA (layout FATURAMENTO)
    ANEXO_REFERENCIA = "anexo_referencia"  # [F1-02] anexo/referência (incl. só-imagem)
    DESCONHECIDO = "desconhecido"


# CNPJs dos despachantes (âncora confiável só quando é o EMITENTE do fechamento;
# ver nota abaixo — a NFS-e do porto também traz o CNPJ do despachante).
CNPJ_TERRA = "05.989.453/0001-06"
CNPJ_WIN = "26.316.473/0002-77"
CNPJ_SYNDEX = "02.286.106/0002-00"

# Abaixo deste tamanho de texto, o PDF é tratado como só-imagem/quase-vazio
# (escaneado sem camada de texto) → ANEXO/REFERÊNCIA, não "desconhecido".
LIMIAR_TEXTO_MINIMO = 40

# Marcadores de anexos de referência (não são fonte de dado nesta fatia). Só são
# avaliados DEPOIS dos tipos suportados, então o dossiê do fechamento (que embute
# NFS-e/CT-e/GRU) já foi classificado corretamente antes de chegar aqui.
_MARCADORES_ANEXO = (
    "NOTA FISCAL DE SERV", "NFS-E", "NFSE",             # NFS-e de serviço
    "DACTE", "CT-E", "CONHECIMENTO DE TRANSPORTE",       # CT-e / frete rodoviário
    "GUIA DE RECOLHIMENTO", "INMETRO",                   # GRU
    "DARE",                                              # DARE-SC (ICMS)
    "BILL OF LADING",                                    # BL / MTD
    "FICHA DE COMPENSA", "LINHA DIGIT", "NOSSO N",       # boleto
    "COMPROVANTE", "RECIBO",                             # comprovantes Pix/TED
)


def _eh_anexo_referencia(tu: str) -> bool:
    return any(m in tu for m in _MARCADORES_ANEXO)


def detectar_tipo(texto: str) -> TipoDocumento:
    """Retorna o :class:`TipoDocumento` correspondente ao texto extraído."""
    if not texto:
        return TipoDocumento.ANEXO_REFERENCIA  # PDF só-imagem (0 chars)

    t = texto
    tu = texto.upper()

    # 1) Fechamentos suportados — cabeçalho/CNPJ do emitente (antes das declarações).
    #    TERRA: o cabeçalho é "TERRA DESP. ADUANEIROS ... Nota de Despesas". Não usar
    #    o CNPJ como âncora: a NFS-e do porto (anexo) também carrega o CNPJ do TERRA.
    if "TERRA DESP. ADUANEIROS" in tu:
        return TipoDocumento.FECHAMENTO_TERRA
    if "WIN TRADING" in tu:
        return TipoDocumento.FECHAMENTO_WIN
    #    SYNDEX: âncora = CNPJ do despachante. A palavra "SYNDEX" também aparece na
    #    DUIMP (carta do despachante) e não serve; o CNPJ só está no fechamento/numerário.
    if CNPJ_SYNDEX in t:
        return TipoDocumento.FECHAMENTO_SYNDEX
    #    ALL TIME: cabeçalho "ALL TIME ... COMERCIO EXTERIOR" (ou o forwarder RHENUS).
    #    ANTES da DI: o fechamento ALL TIME embute a DI ("Extrato da Declaração").
    if ("ALL TIME" in tu and "COMERCIO EXTERIOR" in tu) or "RHENUS" in tu:
        return TipoDocumento.FECHAMENTO_ALLTIME
    #    CONNECTA: página de FATURAMENTO. Âncora dupla — nome do despachante MAIS o
    #    cabeçalho da tabela de despesas — p/ não casar uma NFS-e Connecta que apareça
    #    como anexo de OUTRO despachante. ANTES da DUIMP: o dossiê CONNECTA embute o
    #    Extrato da Duimp (7 ocorrências), que senão o roteava para DUIMP.
    if "CONNECTA ASSESSORIA ADUANEIRA" in tu and re.search(
        r"DESPESAS\s+COBRADOR\s+DATA DE PAGAMENTO", tu
    ):
        return TipoDocumento.FECHAMENTO_CONNECTA

    # 2) Declaração / NF-e de importação — âncoras específicas.
    if "EXTRATO DA DUIMP" in tu:
        return TipoDocumento.DUIMP
    if "EXTRATO DA DECLARA" in tu or re.search(r"DECLARA[ÇC][ÃA]O:\s*\d{2}/\d{7}-\d", tu):
        return TipoDocumento.DI
    #    A NF-e de importação imprime "DANFE"; a NFS-e/CT-e/boleto NÃO — evita o
    #    falso-positivo do CT-e (que contém "NF-e" como chave referenciada).
    if "DANFE" in tu:
        return TipoDocumento.NOTA_FISCAL

    # 3) Só-imagem / quase-vazio (escaneado sem camada de texto) → anexo (imagem).
    if len(texto.strip()) < LIMIAR_TEXTO_MINIMO:
        return TipoDocumento.ANEXO_REFERENCIA

    # 4) Anexos de referência reconhecíveis (não são fonte de dado nesta fatia).
    if _eh_anexo_referencia(tu):
        return TipoDocumento.ANEXO_REFERENCIA

    return TipoDocumento.DESCONHECIDO
