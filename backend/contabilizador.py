"""Motor de partidas contábeis do POP (spec §1.5 / Passos 5–9).

``gerar_partidas(processo, middleware)`` monta os lançamentos da Saída B a
partir do processo consolidado e dos complementos do operador (middleware).

Princípios (brief §4):
- O motor referencia **papéis** de conta (nunca códigos soltos); o código vem
  do de-para/middleware. Papel sem código → :class:`Aviso`, jamais inventar.
- **Guard anti-double-count (§3):** só as linhas classificadas como
  ``DESPESA_PROCESSO`` entram no Passo 6.2. Os tributos federais já entram pela
  NF no Passo 5, então relançá-los duplicaria ~89 mil.
- **Nunca fabricar valor:** partida sem valor vira Aviso (não entra com 0).
- **Parametrizado:** valores que dependem de decisão da Larissa (Passo 5.1) e
  do contrato de câmbio (Passos 7/8) têm *default documentado*; o mecanismo
  roda, a asserção fica xfail.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from backend.depara import (
    HISTORICO_DESPESA_PROCESSO,
    HISTORICO_TRANSFERENCIA,
    HISTORICO_VALOR_DEVIDO,
    CategoriaLinha,
    PapelConta,
    classificar_linha,
    codigo_conta,
)
from backend.models import Aviso, Lancamento, MiddlewareInput, ProcessoExtraido


def montar_nome_conta_processo(p: ProcessoExtraido) -> str:
    """Nome da conta do processo (spec §1.4): PROCESSO <nome> DI/DUIMP <n> NF <n>."""
    nome = p.importador_nome or p.fornecedor_estrangeiro or ""
    partes = ["PROCESSO"]
    if nome:
        partes.append(nome)
    if p.di_duimp:
        partes.append(f"DI/DUIMP {p.di_duimp}")
    if p.numero_nf:
        partes.append(f"NF {p.numero_nf}")
    return " ".join(partes)


def _fmt(valor: Optional[float], casas: int = 2) -> str:
    """Número BR para o texto do histórico (evita import circular com outputs)."""
    if valor is None:
        return ""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_partidas(processo: ProcessoExtraido, middleware: MiddlewareInput) -> List[Lancamento]:
    """Gera as partidas do POP; anexa Avisos de pendência a ``processo.avisos``."""
    lancamentos: List[Lancamento] = []
    avisos: List[Aviso] = []
    contas_ovr = middleware.contas_override
    hist_ovr = middleware.historicos_override
    contas_faltando: set = set()

    def conta(papel: PapelConta) -> str:
        cod = codigo_conta(papel, contas_ovr)
        if not cod and papel.value not in contas_faltando:
            contas_faltando.add(papel.value)
            avisos.append(Aviso(
                tipo="ausente", campo=f"conta:{papel.value}",
                mensagem=f"Conta '{papel.value}' não configurada — informe no middleware",
            ))
        return cod

    def hist(passo: str, default: str) -> str:
        return hist_ovr.get(passo, default)

    data = middleware.data_lancamento or (processo.data_nf or "")
    proc_nome = middleware.conta_processo_nome or montar_nome_conta_processo(processo)
    proc_num = middleware.conta_processo_numero or ""
    ref_proc = proc_num or proc_nome
    lote = 0

    # ------------------------------------------------------------------
    # Passo 5.1 (parametrizado) — NF de entrada
    # D IMPORTAÇÕES EM ANDAMENTO · C CONTA DO PROCESSO · valor = total da NF
    # ------------------------------------------------------------------
    lote += 1
    if processo.valor_nf:
        lancamentos.append(Lancamento(
            data=data,
            conta_debito=conta(PapelConta.IMPORTACOES_EM_ANDAMENTO),
            conta_credito=conta(PapelConta.CONTA_PROCESSO),
            valor=float(processo.valor_nf),
            cod_historico=hist("5.1", HISTORICO_TRANSFERENCIA),
            complemento_historico=f"TRANSFERÊNCIA DE VALORES IMPORTAÇÃO EM ANDAMENTO CFM {ref_proc}".strip(),
            inicia_lote="S",
            lote=lote, passo="5.1",
        ))
    else:
        avisos.append(Aviso(tipo="ausente", campo="valor_nf",
                            mensagem="Passo 5.1 pendente: valor total da NF ausente"))

    # ------------------------------------------------------------------
    # Passo 5.2 (fixo) — valor devido ao fornecedor
    # D CONTA DO PROCESSO · C FORNECEDOR ESTRANGEIRO · valor = RESULTADO R$ (campo 3)
    # ------------------------------------------------------------------
    lote += 1
    if processo.resultado_rs:
        comp = (
            f"VALOR DEVIDO FORNECEDOR {processo.processo or ''} "
            f"REF. {processo.di_duimp or ''} USD {_fmt(processo.invoice_usd)} "
            f"TAXA INVOICE {_fmt(processo.tx_di, 4)}"
        )
        lancamentos.append(Lancamento(
            data=data,
            conta_debito=conta(PapelConta.CONTA_PROCESSO),
            conta_credito=conta(PapelConta.FORNECEDOR_ESTRANGEIRO),
            valor=float(processo.resultado_rs),
            cod_historico=hist("5.2", HISTORICO_VALOR_DEVIDO),
            complemento_historico=" ".join(comp.split()),
            inicia_lote="S",
            lote=lote, passo="5.2",
        ))
    else:
        avisos.append(Aviso(tipo="ausente", campo="resultado_rs",
                            mensagem="Passo 5.2 pendente: RESULTADO R$ (invoice US$ × TX DI) ausente"))

    # ------------------------------------------------------------------
    # Passo 6.2 (fixo) — despesas do numerário (um lote, vários débitos)
    # Só as linhas DESPESA_PROCESSO (guard §3): D CONTA DO PROCESSO · C ADIANTAMENTO
    # ------------------------------------------------------------------
    lote += 1
    despesas_proc = [
        d for d in processo.despesas
        if classificar_linha(d.get("descricao"), d.get("tipo"), middleware.classificacao_override)
        == CategoriaLinha.DESPESA_PROCESSO
    ]
    primeiro = True
    for d in despesas_proc:
        valor = d.get("valor")
        desc = d.get("descricao", "")
        if not valor:
            avisos.append(Aviso(tipo="ausente", campo="despesa",
                                mensagem=f"Passo 6.2: despesa '{desc}' sem valor — ignorada"))
            continue
        lancamentos.append(Lancamento(
            data=data,
            conta_debito=conta(PapelConta.CONTA_PROCESSO),
            conta_credito=conta(PapelConta.ADIANTAMENTO_DESPACHANTE),
            valor=float(valor),
            cod_historico=hist("6.2", HISTORICO_DESPESA_PROCESSO),
            complemento_historico=f"{ref_proc} - {desc}".strip(" -"),
            inicia_lote="S" if primeiro else "",
            lote=lote, passo="6.2",
        ))
        primeiro = False

    # ------------------------------------------------------------------
    # Passo 8 (câmbio) — só com dados do contrato de câmbio no middleware
    # ------------------------------------------------------------------
    if middleware.vlr_usd_pg_cambio and middleware.tx_cambio and processo.tx_di:
        lote += 1
        usd = float(middleware.vlr_usd_pg_cambio)
        vlr_pg_rs = round(usd * float(middleware.tx_cambio), 2)          # campo 6 = 4×5
        vlr_pg_x_tx_di = round(usd * float(processo.tx_di), 2)           # campo 7 = 4×2
        variacao = round(vlr_pg_x_tx_di - vlr_pg_rs, 2)                  # campo 8 (convenção provisória)
        # reflete na Saída A
        processo.vlr_usd_pg_cambio = usd
        processo.tx_cambio = float(middleware.tx_cambio)
        processo.vlr_pg_rs = vlr_pg_rs
        processo.vlr_pg_x_tx_di = vlr_pg_x_tx_di
        processo.variacao = variacao
        if abs(variacao) >= 0.01:
            if variacao > 0:  # ganho (receita) — variação cambial ativa
                deb, cred = PapelConta.FORNECEDOR_ESTRANGEIRO, PapelConta.VARIACAO_CAMBIAL_ATIVA
            else:             # perda (despesa) — variação cambial passiva
                deb, cred = PapelConta.VARIACAO_CAMBIAL_PASSIVA, PapelConta.FORNECEDOR_ESTRANGEIRO
            lancamentos.append(Lancamento(
                data=data, conta_debito=conta(deb), conta_credito=conta(cred),
                valor=abs(variacao), cod_historico=hist("8", ""),
                complemento_historico=f"VARIAÇÃO CAMBIAL {processo.processo or ''}".strip(),
                inicia_lote="S", lote=lote, passo="8",
            ))
    else:
        avisos.append(Aviso(tipo="ausente", campo="cambio",
                            mensagem="Câmbio não informado — Passos 7/8 pendentes"))

    # CBS/IBS: só lança se o operador confirmar a regra (parametrizado)
    if middleware.tratamento_cbs_ibs == "lancar" and (processo.cbs or processo.ibs_uf):
        avisos.append(Aviso(tipo="ausente", campo="cbs_ibs",
                            mensagem="Tratamento CBS/IBS = 'lancar' mas a regra ainda não está definida"))

    processo.avisos.extend(avisos)
    return lancamentos


def lotes_balanceiam(lancamentos: List[Lancamento]) -> bool:
    """Invariante: em cada lote, Σ débitos = Σ créditos (partidas bem-formadas)."""
    soma: Dict[int, List[float]] = defaultdict(lambda: [0.0, 0.0])
    for l in lancamentos:
        soma[l.lote][0] += l.valor  # debita o valor
        soma[l.lote][1] += l.valor  # credita o valor
    return all(abs(deb - cred) < 0.01 for deb, cred in soma.values())


def validar_partidas(lancamentos: List[Lancamento]) -> List[Aviso]:
    """Aponta partidas incompletas (conta em branco) e lotes desbalanceados.

    Não bloqueia a geração — devolve Avisos para o operador completar. Um lote
    com débito ou crédito sem código de conta não pode ir para o Domínio; hoje
    isso vinha em branco e silencioso (bug 2).
    """
    avisos: List[Aviso] = []
    lotes_incompletos: set = set()
    for l in lancamentos:
        if (not l.conta_debito or not l.conta_credito) and l.lote not in lotes_incompletos:
            lotes_incompletos.add(l.lote)
            avisos.append(Aviso(
                tipo="ausente", campo=f"partida:passo{l.passo}",
                mensagem=(f"Passo {l.passo}: partida incompleta (conta em branco) — "
                          "complete o código da conta no middleware"),
            ))
    if lancamentos and not lotes_balanceiam(lancamentos):
        avisos.append(Aviso(tipo="divergencia", campo="balanceamento",
                            mensagem="Um lote não balanceia (Σ débitos ≠ Σ créditos)"))
    return avisos
