# Instruções para o Claude Code — Mockup Extrator de Importação (Aconsult)

> **Leia também `spec.md` antes de começar — ele é a fonte de verdade do escopo.**
> Este arquivo é o plano de construção. Se algo aqui conflitar com o `spec.md`, siga o `spec.md` e avise o desenvolvedor.

---

## 0. Objetivo

Construir um **mockup funcional** que:
1. recebe os PDFs de **um processo de importação** por upload (arrastar/soltar);
2. **extrai automaticamente** os dados (extração crua, sem conciliação);
3. permite ao operador **conferir e completar** os campos que não existem nos documentos (camada *Middleware*);
4. **gera os arquivos de saída** para download.

É um mockup de **validação de fluxo** — priorize clareza e uma extração que funcione bem nos exemplos reais. Não é produção; não precisa de banco, login ou deploy.

---

## 1. Stack e como rodar

- **Python 3.11+**, **FastAPI**, **uvicorn**, **pdfplumber** (extração de PDF), **pydantic**, **python-multipart** (upload). Saída CSV com o módulo `csv` da stdlib (sem pandas obrigatório).
- **Front-end**: HTML/CSS/JS puro (sem framework), servido como estático pela própria API.
- **Testes**: `pytest`.

Comandos esperados ao final (documente no README):
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
# abrir http://localhost:8000
pytest
```

---

## 2. Estrutura de pastas (criar)

```
.
├── assets/                     # documentos-fonte (JÁ EXISTEM — use como fixtures de teste)
├── docs/                       # imagem do fluxo (já existe)
├── spec.md                     # já entregue — colocar na raiz
├── INSTRUCOES_CLAUDE_CODE.md   # este arquivo
├── README.md                   # GERAR POR ÚLTIMO (ver seção 10)
├── requirements.txt
├── backend/
│   ├── main.py                 # app FastAPI + rotas + servir front-end
│   ├── models.py               # schemas Pydantic (ProcessoExtraido, MiddlewareInput, etc.)
│   ├── pdf_utils.py            # extrair texto (pdfplumber) + helpers de número/data BR
│   ├── detector.py             # identifica o tipo do documento pelo conteúdo
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── duimp.py
│   │   ├── di.py
│   │   ├── nota_fiscal.py
│   │   ├── fechamento_terra.py
│   │   └── fechamento_win.py
│   ├── consolidador.py         # junta vários documentos em 1 registro de processo
│   ├── depara.py               # tabela de-para (seed simples, editável)
│   └── outputs.py              # gera CSV A, B e C
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── tests/
    ├── test_detector.py
    ├── test_extractors.py
    └── test_outputs.py
```

---

## 3. Regras gerais (valem para todos os extratores)

- **Identificar o tipo pelo conteúdo do texto, não pelo nome do arquivo.** Âncoras sugeridas:
  - DUIMP → contém `Extrato da Duimp` / `DUIMP`.
  - DI → contém `EXTRATO DA DECLARAÇÃO DE IMPORTAÇÃO` / `Declaração: NN/NNNNNNN-N`.
  - NF de importação → contém `DANFE` / `NF-e`.
  - Fechamento TERRA → cabeçalho `TERRA DESP. ADUANEIROS` / CNPJ `05.989.453/0001-06`.
  - Fechamento WIN → cabeçalho `WIN TRADING` / CNPJ `26.316.473/0002-77`.
- **Números em formato brasileiro**: `1.234,56` → `1234.56`. Criar helper `parse_valor_br(str) -> float | Decimal`.
- **Datas** em `dd/mm/aaaa` (manter string; não converter para serial).
- **Tolerar documento ausente**: um processo pode ter só DUIMP+NF, ou só DI+Fechamento. Nunca quebrar por falta de um tipo.
- **Extração crua**: NÃO conciliar nem validar divergências entre documentos nesta etapa.
- **Sem câmbio / variação cambial** (colunas S–X do controle ficam fora).
- Campo não encontrado → retornar `null`/vazio (não inventar valor), e registrar em uma lista `avisos` do processo.

---

## 4. Campos a extrair por documento

> Detalhe completo está no `spec.md`, seção 4. Resumo operacional abaixo. Os **valores esperados reais** estão no Anexo A (use para os testes).

**DUIMP** — número/versão; situação; CNPJ e nome do importador; tipo de importação (própria / conta e ordem); referência (`NNNN#`); fatura (nº/data/US$); cotação USD; FOB (R$/US$), frete (R$/US$), valor aduaneiro (R$/US$); tributos (II, IPI, PIS, COFINS, Siscomex, total); data de registro; navio, BL, chegada, armazém; país de procedência/aquisição; peso bruto/líquido e volumes; exportador estrangeiro e fabricante.

