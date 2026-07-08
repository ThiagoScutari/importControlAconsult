# ANEXO A — Gabarito de extração · Processo SY1453/26 (ENCATEX · SYNDEX)

> **Fase 0 da Fatia 1 — inspeção do kit `assets/novos_arquivos/`.** Documento de conferência: os
> valores abaixo foram lidos dos PDFs reais (camada de texto via `pdf_utils.extract_text`). Serve de
> gabarito para os testes. **Campos marcados "Precisa Larissa? = SIM" só viram asserção fixa após
> conferência humana** — até lá, os testes de saída contábil ficam `xfail`.
>
> **Nenhum valor foi fabricado.** Onde o documento não traz o dado, está registrado como ausente/`None`.

---

## 0. Achado crítico — a pasta mistura 4 processos (não é um kit SY1453 limpo)

`assets/novos_arquivos/` **não** contém apenas o processo SY1453. Classificando por CNPJ/conteúdo,
há documentos de **pelo menos 4 processos diferentes**. Isso muda a tarefa T6: a pasta precisa ser
**triada** — só os arquivos do SY1453 devem virar fixtures do SYNDEX.

| Processo | Importador · Despachante | Arquivos na pasta |
|---|---|---|
| **SY1453/26** (DUIMP `26BR0000258971-1`) | ENCATEX · **SYNDEX** | `DUIMP DESEMBARAÇADA…`, `2025ECX067 NOTA FISCAL…`, `NUMERARIO - SY1453…`, `FECHAMENTO_SY1453.26 Encatex Fatura`, `FRETE_PORTO-CTE`, `FRETE_PORTO-BOLETO`, `BILL OF LADING` (escaneado) |
| **26/0058** (DI `26/0418027-7`) | ALL LAB · **ALL TIME** | `FECHAMENTO DIGITAL.pdf` — é a *Prestação de Contas* ALL TIME, **mas com camada de texto OCR de baixíssima qualidade** (ex.: "DI 26/04180Z7-7", "ALL TIME A5SESSC)RIA"). Fora de escopo (Fatia 2) e, do jeito que está, **não parseável** de forma confiável. |
| **982 / CMO** | ZINLOG → CMO · **TERRA** | `Fechamento CMO`, `GRU Inmetro 3631859`, `NF Seara 1`, `NFES 1`, `NFS 275 Comissão` |
| **IM25/00171** | ZINLOG · Fortress (freight) | `Recibo Fortress` |

**Implicação:** a Invoice CML Biotech e o kit ALL TIME citados no spec §7 **não estão presentes como PDF
próprio com texto** — só existem embutidos e degradados no `FECHAMENTO DIGITAL.pdf`. Confirma manter
ALL TIME/Invoice fora da Fatia 1.

### Inventário completo dos 16 arquivos

