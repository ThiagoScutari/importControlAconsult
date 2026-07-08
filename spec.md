# Spec — Extrator de Dados de Importação → Domínio
### Contabilidade Aconsult · Mockup de validação

**Versão:** 0.2 (consolidada — substitui a 0.1)
**Data:** 2026-07-04
**Etapa:** Validação de fluxo, extração e formato de saída. **Não** é desenvolvimento de produção.
**Objetivo:** provar que conseguimos (1) extrair os dados dos documentos de importação de um processo e (2) gerar os artefatos de saída (extração estruturada + lançamentos no layout do Domínio), validando o fluxo com a key user (Larissa) antes de investir em desenvolvimento.

> **Ponto de partida deste documento:** o **POP da Larissa** é a nossa base de conhecimento (Seção 1). Toda regra de negócio — quais documentos entram, o que se extrai de cada um, e como isso vira lançamento contábil — deriva dele. A Seção 1 é **canônica e versionada**: cada novo POP recebido é anexado ali, e o restante do spec se ajusta ao que ela disser.

---

## 1. BASE DE CONHECIMENTO — POP (fonte da verdade)

> **Como manter esta seção:** este é o repositório do conhecimento extraído dos POPs. Fonte atual: **(P1)** "Forma Correta de Envio da Documentação de Processos" e **(P2)** "POP Geral IMPORTAÇÃO", ambos da Larissa. Ao receber novos POPs, **acrescente** subitens numerados (1.x) e marque a origem `[P3]`, `[P4]`… Não sobrescrever — versionar. Onde o POP não define uma regra, marcar explicitamente como **LACUNA** (ver 1.6).

### 1.1 Taxonomia documental — o "processo completo" `[P1]`

Um processo de importação = **pasta com 6 blocos de documentos**. O operador deve enviar todos; o extrator deve reconhecê-los.

| # | Documento | Para que serve | Campos-chave a extrair |
|---|---|---|---|
| 01 | **Nota de Entrada (NF-e/DANFE)** | Lançamento do processo no sistema | Nº NF, chave, valor total, produtos, NCM, obs. (DI/Invoice no corpo), CBS/IBS quando houver |
| 02 | **DI ou DUIMP** | Conferência e contabilização | Taxa de câmbio da DI, valor a pagar ao estrangeiro, **VCMV**, tributos (II/IPI/PIS/COFINS/Siscomex), adições/itens |
| 03 | **Comercial Invoice** | Valor devido ao fornecedor no exterior | Nº invoice, moeda, valor FOB em moeda estrangeira, itens |
| 04 | **Fechamento do Despachante** (+ anexos) | Lançar custos do processo, baixar armazenagem/frete | Despesas por tipo, adiantamentos, saldo. **Anexos:** NFS-e de serviço, **CT-e**, boletos, GRU, DARE, termos AFRMM |
| 05 | **Fechamento Trading × Cliente** | Conferência final do processo | Preferir o **fechamento completo**, não só o numerário |
| 06 | **Contrato de Câmbio pago** | Baixa do fornecedor no exterior + variação cambial | Data de liquidação, taxa de câmbio, valor em moeda estrangeira e em R$, instituição financeira, vínculo com a importação |

**Regra de organização `[P1]`:** uma pasta por processo → no mockup, **um upload = um processo** (resolve o agrupamento sem casar arquivos por nome).

### 1.2 Identificação do processo no mês `[P2 · Passo 1]`

- Origem: módulo Fiscal → Relatórios > Acompanhamentos > **Resumo por Acumulador** (por período).
- **Acumuladores de importação:** `57` e `1001`.
- **CFOP:** `3102` = importação **própria**; `5949` = **encomenda** (NF física com destinatário = cliente e remetente = trading).

### 1.3 Planilha de controle — colunas calculadas `[P2 · Passo 3]`

Aba "Fornecedores Estrangeiros / Controle de Importações" (uma aba por fornecedor estrangeiro). Oito campos numerados (aprox. colunas **O–W**):

| # | Campo | Origem | Fórmula |
|---|---|---|---|
| 1 | VALOR INVOICE US$ | Invoice / DI (moeda estrangeira) | — |
| 2 | TX DI | Invoice / DI | — |
| 3 | **RESULTADO EM R$** | calculado | **1 × 2** → provisão do fornecedor |
| 4 | VLR USD PG CÂMBIO | Contrato de câmbio (moeda estrangeira) | — |
| 5 | TX CÂMBIO | Contrato de câmbio | — |
| 6 | VLR PG R$ | calculado | **4 × 5** |
| 7 | VLR PG × TX DI | calculado | **4 × 2** → "o que deveria ser pago ao fornecedor" |
| 8 | **VARIAÇÃO** | calculado | diferença cambial (positiva/negativa) |

