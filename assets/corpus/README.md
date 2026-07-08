# Corpus de documentos reais — por processo

Os PDFs em `assets/novos_arquivos/` (upload avulso) foram **triados por processo** na Fase 0 da
Fatia 1 (ver `ANEXO_A_SY1453.md`). A pasta original misturava **4 processos distintos**.

| Pasta | Processo | Despachante | Uso |
|---|---|---|---|
| `sy1453_syndex/` | **SY1453/26** — DUIMP `26BR0000258971-1` (ENCATEX) | **SYNDEX** | **Fixtures dos testes** (kit-alvo da Fatia 1A) |
| `982_cmo_terra/` | **982 / CMO** (ZINLOG → CMO) | TERRA | Referência (sem teste) |
| `26_0058_alltime/` | **26/0058** — DI `26/0418027-7` (ALL LAB) | **ALL TIME** | Amostra ALL TIME — **texto OCR degradado**, documenta o gap da Fatia 2 |
| `fortress/` | **IM25/00171** (ZINLOG, freight forwarder) | Fortress | Referência (sem teste) |

## Arquivos sem camada de texto (escaneados) — conferência manual

`pdf_utils.extract_text` retorna vazio nestes; ficam versionados como **evidência**, não são parseados
(OCR fora de escopo — spec §10):

- `sy1453_syndex/BILL OF LADING.pdf`
- `sy1453_syndex/NUMERARIO - SY1453-26 - 2025ECX067_RECIBO.pdf` — comprovante Pix do adiantamento `101.645,23`
- `sy1453_syndex/NUMERARIO - SY1453-26 - 2025ECX067_(COMPLEMENTO)_RECIBO.pdf` — comprovante Pix `2.090,00`

Os dois recibos Pix são a evidência dos dois `ADIANTAMENTO DE NUMERÁRIO` do fechamento SYNDEX; o
operador confirma no middleware.