| Arquivo | Classificação (por conteúdo) | Processo | Texto? |
|---|---|---|---|
| `DUIMP DESEMBARAÇADA - SY1453-26 - 2025ECX067.pdf` | **DUIMP** `26BR0000258971-1` | SY1453 | Sim (18,5k) |
| `2025ECX067 NOTA FISCAL IMPORTAÇÃO.pdf` | **NF-e** `000.002.411` | SY1453 | Sim (3,5k) |
| `NUMERARIO - SY1453-26 - 2025ECX067.pdf` | Pedido de **numerário** (estimativa) SYNDEX | SY1453 | Sim (1,4k) |
| `FECHAMENTO_SY1453.26 Encatex Fatura.pdf` | **Fechamento SYNDEX** (real) + NFS-e/DARE/recibos + DUIMP | SY1453 | Sim (28,5k) |
| `FRETE_PORTO-CTE.pdf` | **CT-e/DACTE** (NEXTRANS/CONTLOG, frete rodoviário) | SY1453 | Sim (6,5k) |
| `FRETE_PORTO-BOLETO.pdf` | Boleto/NFS-e do frete | SY1453 | Sim (2,8k) |
| `BILL OF LADING.pdf` | BL marítimo | SY1453 | **Não (escaneado)** |
| `FECHAMENTO DIGITAL.pdf` | **Prestação de Contas ALL TIME** (ALL LAB, DI 26/0418027-7) | 26/0058 | Texto OCR degradado (47k) |
| `Fechamento CMO.pdf` | Fechamento TERRA (resumo) | 982/CMO | Sim (1,5k) |
| `GRU Inmetro 3631859.pdf` | GRU Inmetro | 982/CMO | Sim (2,1k) |
| `NF Seara 1.pdf` | NFS-e | 982/CMO | Sim (4,2k) |
| `NFES 1.pdf` | NFS-e (TERRA) | 982/CMO | Sim (2,5k) |
| `NFS 275 Comissão.pdf` | NFS-e comissão | 982/CMO | Sim (2,6k) |
| `NUMERARIO …_RECIBO.pdf` | Recibo/comprovante | SY1453 | **Não (escaneado)** |
| `NUMERARIO …_(COMPLEMENTO)_RECIBO.pdf` | Recibo/comprovante | SY1453 | **Não (escaneado)** |
| `Recibo Fortress.pdf` | Recibo freight forwarder | IM25/00171 | Sim (1,1k) |

**3 arquivos sem camada de texto** (BILL OF LADING, os 2 RECIBO do numerário) → fora de escopo (OCR),
sinalizar `nao_reconhecido` com aviso "sem camada de texto".

---

## 1. DUIMP `26BR0000258971-1` — gabarito

> ⚠️ **Layout diferente do DUIMP 1159** já suportado. Este usa blocos `==========` e rótulos
> `VMCV USD/REAIS`, `MOEDAS E TAXAS`, `DEMONSTRATIVO DE CALCULOS`. O parser atual (`duimp.py`,
> calibrado no 1159) **não** lê este formato — precisará de novos padrões (T-extra, ver §6).
>
> ⚠️ **A DUIMP NÃO imprime CBS/IBS em valor** — só o `cClassTrib 000001`. Os valores monetários de
> CBS/IBS estão na **NF-e** (ver §2).

| Campo | Valor extraído | Fonte (linha) | Confiança | Precisa Larissa? |
|---|---|---|---|---|
| Número / versão | `26BR0000258971-1` / `0001` | "Extrato da Duimp …" | Alta | Não |
| Situação | `Desembaraçada. Aguardando Cumprimento de Tributos Estaduais` | bloco Situação | Alta | Não |
| Importador | `ENCATEX IMPORTACAO E EXPORTACAO LTDA` · `53.203.621/0001-39` | bloco Importador | Alta | Não |
| Tipo de importação | `Importação Direta` | "Indicação de importação para terceiros" | Alta | Não |
| Ref. despachante / cliente | `SY1453/26` / `2025ECX067` | "REF. SYNDEX / REF. CLIENTE" | Alta | Não |
| Cotação USD (TX DI) | `5,28000` | "MOEDAS E TAXAS … Taxa: 5,28000" | Alta | Não |
| **VMCV USD (invoice US$)** | `52.403,08` | "VMCV USD:" | Alta | **SIM** (é o campo 1; base do campo 3) |
| VMCV REAIS | `276.688,29` | "VMCV REAIS:" | Alta | Não |
| Frete USD / REAIS | `1.050,00` / `5.544,00` | "MOEDA FRETE … VALOR USD/REAIS" | Alta | Não |
| Valor aduaneiro USD / REAIS | `53.453,08` / `282.232,29` | "VALOR ADUANEIRO USD/REAIS" | Alta | Não |
| II | `42.114,64` | DEMONSTRATIVO DE CALCULOS | Alta | Não |
| IPI | `10.873,77` | idem | Alta | Não |
| PIS | `6.141,72` | idem | Alta | Não |
| COFINS | `29.977,44` | idem | Alta | Não |
| Siscomex | `154,23` | idem | Alta | Não |
| Total tributos federais | `89.261,80` (**derivado**, soma; não impresso) | — | Média | Não (marcar derivado) |
| **CBS / IBS-UF / IBS-MUN** | **ausente na DUIMP** (só `cClassTrib`) | — | — | — |
| cClassTrib (item) | `000001 - Situações tributadas integralmente pelo IBS e CBS` | itens 1–6 | Alta | Não |
| País origem / aquisição | `China (CN)` / `Hong Kong (HK)` | itens | Alta | Não |
| Exportador estrangeiro | `HONG KONG ALLIANCE GLOBAL TRADING CO., LTD` | "Código do Exportador Estrangeiro" | Alta | Não |
| Fabricante | `NINGBO WORLD ALLIANCE TRADING CO. LTD.` | "Código do Fabricante/Produtor" | Alta | Não |
| Data registro / chegada | `23/03/2026` / `16/03/2026` | Histórico / "DATA CHEGADA" | Alta | Não |
| Peso bruto | `24.980,00` | "PESO BRUTO" | Alta | Não |
| Peso líquido | ⚠️ **divergência interna**: `23.396,00` (info) vs `24.138,00` (Dados da Carga) | 2 blocos | Baixa | Não (vira Aviso) |
| Volumes | `842` | NF-e / "842 X ROLO" | Média | Não |
| Navio / BL | **ausente na DUIMP**; achados na NFS-e: `KOTA PUSAKA 0039E` / `NBBLU26022319` | Fechamento (NFS-e obs) | Média | Não |
| Nº de itens / NCM | 6 itens · todos `5907.0000` | itens | Alta | Não |