> Atenção contábil: o campo **3 (RESULTADO EM R$)** é a **provisão do fornecedor** = USD da invoice × taxa da DI. **Não** é o valor da NF nem o valor aduaneiro.

### 1.4 Convenções de cadastro `[P2 · Passo 4]`

- **Conta do processo (plano de contas):** `PROCESSO + <nome conforme Fechamento/Prestação de Contas> + DI <nº DI> + NF <nº NF entrada>`.
  Ex.: `9999 - PROCESSO COT0000 DI 00/0000000-0 NF 000000`.
- **NF de importação** deve ser alocada em conta de **IMPORTAÇÕES EM ANDAMENTO** (permite refazer o processo sem alterar fechamentos anteriores).
- Gerar **conta de fornecedor estrangeiro** (Fiscal → Utilitários → Alterar Cadastro de Clientes e Fornecedores → Fornecedores → Contas Contábeis) e reclassificar de "Fornecedores" para "Fornecedores estrangeiros" no Contábil.

### 1.5 Algoritmo de contabilização `[P2 · Passos 5–9]`

Estrutura D/C fixa por passo (regra de negócio; contas específicas variam por cliente — ver 5. Middleware). Contas de exemplo observadas entre colchetes.

**Passo 5 — NF de entrada (dois lançamentos):**
1. `D` IMPORTAÇÕES EM ANDAMENTO [1633] · `C` Conta do Processo [1648]
   Histórico: `TRANSFERÊNCIA DE VALORES IMPORTAÇÃO EM ANDAMENTO CFM #C`
2. `D` Conta do Processo [1648] · `C` Fornecedor Estrangeiro [1177] · **Valor = campo 3 (RESULTADO EM R$)**
   Histórico: `VALOR DEVIDO FORNECEDOR #C REF. #D USD # E TAXA INVOICE #`

**Passo 6 — Despesas do processo:**
- **6.1 NF de serviço** (honorários aduaneiros / despacho / intermediação): vêm do Fiscal como `D 362 (serviço terceiros) · C Fornecedor`. Alterar o **débito 362 → conta da importação (99999)**; crédito mantém (inclusive retenções). Histórico: manter o do Fiscal + nome do processo.
- **6.2 Despesas do numerário sem NF própria** (tarifa bancária, frete, moto boy, AFRMM, frete marítimo, armazenagem…): lançamento único **vários débitos → vários créditos**. `D` Conta do Processo (uma linha por despesa, tipo no histórico) · `C` Adiantamento ao despachante.
- **6.2.2** Se a despesa já tem NF alocada → baixa `D` Fornecedor.
- **6.2.4** A diferença entre despesas do numerário e o valor efetivo do processo vai para a conta do despachante (credora ou devedora).
- **6.2.5** Saldo remanescente na conta do processo → transferência para **Estoque**: se **positivo** `D` Estoque `C` Processo; se **negativo** `D` Processo `C` Estoque. Histórico: `fechamento de processo #C` (ou `#D`).

**Passo 7 — Pagamento do fornecedor estrangeiro (via câmbio):**
- (a) Pagamento antecipado: `D` Fornecedor estrangeiro · `C` Adiantamento fornecedor.
- (b) Pago no andamento: `D` Fornecedor estrangeiro · `C` Banco c/c.
- **7.2 Fornecedores de serviço (despachante/fretes):** baixa junto ao 6.2.2 → `D` Fornecedor despachante · `C` Adiantamento Trading · valor = líquido da NF.

**Passo 8 — Variação cambial (campo 8 da planilha):**
- Positiva (receita): `D` Fornecedor estrangeiro · `C` `973 - VARIAÇÃO CAMBIAL ATIVA`.
- Negativa (despesa): `D` `370 - VARIAÇÕES CAMBIAIS PASSIVAS` · `C` Fornecedor estrangeiro.

**Passo 9 — Finalização (acerto empresa × despachante):**
- `D` Banco `C` Despachante (despachante devolve), **ou** `D` Despachante `C` Banco (empresa ressarce). Histórico: `Fechamento Processo 99999`.

**Plano de contas / históricos observados** (referência, confirmar por cliente):
- Contas: IMPORTAÇÕES EM ANDAMENTO, Conta do Processo, Fornecedor Estrangeiro, Adiantamento a fornecedores, Despachante, Estoque, `362`, `973`, `370`.
- Códigos de histórico do Domínio vistos nos exemplos: `41` (despesa referente processo), `45`/`46` (transferência / valor devido), além de `25/56/59` da macro original.