**DI** — número e data de registro; importador e adquirente (CNPJ/nome); representante; nº de adições; frete/VMLE/VMLD (US$); tributos (II, IPI, PIS, COFINS); referência (`NNNN#`); BL, navio, chegada, armazém, fatura; cotação FOB; FOB R$/US$, frete R$, valor aduaneiro R$; Siscomex; total tributos; peso bruto/líquido e volumes.

**NF de Importação (DANFE)** — número/série; data de emissão; emitente (CNPJ/nome); destinatário (CNPJ/nome); CFOP; base/valor ICMS; valor total dos produtos; valor total IPI; valor total da NF; chave de acesso; info complementares (processo, exportador, PIS/COFINS de entrada, Siscomex).

**Fechamento TERRA** — despachante (nome/CNPJ); cliente (CNPJ/nome); código interno/processo, referência, fatura; navio/origem/destino; **lista de despesas** (descrição + vencimento + valor); retenções (PIS/COFINS/CSLL/ISS/IRRF); totais e saldo.

**Fechamento WIN** — trading (nome/CNPJ); processo; modalidade; INCOTERM; adquirente e referência; exportador; declaração e data de registro; cotação USD; FOB/frete/seguro/valor aduaneiro; **lista de despesas detalhadas**; total, retenções, saldo.

> Para os fechamentos, retorne as despesas como **lista de `{descricao, valor, vencimento?}`** — cada despachante tem um parser próprio.

---

## 5. Consolidação por processo (`consolidador.py`)

- Entrada: lista de documentos já extraídos (cada um com seu `tipo` e seus campos).
- Saída: **um** objeto `ProcessoExtraido` com os campos mesclados.
- Chave do processo: a **referência** (`1159#`, `870#`) presente nos documentos; se ausente, usar nº da DI/DUIMP. Como o upload é por processo, na dúvida trate todos os arquivos da rodada como o mesmo processo.
- Em conflito de valor entre documentos para o mesmo campo (extração crua), **mantenha o do documento de maior prioridade** nesta ordem: DUIMP/DI > NF > Fechamento, e registre o divergente em `avisos` (sem conciliar).

---

## 6. Middleware (`models.py` + front-end)

Campos preenchidos/confirmados pelo operador antes de gerar (ver `spec.md` seção 5):

| Campo | Tipo | Fonte |
|-------|------|-------|
| `tipo_importacao` | enum (Própria / Conta e ordem / Encomenda) | operador (sugerir da DUIMP) |
| `entidade_contabil` | texto/seleção | operador (trading × adquirente) |
| `conta_debito` | código | de-para → operador |
| `conta_credito` | código | de-para → operador |
| `cod_historico` | código | de-para → operador |
| `complemento_historico` | texto | gerado e editável (ex.: `PROCESSO 1159 DUIMP 26BR... NF 000.000.769`) |
| `data_lancamento` | data | operador (default = data da NF/registro) |
| `inicia_lote` / `matriz_filial` / `cc_debito` / `cc_credito` | conforme Domínio | operador (opcionais) |

**De-para (`depara.py`)**: tabela simples e editável que pré-preenche `conta_*` e `cod_historico` a partir do **fornecedor estrangeiro** e do **tipo de despesa**. Pode começar com poucos registros de exemplo (ex.: fornecedor `SHANGHAI YESOP...` → conta `12374`; histórico `25`). Deixe a estrutura pronta para crescer.

---

## 7. Arquivos de saída (`outputs.py`)

### Saída A — Extração estruturada (`.csv`) — PRINCIPAL
Uma linha por processo. Colunas (ver `spec.md` 6.1; confirmar na reunião):
`Tipo Importação; Data NF; DI/DUIMP; Nº NF; Valor NF; Processo; Despachante; Fornecedor Estrangeiro; Fabricante; País Origem; País Aquisição; Invoice; Invoice USD; Cotação; FOB R$; Frete R$; Valor Aduaneiro R$; II; IPI; PIS; COFINS; Siscomex; AFRMM; ICMS; Armazenagem; Total Tributos; Peso Líquido; Volumes; Navio; BL; Chegada; Chave NF-e`