---

## 2. NF-e de importação `000.002.411` — gabarito

> **É aqui que estão os valores da Reforma Tributária.** Estão no bloco de Informações Complementares
> (texto livre), não em campos estruturados — parsing por rótulo (`CBS R$ …`, `IBS UF R$ …`, `IBS MUN. R$ …`).

| Campo | Valor extraído | Fonte | Confiança | Precisa Larissa? |
|---|---|---|---|---|
| Número / série | `000.002.411` / `001` | topo DANFE | Alta | Não |
| Emissão | `25/03/2026` | "Emissão" | Alta | Não |
| Chave de acesso | `42260353203621000139550010000024111153675423` | bloco chave | Alta | Não |
| Natureza | `COMPRA PARA NACIONALIZACAO` | natureza | Alta | Não |
| CFOP | `3102` (importação **direta/própria** — bate com spec §1.2) | itens | Alta | Não |
| Emitente | `ENCATEX` · `53.203.621/0001-39` | destinatário/remetente | Alta | Não |
| Remetente (exportador) | `HONG KONG ALLIANCE GLOBAL TRADING CO., LTD` | dest/remetente | Alta | Não |
| Base ICMS / Valor ICMS | `0,00` / `0,00` (ICMS diferido) | Cálculo do imposto | Alta | Não |
| Valor total dos produtos | `292.461,18` | Cálculo do imposto | Alta | Não |
| Valor do IPI | `10.873,77` | Cálculo do imposto | Alta | Não |
| **Valor total da NF** | `382.358,58` | Cálculo do imposto | Alta | **SIM** (valor da 1ª partida do Passo 5) |
| **CBS** | `3.018,3` (impresso `R$ 3.018,3` — 1 casa decimal!) | Info. complementares | Média (formato) | Não |
| **IBS-UF** | `273,57` | Info. complementares | Alta | Não |
| **IBS-MUN** | `0,00` | Info. complementares | Alta | Não |
| II / PIS / COFINS / IPI (obs) | `42.114,64` / `6.141,72` / `29.977,44` / `10.873,77` | Info. complementares | Alta | Não |
| AFRMM (obs) | `738,34` ⚠️ (difere do fechamento `635,58`) | Info. complementares | Alta | Não (Aviso) |
| Siscomex (obs) | `192,78` ⚠️ (difere da DUIMP `154,23`) | Info. complementares | Alta | Não (Aviso) |
| DUIMP referida | `26BR0000258971-1` DATA `23/03/2026` | Info. complementares | Alta | Não |
| Transportador | `CONTLOG TRANSPORTES LTDA` · `37.361.428/0001-70` | transportador | Alta | Não |