### 1.6 LACUNAS do POP (não cobertas — exigem confirmação)

- **IBS/CBS (Reforma Tributária):** o POP descreve o regime **antigo** (PIS/COFINS + ICMS). Os documentos de 2026 já trazem **CBS/IBS** (ver Seção 8). **Regra de contabilização de CBS/IBS = a definir com a Larissa.**
- **Contrato de câmbio real:** temos só o modelo do POP; sem amostra real, os campos 4–8 e o Passo 8 ficam parametrizados, não validados.
- **Layouts de fechamento além de TERRA/WIN/SYNDEX/ALL TIME:** cada despachante novo é um parser novo.

---

## 2. Visão geral do fluxo

```
[Upload dos documentos do processo]  →  [Extração automática]  →  [Conferência + Middleware]  →  [Gerar arquivos]
        (1 processo por rodada)          (campos dos documentos)    (operador completa contas,        (downloads)
                                                                     histórico, entidade, câmbio)
```

Cada rodada de upload = **um processo** (regra 1.1). O operador sobe o pacote (NF + DI/DUIMP + Invoice + Fechamento + anexos + Contrato de Câmbio quando houver), o sistema extrai, o operador confere/completa, e gera as saídas da Seção 6.

---

## 3. Escopo do mockup

### Dentro do escopo
- Upload por arrastar/soltar dos documentos de **um processo**.
- Extração dos campos dos documentos suportados (Seção 4), guiada pela Seção 1.
- Suporte a **DI** e **DUIMP** (dois modelos) e à **NF-e de importação**.
- Suporte à **Comercial Invoice** (temos amostra real — CML Biotech).
- Suporte aos fechamentos **TERRA, WIN, SYNDEX e ALL TIME** (quatro layouts com amostras reais).
- Reconhecimento dos **anexos do fechamento**: NFS-e de serviço, CT-e/DACTE, boleto, GRU, DARE-SC, termo AFRMM, LI/anuência, BL/MTD, comprovantes de pagamento.
- **Extração de campos IBS/CBS** quando presentes nos documentos (ver Seção 8).
- Camada **Middleware** (Seção 5).
- Geração das saídas (Seção 6), com os lançamentos seguindo o algoritmo 1.5.

### Fora do escopo (nesta etapa)
- **Conciliação / apontamento de divergências** entre DI/DUIMP, NF, Invoice e Fechamento → extração crua + montagem das partidas conforme POP, sem auditoria automática de divergências.
- **Contabilização definitiva de CBS/IBS** enquanto a regra não for confirmada (extraímos e reservamos os campos; o lançamento fica parametrizável).
- Integração automática com o Domínio (importação segue **manual**, via arquivo).
- **Contrato de câmbio real** (parametrizado até recebermos amostra).
- Persistência/banco, autenticação, multiusuário.
- OCR de escaneados de baixa qualidade (alguns anexos são imagens ruins — ver Seção 10).

---

## 4. Documentos suportados e campos extraídos

Guiado pela taxonomia 1.1. Resumo por tipo (campos detalhados no anexo de implementação):

- **DUIMP** (ex. 26BR0000258971-1): nº/versão, situação, importador (CNPJ/nome), tipo de importação (direta / conta e ordem), ref. despachante e cliente, invoice (nº/data/valor US$), moeda/taxa, VMCV/VMLD (US$/R$), tributos (II/IPI/PIS/COFINS/Siscomex), **CBS/IBS por item (`cClassTrib`)**, porto/navio/BL/chegada/recinto, pesos, exportador e fabricante, itens (NCM, qtd, valor).
- **DI** (ex. 26/0418027-7): nº/data registro, importador/adquirente, representante, modalidade/nº adições, frete/VMLE/VMLD, tributos, carga (manifesto/recinto/pesos), ref. interna/BL/navio/fatura, cotação e valores R$/US$, por adição (exportador, fabricante, NCM, INCOTERM, VCMV, alíquotas, LI/anuência).
- **NF-e de importação (DANFE de entrada)**: nº/série/chave, emitente/destinatário, natureza, valor produtos/total, ICMS/IPI, **CBS/IBS/IBS-UF/IBS-MUN** e demais campos da reforma quando houver, itens (NCM/CFOP/qtd/valor), obs. (DUIMP/DI, PIS/COFINS entrada, Siscomex).
- **Comercial Invoice** (ex. CML Biotech): exportador, consignee, nº invoice/data, INCOTERM, moeda, itens (NCM, batch, qtd, unit price, total), FOB total US$, condições de pagamento.
- **Fechamentos** (TERRA / WIN / SYNDEX / ALL TIME): despesas por tipo, adiantamentos/numerário, tributos recolhidos, saldo credor/devedor, dados bancários. Layouts distintos → um parser por despachante.
- **Anexos**: NFS-e (despachante/porto/frete), CT-e/DACTE (frete rodoviário, ICMS), GRU (Inmetro), DARE-SC (ICMS importação/diferido), termo/`débito` AFRMM, BL/MTD, comprovantes Pix/TED/boleto.
- **Contrato de câmbio** (modelo do POP): tipo/nº contrato, data, moeda, valor moeda estrangeira e nacional, taxa cambial, VET, data de liquidação, pagador/recebedor exterior, instituição.