> Gerar também a versão **rastreável** (formato longo) `Processo; Documento; Campo; Valor; Fonte` — ótima para mostrar a procedência de cada dado na apresentação.

### Saída B — Lançamentos Domínio (partidas) — EXEMPLO
Layout **idêntico à macro `Sub Gerar()`**, separado por `;`, **sem cabeçalho** no arquivo final, 10 colunas nesta ordem:
```
Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;CC Débito;CC Crédito
```
Os valores de conta/histórico/lote vêm do **Middleware/de-para**. Gerar oferecendo extensão `.csv` e `.txt`.

### Saída C — Cadastro de fornecedor (`.csv`) — OPCIONAL (bônus)
`Código Exportador; Nome Exportador Estrangeiro; Endereço; País Aquisição; Nome Fabricante; País Origem; Relação Exportador×Fabricante; Vinculação Comprador×Vendedor` (dados da DUIMP/DI).

---

## 8. API + Front-end

**Rotas FastAPI:**
- `POST /extract` — recebe 1..N PDFs (multipart). Detecta tipo, extrai, consolida. Retorna JSON `ProcessoExtraido` + `avisos`.
- `POST /generate` — recebe o `ProcessoExtraido` (editado) + `MiddlewareInput`. Retorna os arquivos (A, B, e C se marcado) — pode ser um `.zip` ou links de download individuais.
- `GET /` — serve `frontend/index.html`.

**Fluxo do front-end (uma página):**
1. Área de **arrastar/soltar** (aceita múltiplos PDFs do processo) → chama `/extract`.
2. Mostra os **campos extraídos em formulário editável** (operador confere/corrige) + os **campos do Middleware** (seção 6), com de-para pré-preenchendo o que der.
3. Botão **"Gerar arquivos"** → chama `/generate` → dispara os downloads.
4. Mostrar `avisos` (campos não encontrados / divergências) de forma visível, sem travar.

Mantenha a UI limpa e direta — é uma demonstração para a key user.

---

## 9. Testes (`tests/`) — usar os arquivos de `assets/` como fixtures

Escreva testes com os **valores esperados do Anexo A**:
- `test_detector`: cada arquivo de `assets/` é classificado no tipo correto.
- `test_extractors`: DUIMP 1159, NF 1159, DI 870, Fechamento TERRA e Fechamento WIN retornam os campos-chave com os valores esperados.
- `test_outputs`: consolidando DUIMP 1159 + NF 1159 gera 1 processo `1159`; a Saída B respeita o layout de 10 colunas separadas por `;` sem cabeçalho.
- Tolerância: testar também processo com só um documento (não deve quebrar).

---

## 10. Entregável final — README.md (gerar por último)

Ao terminar, **gere um `README.md` didático, explicativo e fácil de entender**, cobrindo:
1. **O que é o projeto** e para quem (contabilidade Aconsult) — em linguagem simples.
2. **O problema** que resolve (extrair dados de importação e gerar arquivos para o Domínio) e o contexto do fluxo (referenciar a imagem em `docs/`).
3. **Como instalar e rodar** (passo a passo, com os comandos).
4. **Como usar o mockup** — tutorial passo a passo: arrastar PDFs → conferir/completar → gerar arquivos, com o que cada arquivo de saída significa (A, B, C).
5. **Estrutura de pastas** explicada.
6. **O que está e o que não está no escopo** (extração crua; sem câmbio/conciliação; só TERRA e WIN).
7. **Limitações conhecidas e próximos passos**.

Tom: como se explicasse para alguém não-técnico conseguir rodar e demonstrar. Use exemplos.

---

## Anexo A — Valores esperados para teste (dos arquivos em `assets/`)

**DUIMP 1159** — Nº `26BR0000380790-9` v0001 · Importador `ZINLOG TRADING, IMPORTACAO E EXPORTACAO LTDA` CNPJ `57.345.180/0001-60` · Tipo `Conta e Ordem` · Ref `1159#` · Fatura `HKYCMOBR1159` 03/02/26 US$ `17.069,00` · Cotação `5,0899` · FOB R$ `79.882,82` / US$ `15.694,38` · Frete R$ `6.996,68` · Vr.Aduaneiro R$ `86.879,50` · II `15.638,31` · IPI `9.995,49` · PIS `1.824,47` · COFINS `8.383,87` · Siscomex `154,23` · Total `35.996,37` · Navio `MSC AVNI` · BL `HLCUSHA2601CDGF5` · Chegada `06/04/26` · Armazém `BRASKARNE` · Procedência `China` / Aquisição `Hong Kong` · Peso bruto `18.045,15` líq `16.188,48` · Volumes `965` · Exportador `HONGKONG YESOP CONNECT SUPPLY CHAIN MANAGEMENT CP., LIMITED` · Fabricante `SHANGHAI YESOP CONNECT SUPPLY CHAIN MANAGEMENT CO., LTD`.