---

## 3. Fechamento SYNDEX (Fatura) — gabarito

> **Despachante:** `SYNDEX LOGÍSTICA E GESTÃO ADUANEIRA LTDA` · CNPJ **`02.286.106/0002-00`**
> (âncora do detector). Layout tabular `Data | Descrição | Complemento | Valor | T(D/C) | Nr. Nota`.
> **Dois documentos distintos** para o mesmo processo:
> - **Numerário** (`NUMERARIO - SY1453…`) = *estimativa/adiantamento* pedido (valores redondos).
> - **Fechamento/Fatura** (`FECHAMENTO_SY1453.26 …`) = *prestação de contas real* → **é este que se lança**.

### 3.1 Despesas reais (débitos) do fechamento — o que vira lançamento

| Descrição | Valor | Anexo |
|---|---|---|
| COMISSÃO ADUANEIRA IMPORTAÇÃO - PORTO | `1.621,00` | NFS-E 42817 |
| IMPOSTO DE IMPORTAÇÃO | `42.114,64` | |
| I.P.I. | `10.873,77` | |
| PIS IMPORTAÇÃO | `6.141,72` | |
| COFINS IMPORTAÇÃO | `29.977,44` | |
| TAXA SISCOMEX | `154,23` | |
| ICMS IMPORTAÇÃO | `3.982,88` | DARE-SC |
| AFRMM - MARINHA MERCANTE | `635,58` | |
| .SEGURO DE CARGAS - IMPO | `877,39` | Recibo |
| ARMAZENAGEM | `7.352,40` | NFS-e Portonave |
| DESPESAS BANCÁRIAS | `5,82` | Recibo |
| **Total de Débitos** | **`103.736,87`** | ✅ soma confere |

### 3.2 Créditos (adiantamentos + retenções)

| Descrição | Valor | Tipo |
|---|---|---|
| IRRF | `24,32` | retenção |
| CSLL | `16,21` | retenção |
| COFINS | `48,63` | retenção |
| PIS | `10,54` | retenção |
| ADIANTAMENTO DE NUMERÁRIO | `101.645,23` | adiantamento |
| ADIANTAMENTO DE NUMERÁRIO | `2.090,00` | adiantamento |
| **Total de Créditos** | **`103.834,93`** | ✅ soma confere |

**Saldo:** `98,06` (créditos − débitos; o documento diz "R$98,06 a pagar"). Confiança alta.
**Dados bancários:** Banco Santander (033), Ag `3159`, C/C `13005676-6`, PIX `02.286.106/0002-00`.

### 3.3 Numerário (estimativa — para referência, **não** lançar)
Total estimado `101.645,23`. Difere do real em cada rubrica (ex.: II estimado `42.500,00` vs real
`42.114,64`; ICMS `4.500,00` vs `3.982,88`; AFRMM `670,00` vs `635,58`). É a diferença que o POP 6.2.4
joga na conta do despachante.

---

## 4. Campo 3 (RESULTADO R$) e câmbio

| # | Campo (spec §1.3) | Valor | Origem |
|---|---|---|---|
| 1 | VALOR INVOICE US$ | `52.403,08` | DUIMP VMCV USD (não há Invoice no processo) |
| 2 | TX DI | `5,28000` | DUIMP MOEDAS E TAXAS |
| 3 | **RESULTADO R$** = 1×2 | **`276.688,26`** (calc.) ≈ `276.688,29` (VMCV REAIS impresso) | provisão do fornecedor |
| 4–8 | câmbio (USD PG, TX câmbio, VLR PG R$, VLR PG×TX DI, Variação) | **ausentes** | sem contrato de câmbio → middleware |