---

## 5. Middleware (campos que não vêm dos documentos)

O extrator preenche o que é do documento; o operador confere e completa o que é **regra de negócio / plano de contas**:

| Campo | Origem | Observação |
|---|---|---|
| Entidade contábil (trading × adquirente) | Operador | Define CNPJ/contas em conta e ordem |
| Conta do Processo (nº) | Gerado por regra 1.4 + operador | Nome montado automaticamente; nº confirmado |
| Contas débito/crédito por partida | Operador / de-para | Específicas por cliente |
| Códigos de histórico | Operador / de-para | Tabela do Domínio (ex. 41/45/46) |
| Complemento do histórico | Gerado (templates 1.5) + editável | Ex.: `VALOR DEVIDO FORNECEDOR … USD … TAXA INVOICE …` |
| Data do lançamento / lote / matriz-filial / CC | Operador | Conforme regra Domínio |
| Dados do contrato de câmbio (campos 4–8) | Operador (até termos parser) | Alimenta variação cambial |
| **Tratamento CBS/IBS** | Operador (parametrizado) | Até a regra ser confirmada (1.6 / Seção 8) |

**De-para (recomendado):** `fornecedor estrangeiro → conta`, `tipo de despesa → conta/histórico`, `despachante → contas`. Pré-preenche o middleware e "aprende" a cada processo. No mockup pode ser tabela simples e editável; arquitetura já prevê evoluí-la.

---

## 6. Layout dos arquivos de saída

### 6.1 Saída A — Extração estruturada (`.csv`)
Uma linha por processo (espelha o controle "Relação importações"), incluindo colunas 1–8 da planilha (Seção 1.3) e os blocos de tributos federais **e** os campos da reforma:
`Tipo Importação; Data NF; DI/DUIMP; Nº NF; Valor NF; Processo; Despachante; Fornecedor Estrangeiro; Fabricante; País Origem; País Aquisição; Invoice (nº); Invoice USD; TX DI; Resultado R$; USD PG Câmbio; TX Câmbio; VLR PG R$; VLR PG × TX DI; Variação; FOB R$; Frete R$; Valor Aduaneiro R$; II; IPI; PIS; COFINS; CBS; IBS-UF; IBS-MUN; Siscomex; AFRMM; ICMS; Armazenagem; Total Tributos; Peso Líquido; Volumes; Navio; BL; Chave NF-e`

> Opcional (auditoria/rastreio): versão longa `Processo; Documento; Campo; Valor; Fonte`.

### 6.2 Saída B — Lançamentos Domínio (partidas)
Layout **idêntico ao da macro** `Sub Gerar()` (`lanctos.txt`), separado por `;`, **sem cabeçalho** no arquivo final, uma linha por partida gerada pelo algoritmo 1.5:
```
Data;Cód.Conta Débito;Cód.Conta Crédito;Valor;Cód.Histórico;Complemento Histórico;Inicia Lote;Matriz/Filial;Centro Custo Débito;Centro Custo Crédito
```
Contas, histórico e lote vêm do middleware/de-para (Seção 5). As partidas de CBS/IBS entram condicionadas à regra confirmada (Seção 8).

### 6.3 Saída C — Cadastro de fornecedor / controle interno (`.csv`, opcional)
`Código Exportador; Nome Exportador Estrangeiro; Endereço; País Aquisição; Nome Fabricante/Produtor; País Origem; Relação Exportador×Fabricante; Vinculação Comprador×Vendedor`.

---

## 7. Corpus de teste (documentos reais disponíveis)