**NF Importação 1159** — NF `000.000.769` série `001` · Emissão `30/04/2026` · Emitente `ZINLOG` `57.345.180/0001-60` · Destinatário `CMO COMERCIO LTDA` `42.435.597/0002-28` · CFOP `5949` · Base ICMS `139.663,65` · ICMS `5.586,55` · V.Produtos `139.663,65` · IPI `13.617,20` · V.Total NF `153.280,85` · Chave `42260457345180000160550010000007691435300822` · Processo `Z028/26` · PIS entrada `1.824,46` · COFINS entrada `8.383,87` · Siscomex `154,23`.

**DI 870** — Declaração `25/2290426-3` · Registro `13/10/2025` · Importador/Adquirente `INFINITY COMERCIO DE IMPORTADOS LTDA` `24.545.851/0002-69` · Representante `JOSIANE IZING` · Adições `7` · Frete US$ `3.415,00` · VMLE US$ `19.214,12` · VMLD US$ `22.629,08` · II `15.679,92` · IPI `909,47` · PIS `2.587,33` · COFINS `12.752,27` · Ref `870#` · BL `SHYY25081848` · Navio `EVER FAST` · Chegada `01/10/25` · Armazém `BRASKARNE` · Fatura `YSPINFFBR870` · Cotação `5,4446` · FOB R$ `104.612,98` / US$ `19.214,08` · Frete R$ `18.593,31` · Vr.Aduaneiro R$ `123.206,29` · Siscomex `331,62` · Total tributos `32.260,61` · Peso bruto `14.653,78` líq `13.322,55` · Volumes `876`.

**Fechamento TERRA (870)** — Despachante `TERRA` `05.989.453/0001-06` · Cliente `INFINITY` `24.545.851/0002-69` · Cód interno `1819` · Ref `870#` · Fatura `YSPINFFBR870` · Navio `EVER FAST` · Origem `SHANGHAI` · Destino `NAVEGANTES` · Despesas: `TARIFA BANCARIA 13,50` · `MOTO BOY 20,00` · `AFRMM 1.595,46` · `ICMS 1.619,45` · `COMISSAO 3.000,00` · `FRETE MARITIMO 3.929,89` · `ARMAZENAGEM BRASKARNE 3.938,82` · `IMPOSTOS DI 32.260,61` · `ADIANTAMENTO 45.692,26` · Retenções: PIS `19,50` COFINS `90,00` CSLL `30,00` ISS `45,00` · Total informativo `46.193,23 CR` · Saldo `500,97 DB`.

**Fechamento WIN TRADING (ENC-153/2024.1)** — Trading `WIN TRADING LTDA` `26.316.473/0002-77` · Processo `ENC-153/2024.1` · Modalidade `Conta e ordem` · INCOTERM `FOB` · Adquirente `EQUIPMAX BRASIL` · Ref `ESC-2404-F139` · Exportador `HANGZHOU EQUIPMAX INDUSTRIES CO., LTD` · Declaração `24/2793486-0` · Registro `19/12/2024` · Cotação USD `6,16240114` · FOB `479.126,69` · Frete `44.677,41` · Seguro `785,71` · Vr.Aduaneiro `524.589,81` · Despesas: Frete intl `50.483,61` · Seguro intl `785,71` · II `58.754,05` · PIS `11.016,38` · COFINS `55.868,80` · ICMS `9.871,28` · IRPJ/CSLL `1.686,46` · Contrato Câmbio `433.414,12` · Honorários WIN `2.644,48` · Despacho `2.824,00` · AFRMM `3.658,67` · Siscomex `192,79` · Armazenagem `9.123,85` · Tarifa bancária `10,50` · Total `640.334,70` · Retenções `194,86`.

> Observação para os testes: em `assets/` o processo **1159** tem DUIMP + NF (sem fechamento) e o **870** tem DI + Fechamento TERRA (sem NF). O Fechamento WIN é um exemplo isolado do layout (processo ENC-153). Os parsers devem funcionar isoladamente.
