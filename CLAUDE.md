# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A **throwaway mockup** (not production) that validates a workflow for the Aconsult accounting firm: read the PDFs of a single Brazilian import process, extract the fields automatically, let an operator review/complete the accounting-only fields (the *Middleware* layer), and generate CSV files for internal control and for the **Domínio** accounting system. No database, login, or deploy.

`spec.md` is the source of truth for scope. `INSTRUCOES_CLAUDE_CODE.md` is the original build plan and — critically — its **Anexo A** holds the real expected extraction values used by the tests. When something conflicts, `spec.md` wins.

## Commands

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload   # serves API + frontend at http://localhost:8000
pytest                              # runs all tests
pytest tests/test_extractors.py::TestDuimp1159 -q   # single test class
pytest tests/test_extractors.py::TestDuimp1159::test_tributos   # single test
```

There is no linter configured despite `.ruff_cache/` being gitignored. Python 3.11+.

## Architecture: the extraction pipeline

The whole system is one linear pipeline. Follow the data through these stages:

1. **`pdf_utils.extract_text`** — pulls raw text from a PDF via `pdfplumber` (pages joined by `\n`). No OCR; assumes a text layer exists.
2. **`detector.detectar_tipo`** — classifies a document **by its text content, never by filename**, into `TipoDocumento` (DUIMP / DI / NOTA_FISCAL / FECHAMENTO_TERRA / FECHAMENTO_WIN / DESCONHECIDO). Order matters: the despachante closings (matched by CNPJ or header) are checked *before* DUIMP/DI/NF to avoid misclassification.
3. **`extractors/*.py`** — one module per document type, each exposing `extrair(texto) -> dict`. The returned dict always carries `"tipo": <value>` plus that document's fields. `extractors/comum.py` holds the shared "RESUMO DE VALORES / TRIBUTOS" block parser reused by both `di.py` and `duimp.py`. Extractors are regex-heavy and **calibrated against the real sample PDFs in `assets/`** — changing a regex risks breaking a specific fixture assertion.
> **Two DUIMP layouts / two NF layouts.** `duimp.extrair` sub-dispatches by content: `_extrair_resumo` (1159, RESUMO blocks) vs `_extrair_vmcv` (SY1453, `VMCV`/`DEMONSTRATIVO DE CALCULOS`). `nota_fiscal` covers both DANFE variants. **CBS/IBS come from the NF-e** (Info. Complementares), not the DUIMP (which only prints `cClassTrib`). Supported despachantes: **TERRA, WIN, SYNDEX** (`fechamento_syndex`, anchored on CNPJ `02.286.106/0002-00`; note the word "SYNDEX" also appears inside the DUIMP, so the CNPJ is the anchor).

4. **`consolidador.consolidar`** — merges the list of per-document dicts into one `ProcessoExtraido`. This is the heart of the business logic:
   - Field selection uses `pega(campo, [(fonte, valor), ...])` with sources in **priority order DUIMP/DI > NF > Fechamento**. First non-empty wins.
   - **Raw extraction only — no reconciliation.** When a lower-priority source disagrees with the chosen value, it is *not* corrected; a `divergencia` `Aviso` is appended. Missing critical fields (`_CRITICOS`) produce an `ausente` `Aviso`. Every chosen value is logged to `rastreamento` (feeds the traceable Saída A).
   - Process key = the reference (`1159#` → `1159`), falling back to the DI/DUIMP number or NF process.
5. **`depara.py`** — two models: (a) **papel-de-conta → código** (`PapelConta` + `PLANO_CONTAS_PADRAO`, e.g. `CONTA_PROCESSO`→1648) that the motor references by *role*, overridable via middleware; (b) **line classification** (`classificar_linha` → `CategoriaLinha`) that drives the anti-double-count guard. Plus the legacy TERRA/WIN seed.
6. **`contabilizador.py`** — the **POP posting engine** (`gerar_partidas`, spec §1.5 / Passos 5–9). Builds Saída B's D/C entries: Passo 5.1 (NF entry, D IMPORTAÇÕES EM ANDAMENTO / C CONTA_PROCESSO), 5.2 (D CONTA_PROCESSO / C FORNECEDOR, value = `resultado_rs` = invoice_usd × tx_di), 6.2 (one lote, one debit per `DESPESA_PROCESSO` line / C ADIANTAMENTO), 8 (câmbio variation, only if middleware supplies it). **Guard (critical):** federal taxes in the fechamento are classified `tributo_federal_na_nf` and are NOT re-posted — they already enter via the NF in Passo 5; re-posting would double-count ~89k. The engine references account *roles*, never hardcoded codes; an unseeded role emits an `Aviso` instead of inventing a code.
7. **`outputs.py`** — generates the deliverables (see below).

**`main.py`** wires it together over FastAPI:
- `POST /extract` — accepts 1..N PDFs, runs steps 1–5, returns the `ProcessoExtraido` JSON plus `nao_reconhecidos` and `sugestoes_middleware`.
- `POST /generate` — takes the (operator-edited) `GerarRequest` (`processo` + `middleware`) and returns a `.zip` of the output files.
- `GET /` serves `frontend/index.html`; `/static` mounts the frontend dir.
- The frontend (`frontend/app.js`, plain JS, no framework) renders every `ProcessoExtraido` field as an editable form, then the Middleware fields, then calls `/generate`.

## Output files (`outputs.py`)

- **Saída A** (`saida_A_extracao.csv`) — v0.2 layout (`COLUNAS_A`, ~40 cols): includes the control-sheet câmbio columns 1–8 (Invoice USD, TX DI, **Resultado R$**, câmbio 4–8) and the Reforma (CBS/IBS-UF/IBS-MUN). Plus `saida_A_rastreavel.csv` (`Processo;Documento;Campo;Valor;Fonte`).
- **Saída B** (`saida_B_lancamentos_dominio.csv` + `.txt`) — Domínio entries, now produced by `contabilizador.gerar_partidas`. **Exactly 10 columns, `;`-delimited, NO header**, matching the `Sub Gerar()` macro: `Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;CC Débito;CC Crédito`. (`Lancamento.lote`/`.passo` are internal metadata, not columns.)
- **Saída C** (`saida_C_fornecedores.csv`) — optional supplier registry, only when `incluir_saida_c` is set.

Number formatting is locale-critical: `fmt_br` produces human `1.234,56`; `fmt_dominio` produces the macro's `1234,56` (comma decimal, no thousands separator). CSV content is written with a leading BOM (`﻿`) in the zip so Excel PT-BR opens it correctly.

## Conventions specific to this codebase

- **Brazilian formats throughout.** Values are `1.234,56` (dot=thousands, comma=decimal). Dates stay as `dd/mm/aaaa` strings; do not convert to serial/ISO.
- **Two parsers, two jobs — never cross them.** `pdf_utils.parse_valor_br` is **exclusively** for raw PDF text (where `.` is a thousands separator). `pdf_utils.coerta_valor` is the **only** place a value coming from a request/model is coerced (form round-trip): there a `.` is a thousands separator *only* when a `,` decimal is present, so the JS float string `"382358.58"` is not mangled into 38 million. **Never apply `parse_valor_br` to request/model data**, and never re-parse a value that was already a `float`. Numeric model fields use the `ValorOpt`/`ValorReq` annotated types (which run `coerta_valor`).
- **Every value that crosses the form↔backend boundary needs a round-trip test** (`/extract → edit → /generate`), not just an extraction test. Extraction tests pass while the round-trip silently corrupts — that is exactly the gap that let the decimal bug through. When adding a numeric field, extend the round-trip tests in `test_api.py`.
- **Never break on a missing document.** A process may be DUIMP+NF only, or DI+Fechamento only. Extractors and the consolidator must tolerate absent types — return `None`/empty and record an `Aviso` instead of raising.
- **Missing field → `None` + an aviso, never a fabricated value.**
- Three despachante closing layouts are supported: **TERRA** (`05.989.453/0001-06`), **WIN** (`26.316.473/0002-77`), **SYNDEX** (`02.286.106/0002-00`). Fechamentos return expenses as a list of `{descricao, valor, vencimento?, tipo}`. `fechamento_syndex` is anchored on **labels** (not token indices) — do not reintroduce the positional-token fragility of TERRA/WIN.
- **CBS/IBS and câmbio are parametrized, never hardcoded:** extracted and reserved; their postings stay pending the Larissa rule (`middleware.tratamento_cbs_ibs`). Accounting decisions still open are encoded as `xfail` tests (Passo 5.1 value; whether ICMS joins Passo 6.2) — see `ANEXO_A_SY1453.md` and `test_motor_partidas.py`.
- Code, comments, and identifiers are in **Portuguese** — match that when editing.

## Testing

Tests in `tests/` use the real PDFs as fixtures (`conftest.py` extracts and session-caches text via the `textos` fixture). Legacy samples live in `assets/` (1159 = DUIMP+NF; 870 = DI+TERRA; WIN standalone = ENC-153) with expected values in `INSTRUCOES_CLAUDE_CODE.md` Anexo A. The SY1453/SYNDEX kit lives in `assets/corpus/sy1453_syndex/` (resolved by glob in conftest) with expected values in `ANEXO_A_SY1453.md`; three of its files are scanned (no text layer) and out of scope. `assets/corpus/` also holds three other processes (982/CMO, ALL TIME, Fortress) kept as reference, not tested. When adjusting an extractor, run its specific test class — fixtures pin concrete values.