| Processo / Ref | Importador · Modalidade | Despachante (layout) | Regime | Documentos presentes | Kit completo? |
|---|---|---|---|---|---|
| **SY1453/26 · 2025ECX067** (DUIMP 26BR0000258971-1) | ENCATEX · Direta | **SYNDEX** | IBS/CBS **+** PIS/COFINS | NF-e 2.411, DUIMP, fechamento + NFS-e porto/despachante, DARE-SC, AFRMM, CT-e Nextrans + boleto, recibos, Pix/TED | Sem **Invoice** e sem **contrato de câmbio** |
| **26/0058 · CML-EXP-PI-51/25-26** (DI 26/0418027-7) | ALL LAB · Direta (imp=adq) | **ALL TIME** + Rhenus | PIS/COFINS (reduzido 0%) | DI (2 adições), **Invoice CML Biotech**, Packing List, BL/MTD, LI Anvisa, fechamento + NFS-e, DARE-SC, AFRMM, armazenagem JBS, Best Frete, comprovantes | Sem **contrato de câmbio** |
| **982# · HKYCMOBR982** | ZINLOG p/ CMO · Conta e ordem | **TERRA** | — | Fechamento TERRA, GRU Inmetro | Parcial (amostra de layout) |
| **1159# / 870#** (rodadas anteriores) | ZINLOG-CMO / INFINITY | TERRA / WIN | — | DUIMP+NF / DI+TERRA / WIN | Parcial |

**Cobertura obtida:** DI + DUIMP; quatro layouts de fechamento (TERRA/WIN/SYNDEX/ALL TIME); duas modalidades (direta / conta e ordem); Invoice real; ampla amostra de anexos.
**Gap remanescente:** nenhum processo com **contrato de câmbio real**; documentos adicionais a receber (fora deste chat).

---

## 8. Reforma Tributária (IBS/CBS) — ano de transição

**Fato:** em 2026 os documentos coexistem em dois regimes. A DUIMP/NF-e da ENCATEX trazem **CBS e IBS** (NF-e: `CBS`, `IBS-UF`, `IBS-MUN`; item da DUIMP com `cClassTrib 000001 - tributadas integralmente pelo IBS e CBS`) **junto** com PIS/COFINS. A DI (modelo antigo) traz apenas PIS/COFINS.

**Decisão:** **considerar IBS/CBS no escopo** — o extrator **captura e reserva** os campos da reforma sempre que presentes, e a Saída A já os inclui (Seção 6.1).

**Pendência (LACUNA 1.6):** o POP descreve o regime antigo; a **regra de contabilização do CBS/IBS** (contas, históricos, partidas) **precisa ser confirmada com a Larissa**. Até lá, os lançamentos de CBS/IBS na Saída B ficam **parametrizáveis** no middleware (não hardcoded), para não travar o piloto nem antecipar regra incorreta.

---

## 9. Premissas e decisões confirmadas
- **POP = base de conhecimento canônica** (Seção 1), versionada a cada novo POP.
- Importação no Domínio = **layout de partidas** (igual à macro atual).
- Saída A = prova de extração; Saída B = destino real (partidas); C = opcional.
- **DI e DUIMP** suportados; NF de importação suportada; **Invoice** suportada.
- Fechamentos suportados: **TERRA, WIN, SYNDEX, ALL TIME**.
- **Um upload = um processo.**
- Contas/histórico/entidade contábil: via **middleware/de-para** (não extraíveis).
- **IBS/CBS extraídos e reservados**; contabilização a confirmar.
- Importação no Domínio permanece **manual**.
- `SecurityData_1782083140.xlsx`: anexado por engano — ignorado.

---

## 10. Riscos e observações
- **Maior risco de extração:** layouts de fechamento (4 distintos) e a qualidade dos escaneados (alguns anexos vêm como imagem de baixa resolução — ex. prestações da ALL TIME e comprovantes bancários; podem exigir OCR ou conferência manual).
- **Contrato de câmbio ausente** nos pacotes reais → variação cambial validada só via modelo.
- **Regra CBS/IBS não confirmada** → único ponto que pode alterar a Saída B.
- Documentos adicionais da Larissa a receber por outro canal → podem trazer novos despachantes/layouts.

---

## 11. Stack (mockup)
Aplicação web leve: upload/drag-and-drop, extração de texto dos PDFs no cliente, parsers por layout (guiados pela Seção 1), formulário de conferência/middleware com de-para, e geração dos `.csv`/`.txt` para download. Sem backend persistente nesta etapa.

---

## 12. Próximos passos
1. Receber os **documentos adicionais** e os **próximos POPs** (anexar à Seção 1).
2. Confirmar a **regra de contabilização IBS/CBS** (destrava a Saída B completa).
3. Obter um **contrato de câmbio real** (valida campos 4–8 e Passo 8).
4. Montar o mockup e gerar A + B de exemplo a partir de um processo real completo (ENCATEX é o candidato mais rico).