> Diferença de `0,03` entre calculado (`276.688,26`) e impresso (`276.688,29`) = arredondamento
> por-item da Receita. **Decisão para Larissa:** usar o VMCV REAIS impresso ou o produto recalculado?
> (afeta a 2ª partida do Passo 5).

---

## 5. Checagens de auto-consistência (spec §3 — divergência é Aviso, não correção)

| Checagem | Resultado |
|---|---|
| Soma débitos do fechamento = total declarado | ✅ `103.736,87` = `103.736,87` |
| Soma créditos do fechamento = total declarado | ✅ `103.834,93` = `103.834,93` |
| Saldo = créditos − débitos = declarado | ✅ `98,06` = `98,06` |
| Soma numerário = total declarado | ✅ `101.645,23` = `101.645,23` |
| Campo 3 (VMCV_USD × TX_DI) ≈ VMCV REAIS DUIMP | ✅ `276.688,26` ≈ `276.688,29` (Δ 0,03) |

**Divergências entre documentos (viram `Aviso`, extração crua):**
- **AFRMM**: DUIMP (ausente) · NF-e `738,34` · numerário `670,00` · fechamento `635,58`.
- **Siscomex**: DUIMP `154,23` · NF-e `192,78` · numerário/fechamento `154,23`.
- **ICMS**: NF-e (campo) `0,00` diferido · DARE/fechamento `3.982,88` · numerário `4.500,00`.
- **Peso líquido DUIMP**: `23.396,00` (info) vs `24.138,00` (Dados da Carga).

---

## 6. Consequências para o plano (a confirmar antes de codar)

1. **T5/T-extra — DUIMP tem 2 layouts.** O DUIMP SY1453 usa formato `VMCV/DEMONSTRATIVO`, diferente do
   1159. O `duimp.py` atual não o lê. Isso é **trabalho extra não previsto explícito na Fatia 1** —
   ou generalizo o `duimp.py`, ou crio um segundo parser. **Precisa decisão.**
2. **CBS/IBS vêm da NF-e, não da DUIMP** (ao contrário do que o T3/testes assumiam). A captura da reforma
   deve ser feita no `nota_fiscal.py`, e a DUIMP só fornece `cClassTrib`.
3. **A pasta precisa ser triada** antes do `git add` (T6): versionar como fixtures do SYNDEX apenas os
   7 arquivos do SY1453; os demais são de outros 3 processos (982/CMO, ALL TIME, Fortress).
4. **Fechamento ≠ Numerário.** Lançar o **fechamento real** (§3.1), não o numerário. Confirmar.
5. **CBS `R$ 3.018,3`** vem com 1 casa decimal no PDF — `parse_valor_br` lê como `3018.3`; confirmar se
   é `3.018,30`.

---

## 7. Campos que ficam `xfail` (aguardando conferência da Larissa)

Estes envolvem **interpretação contábil** (qual valor entra em cada partida) — não fixar como asserção
até aprovação:

- **Passo 5 · partida 1** — valor = **valor total da NF** `382.358,58`? (confirmar se é o total da NF ou
  o valor dos produtos `292.461,18`).
- **Passo 5 · partida 2** — valor = **RESULTADO R$**: usar `276.688,26` (calc.) ou `276.688,29` (impresso)?
- **Regra CBS/IBS** — extraídos e reservados; **partida a definir** (LACUNA spec §1.6/§8). Fica parametrizado.
- **Passos 7 e 8** — sem contrato de câmbio no processo → variação cambial não validável; entra pelo middleware.
- **Passo 6.2.4/6.2.5** — destino da diferença numerário×real e do saldo (`98,06`) → estoque/despachante:
  confirmar contas e sentido.

---

*Fase 0 concluída. Aguardando conferência humana deste gabarito antes de iniciar T1–T6.*
